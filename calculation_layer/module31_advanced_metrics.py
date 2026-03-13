#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module 31: Advanced Metrics

Features:
1. Put/Call Ratio (PCR)
2. Max Pain
3. Gamma Exposure (GEX)
"""

import logging
from dataclasses import dataclass
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MarketMetrics:
    """Container for advanced market metrics."""

    pcr_volume: float = 0.0
    pcr_oi: float = 0.0
    max_pain: float = 0.0
    total_gex: float = 0.0
    gex_profile: Dict[float, float] = None

    def to_dict(self) -> Dict:
        return {
            'pcr_volume': round(self.pcr_volume, 2),
            'pcr_oi': round(self.pcr_oi, 2),
            'max_pain': round(self.max_pain, 2),
            'total_gex': round(self.total_gex, 0),
            'gex_profile': self.gex_profile,
        }


class AdvancedMetricsAnalyzer:
    """Analyze PCR, Max Pain and Gamma Exposure."""

    def __init__(self):
        logger.info("Advanced Metrics analyzer initialized")

    def calculate_metrics(
        self,
        calls_df: pd.DataFrame,
        puts_df: pd.DataFrame,
        current_price: float,
    ) -> MarketMetrics:
        """Calculate advanced option market metrics."""
        try:
            metrics = MarketMetrics()

            metrics.pcr_volume = self._calculate_pcr(calls_df, puts_df, metric='volume')
            metrics.pcr_oi = self._calculate_pcr(calls_df, puts_df, metric='openInterest')
            metrics.max_pain = self._calculate_max_pain(calls_df, puts_df)
            metrics.total_gex, metrics.gex_profile = self._calculate_gex(
                calls_df, puts_df, current_price
            )

            logger.info(
                "Advanced metrics calculated: PCR(Vol)=%.2f, Max Pain=$%.2f, Total GEX=$%.1fM",
                metrics.pcr_volume,
                metrics.max_pain,
                metrics.total_gex / 1e6,
            )
            return metrics

        except Exception as e:
            logger.error(f"Advanced metrics calculation failed: {e}")
            return MarketMetrics()

    def _calculate_pcr(self, calls: pd.DataFrame, puts: pd.DataFrame, metric: str = 'volume') -> float:
        """Calculate Put/Call Ratio for volume or open interest."""
        try:
            call_total = calls[metric].sum() if not calls.empty and metric in calls.columns else 0
            put_total = puts[metric].sum() if not puts.empty and metric in puts.columns else 0

            if call_total > 0:
                return round(put_total / call_total, 4)
            return 0.0
        except Exception as e:
            logger.warning(f"PCR calculation failed ({metric}): {e}")
            return 0.0

    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame) -> float:
        """Calculate Max Pain while tolerating missing openInterest data."""
        try:
            call_strikes = calls['strike'].dropna().tolist() if 'strike' in calls.columns else []
            put_strikes = puts['strike'].dropna().tolist() if 'strike' in puts.columns else []
            strikes = sorted(set(call_strikes + put_strikes))
            if not strikes:
                return 0.0

            if 'openInterest' in calls.columns:
                calls_oi_series = calls['openInterest'].fillna(0)
            else:
                calls_oi_series = pd.Series(0.0, index=calls.index, dtype=float)

            if 'openInterest' in puts.columns:
                puts_oi_series = puts['openInterest'].fillna(0)
            else:
                puts_oi_series = pd.Series(0.0, index=puts.index, dtype=float)

            calls_oi = dict(zip(calls['strike'], calls_oi_series)) if 'strike' in calls.columns else {}
            puts_oi = dict(zip(puts['strike'], puts_oi_series)) if 'strike' in puts.columns else {}

            if not any(calls_oi.values()) and not any(puts_oi.values()):
                logger.info("Max Pain skipped: option chain missing openInterest data")
                return 0.0

            min_pain = float('inf')
            max_pain_price = 0.0

            for price in strikes:
                pain = 0.0

                for strike, oi in calls_oi.items():
                    if price > strike:
                        pain += (price - strike) * oi

                for strike, oi in puts_oi.items():
                    if price < strike:
                        pain += (strike - price) * oi

                if pain < min_pain:
                    min_pain = pain
                    max_pain_price = price

            return max_pain_price

        except Exception as e:
            logger.warning(f"Max Pain calculation failed: {e}")
            return 0.0

    def _calculate_gex(self, calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> tuple:
        """Calculate net gamma exposure and a strike-by-strike GEX profile."""
        try:
            total_gex = 0.0
            gex_profile = {}

            if 'gamma' in calls.columns:
                for _, row in calls.iterrows():
                    strike = row['strike']
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    gex = gamma * oi * 100 * current_price

                    total_gex += gex
                    gex_profile[strike] = gex_profile.get(strike, 0) + gex

            if 'gamma' in puts.columns:
                for _, row in puts.iterrows():
                    strike = row['strike']
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    gex = -(gamma * oi * 100 * current_price)

                    total_gex += gex
                    gex_profile[strike] = gex_profile.get(strike, 0) + gex

            return total_gex, gex_profile

        except Exception as e:
            logger.warning(f"GEX calculation failed: {e}")
            return 0.0, {}
