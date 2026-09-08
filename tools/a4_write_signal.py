import json
import os

SEQ = 68 # next sequence after 67
USDT_AMOUNT = 32.19  # USDT x 20%, RL5 pass (loss $1.61 < $2.28)

signal = {
    'signal_id': f'sig_20260607_0100_{SEQ}',
    'generated_at': '2026-06-07T01:00:00+08:00',
    'a4_cycle': f'2026-06-07 01:00 BJT (Cycle #{SEQ})',
    'sequence': SEQ,
    'buy_signals': [
        {
            'coin': 'XLM',
            'usdt_amount': USDT_AMOUNT,
            'confidence': 9,
            'tags': ['just_starting+8.5%', '放量突破量比1.9x', '全周期↑', 'RSI55', '独立于BTC', 'STRONG105', 'layer1'],
            'entry_reason': '刚启动8.5%+放量突破+趋势向上+RSI回升—最高分105STRONG·最佳候选'
        }
    ],
    'sell_signals': [],
    'position_eval': {
        'positions_count': 2,
        'coins': ['C', 'JST'],
        'usdt_balance': 160.93,
        'action_summary': 'HOLD C + JST, BUY XLM $32.19'
    }
}

path = 'data/signals/a4_signals.json'
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    json.dump(signal, f, indent=2, ensure_ascii=False)
print(f'✅ Written: {path}')
print(f'Signal: {signal["signal_id"]}')
print(f'BUY XLM ${USDT_AMOUNT} conf=9')
