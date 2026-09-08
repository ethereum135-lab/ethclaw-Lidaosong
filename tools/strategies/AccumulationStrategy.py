# pragma pylint: disable=missing-docstring, invalid-name
"""
ZQ 吸筹策略 — Freqtrade策略 v1.0

入场逻辑（吸筹评分）：
  ① 量比 0.8~1.5x（有量但还没爆）
  ② 4h趋势向上（EMA8斜率向上）
  ③ RSI 30~60（没超买）
  ④ 24h涨幅 -5%~+5%（还没涨过）
  ⑤ 价格位置 < 70%（不在近期高点）

出场逻辑（方向持有）：
  P1: 4h趋势转跌（EMA8斜率向下）→ 卖出
  P2: RSI > 80 → 超买止盈
  E5: 24h跌超-8% → 止损
  其他机械出场(E2/E3/E4) → 被方向判断覆盖，不触发
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, CategoricalParameter
from pandas import DataFrame
from functools import reduce
import talib.abstract as ta
import numpy as np


class AccumulationStrategy(IStrategy):
    """
    吸筹策略 — 蓄力阶段埋伏，方向持有。
    """
    
    # ─── 策略元数据 ───
    INTERFACE_VERSION = 3
    
    # ─── 仓位管理 ───
    max_open_trades = 3
    stake_amount = 50
    position_adjustment_enable = False
    
    # ─── 风控 ───
    stoploss = -0.15          # 硬止损15%（最后防线）
    trailing_stop = False
    use_custom_stoploss = False
    minimal_roi = {}
    
    # ─── 时间框架 ───
    timeframe = '30m'
    
    # ─── 回测配置 ───
    process_only_new_candles = True
    use_exit_signal = True
    startup_candle_count = 48  # 需要48根K线预热（24h数据）
    
    # ─── 可调参数 ───
    buy_vol_min = DecimalParameter(0.6, 1.5, default=0.8, space='buy')
    buy_vol_max = DecimalParameter(1.2, 2.5, default=1.8, space='buy')
    buy_rsi_min = IntParameter(20, 40, default=30, space='buy')
    buy_rsi_max = IntParameter(55, 70, default=60, space='buy')
    buy_change_min = DecimalParameter(-8, -2, default=-5, space='buy')
    buy_change_max = DecimalParameter(3, 8, default=5, space='buy')
    
    sell_4h_trend = IntParameter(-2, 0, default=-1, space='sell')
    sell_rsi_overbought = IntParameter(75, 85, default=80, space='sell')
    sell_stop_loss = DecimalParameter(-10, -5, default=-8, space='sell')
    
    # ─── 指标计算 ───
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算所有指标：RSI、量比、趋势、涨幅、价格位置
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 成交量相关
        dataframe['volume_ma'] = dataframe['volume'].rolling(window=10).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_ma']
        dataframe['volume_ma_48'] = dataframe['volume'].rolling(window=48).mean()
        dataframe['volume_ratio_48'] = dataframe['volume'] / dataframe['volume_ma_48']
        
        # 24h涨幅（48根30m K线 = 24h）
        dataframe['change_24h'] = (dataframe['close'] - dataframe['close'].shift(48)) / dataframe['close'].shift(48) * 100
        
        # 价格位置（24h高低区间中的位置）
        dataframe['high_24'] = dataframe['high'].rolling(window=48).max()
        dataframe['low_24'] = dataframe['low'].rolling(window=48).min()
        dataframe['price_position'] = (dataframe['close'] - dataframe['low_24']) / (dataframe['high_24'] - dataframe['low_24'])
        
        # 4h EMA趋势（从30m聚合到4h）
        # 4h = 8根30m K线
        dataframe['ema_8'] = ta.EMA(dataframe['close'], timeperiod=8)
        dataframe['ema_4h'] = dataframe['ema_8'].shift(0)  # 8-period EMA on 30m ≈ 4h EMA
        
        # 4h趋势：EMA斜率（用最近3根EMA的差值判断方向）
        dataframe['ema_slope'] = dataframe['ema_4h'] - dataframe['ema_4h'].shift(3)
        dataframe['trend_4h'] = 0
        dataframe.loc[dataframe['ema_slope'] > dataframe['ema_slope'].rolling(48).mean() * 0.5, 'trend_4h'] = 1
        dataframe.loc[dataframe['ema_slope'] < -dataframe['ema_slope'].rolling(48).mean() * 0.5, 'trend_4h'] = -1
        
        # 简化版4h趋势（直接看EMA方向）
        dataframe['ema_4h_slope'] = dataframe['ema_4h'] - dataframe['ema_4h'].shift(8)
        dataframe['ema_4h_direction'] = 0
        dataframe.loc[dataframe['ema_4h_slope'] > 0, 'ema_4h_direction'] = 1
        dataframe.loc[dataframe['ema_4h_slope'] < 0, 'ema_4h_direction'] = -1
        
        # 大盘方向（从BTC的4h趋势来）
        # 注意：这里需要pair级别的处理，在entry_trend里做
        
        return dataframe
    
    # ─── 入场条件 ───
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        吸筹入场条件（全部AND）：
          ① 量比在 0.8~1.5x 之间
          ② 4h趋势向上（ema_4h_direction == 1）
          ③ RSI 在 30~60 之间
          ④ 24h涨幅在 -5%~+5% 之间
          ⑤ 价格位置 < 0.7（不在高位）
          ⑥ 吸筹评分 >= 60（强蓄力信号）
        """
        # 计算综合吸筹评分
        dataframe['acc_score'] = 0
        
        # 量比评分
        dataframe['acc_vol'] = 0
        dataframe.loc[(dataframe['volume_ratio'] >= 0.8) & (dataframe['volume_ratio'] <= 1.5), 'acc_vol'] = 25
        dataframe.loc[(dataframe['volume_ratio'] > 1.5) & (dataframe['volume_ratio'] <= 2.0), 'acc_vol'] = 10
        dataframe.loc[dataframe['volume_ratio'] > 2.0, 'acc_vol'] = -10
        dataframe.loc[dataframe['volume_ratio'] < 0.8, 'acc_vol'] = -5
        
        # 趋势评分
        dataframe['acc_trend'] = 0
        dataframe.loc[dataframe['ema_4h_direction'] == 1, 'acc_trend'] = 20
        dataframe.loc[dataframe['ema_4h_direction'] == -1, 'acc_trend'] = -20
        
        # RSI评分
        dataframe['acc_rsi'] = 0
        dataframe.loc[(dataframe['rsi'] >= 30) & (dataframe['rsi'] <= 50), 'acc_rsi'] = 25
        dataframe.loc[(dataframe['rsi'] > 50) & (dataframe['rsi'] <= 60), 'acc_rsi'] = 15
        dataframe.loc[dataframe['rsi'] > 70, 'acc_rsi'] = -10
        
        # 涨幅评分
        dataframe['acc_chg'] = 0
        dataframe.loc[(dataframe['change_24h'] >= -3) & (dataframe['change_24h'] <= 3), 'acc_chg'] = 20
        dataframe.loc[(dataframe['change_24h'] > 3) & (dataframe['change_24h'] <= 8), 'acc_chg'] = 10
        dataframe.loc[dataframe['change_24h'] > 15, 'acc_chg'] = -15
        
        # 价格位置评分
        dataframe['acc_pos'] = 0
        dataframe.loc[dataframe['price_position'] < 0.3, 'acc_pos'] = 15
        dataframe.loc[(dataframe['price_position'] >= 0.3) & (dataframe['price_position'] < 0.5), 'acc_pos'] = 10
        dataframe.loc[dataframe['price_position'] > 0.7, 'acc_pos'] = -10
        
        # 总评分
        dataframe['acc_score'] = (dataframe['acc_vol'] + dataframe['acc_trend'] + 
                                  dataframe['acc_rsi'] + dataframe['acc_chg'] + dataframe['acc_pos'])
        
        conditions = []
        
        # ① 量比
        conditions.append(dataframe['volume_ratio'] >= self.buy_vol_min.value)
        conditions.append(dataframe['volume_ratio'] <= self.buy_vol_max.value)
        
        # ② 4h趋势向上
        conditions.append(dataframe['ema_4h_direction'] == 1)
        
        # ③ RSI
        conditions.append(dataframe['rsi'] >= self.buy_rsi_min.value)
        conditions.append(dataframe['rsi'] <= self.buy_rsi_max.value)
        
        # ④ 24h涨幅
        conditions.append(dataframe['change_24h'] >= self.buy_change_min.value)
        conditions.append(dataframe['change_24h'] <= self.buy_change_max.value)
        
        # ⑤ 价格位置 < 0.7
        conditions.append(dataframe['price_position'] < 0.7)
        
        # ⑥ 吸筹评分 >= 60
        conditions.append(dataframe['acc_score'] >= 60)
        
        # ⑦ 确保有足够的数据预热
        conditions.append(dataframe['volume'] > 0)
        
        # 组合所有条件
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1
        
        return dataframe
    
    # ─── 出场条件 ───
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        出场条件（OR）：
          P1: 4h趋势转跌（ema_4h_direction == -1）— 主要出场信号
          P2: RSI > 80 → 超买止盈
          E5: 24h跌超-8% → 止损
        """
        conditions = []
        
        # P1: 4h趋势转跌
        conditions.append(dataframe['ema_4h_direction'] == -1)
        
        # P2: RSI超买
        conditions.append(dataframe['rsi'] > self.sell_rsi_overbought.value)
        
        # E5: 止损
        conditions.append(dataframe['change_24h'] < self.sell_stop_loss.value)
        
        # 组合（OR）
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'exit_long'] = 1
        
        return dataframe
