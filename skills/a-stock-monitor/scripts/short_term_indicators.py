#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短线技术指标计算
供 short_term_selector 使用
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any


class ShortTermIndicators:
    def calc_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def calc_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        low_min = df['low'].rolling(n).min()
        high_max = df['high'].rolling(n).max()
        rsv = (df['close'] - low_min) / (high_max - low_min).replace(0, np.nan) * 100
        rsv = rsv.fillna(50)
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j

    def detect_kdj_cross(self, k: pd.Series, d: pd.Series, j: pd.Series) -> Dict[str, Any]:
        k_now, d_now, j_now = float(k.iloc[-1]), float(d.iloc[-1]), float(j.iloc[-1])
        k_prev, d_prev = float(k.iloc[-2]) if len(k) >= 2 else k_now, float(d.iloc[-2]) if len(d) >= 2 else d_now
        golden_cross = k_prev <= d_prev and k_now > d_now
        death_cross = k_prev >= d_prev and k_now < d_now
        oversold = j_now < 20
        overbought = j_now > 80
        signal = None
        if golden_cross:
            signal = 'KDJ金叉'
        elif death_cross:
            signal = 'KDJ死叉'
        score = 0
        if golden_cross and j_now < 50:
            score = 20
        elif oversold:
            score = 15
        return {
            'golden_cross': golden_cross,
            'death_cross': death_cross,
            'oversold': oversold,
            'overbought': overbought,
            'k': k_now,
            'd': d_now,
            'j': j_now,
            'signal': signal,
            'score': score,
        }

    def calc_macd_short(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = (dif - dea) * 2
        return dif, dea, macd_hist

    def detect_macd_cross(self, dif: pd.Series, dea: pd.Series, macd_hist: pd.Series) -> Dict[str, Any]:
        d, de, hist = float(dif.iloc[-1]), float(dea.iloc[-1]), float(macd_hist.iloc[-1])
        d_prev, de_prev = (float(dif.iloc[-2]), float(dea.iloc[-2])) if len(dif) >= 2 else (d, de)
        golden_cross = d_prev <= de_prev and d > de
        death_cross = d_prev >= de_prev and d < de
        signal = None
        if hist > 0 and (len(macd_hist) < 2 or macd_hist.iloc[-2] <= 0):
            signal = 'MACD翻红'
        elif hist < 0 and (len(macd_hist) < 2 or macd_hist.iloc[-2] >= 0):
            signal = 'MACD翻绿'
        return {
            'golden_cross': golden_cross,
            'death_cross': death_cross,
            'dif': d,
            'dea': de,
            'macd_hist': hist,
            'signal': signal,
        }

    def calc_bollinger(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = df['close'].rolling(period).mean()
        std = df['close'].rolling(period).std().fillna(0)
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower

    def detect_bollinger_signal(self, df: pd.DataFrame, upper: pd.Series, middle: pd.Series, lower: pd.Series) -> Dict[str, Any]:
        close = df['close'].iloc[-1]
        u, m, l = float(upper.iloc[-1]), float(middle.iloc[-1]), float(lower.iloc[-1])
        if u == l:
            position_pct = 50.0
            bandwidth = 0.0
        else:
            position_pct = max(0, min(100, (close - l) / (u - l) * 100))
            bandwidth = (u - l) / m * 100 if m else 0
        signal = None
        if close <= l:
            signal = '跌破下轨'
        elif len(df) >= 2 and df['close'].iloc[-2] <= lower.iloc[-2] and close > l:
            signal = '下轨反弹'
        elif close >= u:
            signal = '触及上轨'
        elif m and abs(close - m) / m < 0.02:
            signal = '中轨支撑'
        return {
            'signal': signal or '',
            'upper': u,
            'middle': m,
            'lower': l,
            'bandwidth': bandwidth,
            'position_pct': float(position_pct),
        }

    def detect_volume_surge(self, df: pd.DataFrame, ratio: float = 1.5) -> Dict[str, Any]:
        if len(df) < 2:
            return {'surge_type': '', 'volume_ratio': 1.0, 'price_change': 0.0}
        vol_now = df['volume'].iloc[-1]
        vol_avg = df['volume'].iloc[:-1].tail(5).mean() if len(df) > 1 else vol_now
        vol_ratio = (vol_now / vol_avg) if vol_avg and vol_avg > 0 else 1.0
        price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100 if len(df) >= 2 else 0.0
        surge_type = ''
        if vol_ratio >= ratio and price_change > 0:
            surge_type = '放量上涨'
        elif vol_ratio >= ratio and price_change < 0:
            surge_type = '放量下跌'
        elif vol_ratio < 0.7 and price_change > 0:
            surge_type = '缩量上涨'
        return {'surge_type': surge_type, 'volume_ratio': vol_ratio, 'price_change': price_change}

    def calc_atr_short(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean()
        return atr

    def calc_trade_points(
        self,
        current_price: float,
        atr_now: float,
        stop_multiplier: float = 2.0,
        profit_multiplier: float = 3.0,
    ) -> Dict[str, Any]:
        if atr_now <= 0:
            atr_now = current_price * 0.02
        stop_loss = round(current_price - stop_multiplier * atr_now, 2)
        take_profit = round(current_price + profit_multiplier * atr_now, 2)
        stop_loss_pct = (stop_loss - current_price) / current_price * 100 if current_price else 0
        take_profit_pct = (take_profit - current_price) / current_price * 100 if current_price else 0
        atr_pct = (atr_now / current_price) * 100 if current_price else 0
        return {
            'buy_price': round(current_price, 2),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'stop_loss_pct': round(stop_loss_pct, 2),
            'take_profit_pct': round(take_profit_pct, 2),
            'atr': round(atr_now, 4),
            'atr_pct': round(atr_pct, 2),
            'risk_reward_ratio': abs(profit_multiplier / stop_multiplier) if stop_multiplier else 0,
        }
