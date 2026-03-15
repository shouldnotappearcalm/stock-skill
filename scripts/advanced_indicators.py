#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中长线技术指标计算
供 long_term_selector / enhanced_long_term_selector 使用
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List


class AdvancedIndicators:
    def score_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 60:
            return {'score': 0, 'rating': '未知', 'reasons': [], 'ma20': 0, 'ma60': 0}
        close = df['close']
        ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else float(close.iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else float(close.iloc[-1])
        price = float(close.iloc[-1])
        reasons: List[str] = []
        score = 50
        if price > ma20:
            score += 15
            reasons.append('站上MA20')
        if price > ma60:
            score += 20
            reasons.append('站上MA60')
        if ma20 > ma60:
            score += 15
            reasons.append('均线多头')
        score = max(0, min(100, score))
        if score >= 80:
            rating = '强势'
        elif score >= 60:
            rating = '偏多'
        elif score >= 40:
            rating = '中性'
        else:
            rating = '偏弱'
        return {'score': score, 'rating': rating, 'reasons': reasons, 'ma20': ma20, 'ma60': ma60}

    def calc_obv(self, df: pd.DataFrame) -> pd.Series:
        direction = np.sign(df['close'].diff())
        direction.iloc[0] = 0
        obv = (direction * df['volume']).cumsum()
        return obv

    def calc_volume_ratio(self, df: pd.DataFrame, window: int = 5) -> pd.Series:
        vol = df['volume']
        avg = vol.rolling(window).mean().shift(1)
        ratio = vol / avg.replace(0, np.nan)
        return ratio.fillna(1.0)

    def calc_adx(self, df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        high, low, close = df['high'], df['low'], df['close']
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        plus_dm = high.diff().where(high.diff() > low.diff().abs(), 0).clip(lower=0)
        minus_dm = low.diff().where(low.diff() > high.diff().abs(), 0).clip(lower=0)
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan))
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr.replace(0, np.nan))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(span=period, adjust=False).mean()
        return adx.fillna(0), plus_di.fillna(0), minus_di.fillna(0)

    def calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    def calc_bias(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        close = df['close']
        ma = close.rolling(period).mean()
        bias = (close - ma) / ma.replace(0, np.nan) * 100
        return bias.fillna(0)
