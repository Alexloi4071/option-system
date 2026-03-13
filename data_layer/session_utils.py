"""
session_utils.py
----------------
Utility for classifying the current market session type based on
US Eastern Time (ET). Used to enforce appropriate data quality
rules and strategy restrictions for each session.

Session Definitions (Eastern Time):
  - primary_session:  Mon-Fri  09:30 – 16:15
  - premarket:        Mon-Fri  04:00 – 09:30
  - overnight:        Mon-Fri  20:00 – 24:00 / 00:00 – 04:00
  - closed:           Weekends / holidays
"""

from datetime import datetime, time
import pytz
from typing import Literal, Optional, Union

SessionType = Literal["primary", "premarket", "overnight", "closed"]

ET_TZ = pytz.timezone("America/New_York")

# Session time boundaries (Eastern Time, 24-hour)
_PRIMARY_START   = time(9, 30)
_PRIMARY_END     = time(16, 15)
_PREMARKET_START = time(4, 0)
_PREMARKET_END   = time(9, 30)
_OVERNIGHT_START = time(20, 0)  # Day boundary: 20:00 ET onwards is overnight

# Bid/Ask spread threshold above which a quote is considered low-quality
# during non-primary sessions (expressed as fraction of mid price)
OVERNIGHT_SPREAD_THRESHOLD = 0.01   # 1%
PRIMARY_SPREAD_THRESHOLD   = 0.05   # 5%  (more lenient during day)


def get_session_type(dt: Optional[datetime] = None) -> SessionType:
    """
    Return the current (or provided) US market session type.

    Parameters
    ----------
    dt : datetime, optional
        UTC-aware or naive datetime. Defaults to ``datetime.utcnow()`` (UTC).

    Returns
    -------
    SessionType
        One of "primary", "premarket", "overnight", or "closed".
    """
    if dt is None:
        dt = datetime.utcnow().replace(tzinfo=pytz.utc)

    # Make timezone-aware if naive (assume UTC)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    et = dt.astimezone(ET_TZ)
    weekday = et.weekday()   # 0=Mon … 6=Sun
    t = et.time()

    # Weekend → closed
    if weekday >= 5:
        return "closed"

    # Primary session: 09:30 – 16:15 ET
    if _PRIMARY_START <= t < _PRIMARY_END:
        return "primary"

    # Pre-market: 04:00 – 09:30 ET
    if _PREMARKET_START <= t < _PREMARKET_END:
        return "premarket"

    # Overnight: 20:00 – 04:00 ET (spans midnight)
    if t >= _OVERNIGHT_START or t < _PREMARKET_START:
        return "overnight"

    # Gap between 16:15 – 20:00 → closed (after-hours/early evening)
    return "closed"


def is_primary_session(dt: Optional[datetime] = None) -> bool:
    """Return True if we are inside the primary US trading session."""
    return get_session_type(dt) == "primary"


def is_overnight_session(dt: Optional[datetime] = None) -> bool:
    """Return True if we are in the overnight window (20:00–04:00 ET)."""
    return get_session_type(dt) == "overnight"


def is_non_primary_session(dt: Optional[datetime] = None) -> bool:
    """Return True if we are OUTSIDE the primary session (any off-hours)."""
    return get_session_type(dt) != "primary"


def get_spread_threshold(dt: Optional[datetime] = None) -> float:
    """
    Return the Bid/Ask spread quality threshold as a fraction of mid-price.

    During the primary session a wider spread (5%) is tolerable.
    During overnight/pre-market a stricter threshold (1%) is applied.
    """
    if is_primary_session(dt):
        return PRIMARY_SPREAD_THRESHOLD
    return OVERNIGHT_SPREAD_THRESHOLD


def quote_passes_liquidity_check(
    bid: float,
    ask: float,
    bid_size: int   = 0,
    ask_size: int   = 0,
    dt: Optional[datetime] = None,
    min_size: int   = 5,
) -> Union[bool, str]:
    """
    Check whether a quote meets minimum liquidity requirements for the
    current session.

    Returns
    -------
    (passed: bool, reason: str)
        ``reason`` is empty string on success, otherwise describes the failure.
    """
    session = get_session_type(dt)

    if bid <= 0 or ask <= 0 or ask < bid:
        return False, f"無效報價 bid={bid} ask={ask}"

    mid = (bid + ask) / 2.0
    if mid <= 0:
        return False, "mid-price 為零"

    spread_pct = (ask - bid) / mid
    threshold  = get_spread_threshold(dt)

    # During pre-market/overnight: also enforce minimum bid/ask sizes
    if session in ("premarket", "overnight"):
        if bid_size < min_size or ask_size < min_size:
            return (
                False,
                f"流動性不足 ({session}): bid_size={bid_size} ask_size={ask_size} < {min_size}",
            )

    if spread_pct > threshold:
        return (
            False,
            f"買賣價差過大 ({session}): {spread_pct:.1%} > {threshold:.1%} 閾值",
        )

    return True, ""


def label_data_with_session(data: dict, dt: Optional[datetime] = None) -> dict:
    """
    Inject ``session_type`` and ``is_overnight`` keys into an existing data dict.
    This is a pure helper – it does not modify ``data`` in place but returns
    a new dict with the extra keys merged in.
    """
    session = get_session_type(dt)
    return {
        **data,
        "session_type": session,
        "is_overnight": session in ("overnight", "premarket"),
    }
