#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中长线高级指标（DMI/PEG/信号优化）
供 enhanced_long_term_selector 使用，与 advanced_indicators 配合
"""

import pandas as pd
from typing import Tuple, Dict, Any
from advanced_indicators import AdvancedIndicators


class AdvancedLongTermIndicators:
    def __init__(self):
        self._base = AdvancedIndicators()

    def calc_dmi(self, df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        adx, plus_di, minus_di = self._base.calc_adx(df, period=period)
        return plus_di, minus_di, adx

    def analyze_dmi_signal(
        self, plus_di: float, minus_di: float, adx: float
    ) -> Dict[str, Any]:
        signal = 'neutral'
        strength = '中性'
        if adx > 25 and plus_di > minus_di:
            diff = plus_di - minus_di
            signal = 'strong_buy' if diff > 10 else 'buy'
            strength = '强' if diff > 10 else '弱'
        elif adx > 25 and minus_di > plus_di:
            diff = minus_di - plus_di
            signal = 'strong_sell' if diff > 10 else 'sell'
            strength = '强' if diff > 10 else '弱'
        return {
            'signal': signal,
            'strength': strength,
            'plus_di': plus_di,
            'minus_di': minus_di,
            'adx': adx
        }

    def optimize_signal_trigger(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        buy_count = sum(
            1 for s in signals.values()
            if isinstance(s, dict) and s.get('signal') in ('buy', 'strong_buy')
        )
        reasons = []
        if buy_count >= 3:
            decision = '强烈买入'
            reasons.append('多维度共振')
        elif buy_count >= 2:
            decision = '买入'
            reasons.append('部分指标支持')
        elif buy_count >= 1:
            decision = '观望'
        else:
            decision = '卖出'
        return {'decision': decision, 'reasons': reasons}

    def calc_peg_ratio(self, pe: float, growth: float) -> Dict[str, Any]:
        if pe is None or growth is None or growth <= 0:
            return {'peg': None}
        peg = pe / growth
        return {'peg': peg}
