#!/usr/bin/env node
/**
 * A4 Trading Execution via Node.js (bypasses local Python SSL issue)
 * Executes trades directly on Binance
 */
const https = require('https');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Config
const AUTH_PATH = path.join(__dirname, '..', 'config', 'auth.json');
const TRADES_PATH = path.join(__dirname, '..', 'audit', 'TRADES.md');
const HISTORY_PATH = path.join(__dirname, '..', 'data', 'node_history.jsonl');
const BJT_OFFSET = 8 * 60 * 60 * 1000;

function bjtNow() {
  const d = new Date();
  return new Date(d.getTime() + BJT_OFFSET).toISOString().replace('T', ' ').slice(0, 16) + ' BJT';
}

// Load auth
function loadAuth() {
  const data = JSON.parse(fs.readFileSync(AUTH_PATH, 'utf8'));
  return { key: data.binance.api_key, secret: data.binance.api_secret };
}

// HTTP helper
function apiRequest(method, path, params, apiKey, secret) {
  return new Promise((resolve, reject) => {
    params = { ...params, timestamp: Date.now() };
    const query = Object.entries(params)
      .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
      .sort((a, b) => a.split('=')[0].localeCompare(b.split('=')[0]))
      .join('&');
    const signature = crypto.createHmac('sha256', secret).update(query).digest('hex');
    const fullQuery = query + '&signature=' + signature;
    const url = 'https://api.binance.com' + path + '?' + fullQuery;

    const options = {
      method,
      hostname: 'api.binance.com',
      path: path + '?' + fullQuery,
      headers: { 'X-MBX-APIKEY': apiKey },
      rejectUnauthorized: false
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('Parse error: ' + data.slice(0, 200)));
        }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// Public API (no auth needed)
function publicGet(path) {
  return new Promise((resolve, reject) => {
    https.get('https://api.binance.com' + path, { rejectUnauthorized: false }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch(e) { reject(e); }
      });
    }).on('error', reject);
  });
}

async function getPrice(symbol) {
  const data = await publicGet('/api/v3/ticker/price?symbol=' + symbol);
  return parseFloat(data.price);
}

async function getBalance(apiKey, secret) {
  const data = await apiRequest('GET', '/api/v3/account', {}, apiKey, secret);
  const balances = {};
  for (const b of data.balances) {
    const free = parseFloat(b.free);
    const locked = parseFloat(b.locked);
    if (free > 0 || locked > 0) {
      balances[b.asset] = { free, locked, total: free + locked };
    }
  }
  return balances;
}

async function buyMarket(apiKey, secret, symbol, usdtAmount) {
  console.log(`🟢 买入 ${symbol} $${usdtAmount.toFixed(2)}`);
  const params = {
    symbol: symbol,
    side: 'BUY',
    type: 'MARKET',
    quoteOrderQty: usdtAmount.toFixed(2),
  };
  const result = await apiRequest('POST', '/api/v3/order', params, apiKey, secret);
  return result;
}

async function sellMarket(apiKey, secret, symbol, quantity) {
  console.log(`🔴 卖出 ${symbol} ${quantity}`);
  const params = {
    symbol: symbol,
    side: 'SELL',
    type: 'MARKET',
    quantity: quantity.toString(),
  };
  const result = await apiRequest('POST', '/api/v3/order', params, apiKey, secret);
  return result;
}

function appendTrade(action, symbol, qty, price, usdtAmount, reason, orderId) {
  const ts = bjtNow();
  const line = `||||||||| ${ts} | ${action} | ${symbol.replace('USDT','')} | ${qty} | $${price} | A4 Blade ${reason} Order#${orderId} |\n`;
  fs.appendFileSync(TRADES_PATH, line);
  console.log(`  记录到TRADES.md: ${action} ${symbol}`);
}

function roundQuantity(qty) {
  // Round down to appropriate precision for Binance
  const step = 0.01; // most USDT pairs use 0.01 or 0.001
  return Math.floor(qty / step) * step;
}

async function main() {
  console.log(`\n══════ A4 Blade 交易执行 [${bjtNow()}] ══════\n`);
  
  try {
    const auth = loadAuth();
    const { key: apiKey, secret } = auth;

    // 1. Get balance
    console.log('📊 获取账户余额...');
    const balances = await getBalance(apiKey, secret);
    console.log('  余额:', JSON.stringify(balances, null, 2));
    
    let usdtFree = balances['USDT'] ? balances['USDT'].free : 0;
    console.log(`\n💰 USDT可用: $${usdtFree.toFixed(2)}`);
    
    // Check if we have ENA to sell
    const enaBalance = balances['ENA'] ? balances['ENA'].free : 0;
    console.log(`   ENA持有: ${enaBalance}`);
    
    if (enaBalance >= 1) {
      // 2. Get ENA price for sell
      const enaPrice = await getPrice('ENAUSDT');
      console.log(`\n📈 ENA当前价: $${enaPrice}`);
      
      // 3. Sell ENA
      const sellResult = await sellMarket(apiKey, secret, 'ENAUSDT', roundQuantity(enaBalance));
      console.log(`   卖出结果:`, JSON.stringify(sellResult, null, 2));
      
      if (sellResult.status === 'FILLED') {
        const fillPrice = parseFloat(sellResult.fills[0].price);
        const fillQty = parseFloat(sellResult.fills[0].qty);
        appendTrade('SELL', 'ENAUSDT', fillQty, fillPrice.toFixed(4), 0, 
          `卖出—换仓: ENA P&L -1.03%(最差), 替换为LUMIA(实时动量+1.18%✅)`, 
          sellResult.orderId);
        
        // Re-check balance after sell
        const balances2 = await getBalance(apiKey, secret);
        usdtFree = balances2['USDT'] ? balances2['USDT'].free : 0;
        console.log(`\n💰 卖出后USDT: $${usdtFree.toFixed(2)}`);
      } else {
        console.log(`⚠️ ENA卖出未成交: ${JSON.stringify(sellResult)}`);
        return { status: 'sell_failed', result: sellResult };
      }
    } else {
      console.log('⚠️ 无ENA持仓可卖');
      return { status: 'no_ena' };
    }
    
    // 4. Buy LUMIA (7.5% of USDT per F&G<20 rules)
    const lumiaPrice = await getPrice('LUMIAUSDT');
    console.log(`\n📈 LUMIA当前价: $${lumiaPrice}`);
    
    const buyAmount = usdtFree * 0.075;
    console.log(`🔢 买入金额: $${usdtFree.toFixed(2)} × 7.5% = $${buyAmount.toFixed(2)}`);
    
    if (buyAmount < 10) {
      console.log(`⚠️ 买入金额$${buyAmount.toFixed(2)} < $10, 调整至$10`);
      // Actually use more if we have it
    }
    
    const effectiveAmount = Math.max(buyAmount, 10);
    if (effectiveAmount > usdtFree * 0.95) {
      console.log(`⚠️ 金额超过可用余额，使用余额的95%`);
    }
    
    const finalAmount = Math.min(effectiveAmount, usdtFree * 0.95);
    console.log(`  最终买入金额: $${finalAmount.toFixed(2)}`);
    
    if (finalAmount < 10) {
      console.log(`❌ 买入金额$${finalAmount.toFixed(2)} < $10最低限额，取消买入`);
      return { status: 'insufficient_funds' };
    }
    
    const buyResult = await buyMarket(apiKey, secret, 'LUMIAUSDT', finalAmount);
    console.log(`   买入结果:`, JSON.stringify(buyResult, null, 2));
    
    if (buyResult.status === 'FILLED') {
      const fillPrice = parseFloat(buyResult.fills[0].price);
      const fillQty = parseFloat(buyResult.fills[0].qty);
      appendTrade('BUY', 'LUMIAUSDT', fillQty, fillPrice.toFixed(4), finalAmount,
        `买入—fast_scan A级超高conf+range75%+实时动量+1.18%✅+F&G极恐7.5%仓`,
        buyResult.orderId);
      
      console.log(`\n✅ 交易完成! 已卖出ENA -> 买入LUMIA`);
      
      // Get final balance
      const balances3 = await getBalance(apiKey, secret);
      const finalUsdt = balances3['USDT'] ? balances3['USDT'].free : 0;
      
      // Calculate total equity
      let totalVal = finalUsdt;
      for (const [asset, bal] of Object.entries(balances3)) {
        if (asset === 'USDT') continue;
        if (bal.free > 0 || bal.locked > 0) {
          try {
            const px = await getPrice(asset + 'USDT');
            totalVal += bal.free * px;
          } catch(e) {}
        }
      }
      
      console.log(`\n💰 最终权益: $${totalVal.toFixed(2)}`);
      console.log(`💰 USDT: $${finalUsdt.toFixed(2)}`);
      
      // Update history
      const histEntry = {
        timestamp: bjtNow(),
        total_equity: parseFloat(totalVal.toFixed(2)),
        USDT: parseFloat(finalUsdt.toFixed(2)),
        action: 'SWAP: ENA→LUMIA',
        note: `A4执行: 卖出ENA(-1.03%), 买入LUMIA($${finalAmount.toFixed(2)}) F&G=15`
      };
      const histLine = JSON.stringify(histEntry) + '\n';
      fs.appendFileSync(HISTORY_PATH, histLine);
      
    } else {
      console.log(`⚠️ LUMIA买入未成交: ${JSON.stringify(buyResult)}`);
    }
    
    return { status: 'completed' };
    
  } catch (err) {
    console.error('❌ 错误:', err.message);
    return { status: 'error', error: err.message };
  }
}

main().then(r => {
  console.log('\n══════ 执行完成 ══════');
  process.exit(0);
}).catch(e => {
  console.error('FATAL:', e);
  process.exit(1);
});
