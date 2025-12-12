"""
交易日計算工具
"""

import logging
from datetime import datetime
from typing import Union

import pandas_market_calendars as mcal

logger = logging.getLogger(__name__)


class TradingDaysCalculator:
    """使用交易所行事曆計算交易日數量"""

    def __init__(self, exchange: str = 'NYSE'):
        self.exchange = exchange
        try:
            self.calendar = mcal.get_calendar(exchange)
            logger.info("✓ 交易日曆已載入: %s", exchange)
        except Exception as exc:
            logger.error("✗ 無法載入交易日曆 (%s): %s", exchange, exc)
            raise

    def calculate_trading_days(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime]
    ) -> int:
        """
        計算兩日期之間的交易日天數（包含起始日和結束日）
        若計算失敗，回退為日曆日差。
        """
        try:
            start_str = self._to_datestr(start_date)
            end_str = self._to_datestr(end_date)
            schedule = self.calendar.schedule(
                start_date=start_str,
                end_date=end_str
            )
            trading_days = len(schedule)
            logger.debug(
                "計算交易日: %s → %s = %d 天",
                start_str,
                end_str,
                trading_days
            )
            return trading_days
        except Exception as exc:
            logger.warning(
                "⚠ 無法計算交易日，改用日曆日估算交易日: %s", exc
            )
            start_dt = self._to_datetime(start_date)
            end_dt = self._to_datetime(end_date)
            calendar_days = max(0, (end_dt.date() - start_dt.date()).days)
            # 使用 5/7 比例估算交易日（排除週末）
            # 這比直接使用日曆日更準確
            estimated_trading_days = int(calendar_days * 5 / 7)
            logger.debug(
                "日曆日 %d 天 → 估算交易日 %d 天 (5/7 比例)",
                calendar_days,
                estimated_trading_days
            )
            return estimated_trading_days

    @staticmethod
    def _to_datestr(value: Union[str, datetime]) -> str:
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        return str(value)

    @staticmethod
    def _to_datetime(value: Union[str, datetime]) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.strptime(str(value), '%Y-%m-%d')

