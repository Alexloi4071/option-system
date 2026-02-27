from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class StrategyCriteria:
    min_market_cap: float  # In Billions
    min_volume: int
    min_relative_volume: float
    gap_min_pct: float
    gap_max_pct: Optional[float]
    iv_rank_max: Optional[float]
    preferred_strategies: List[str] # ['LONG_CALL', 'LONG_PUT', 'SHORT_PUT', etc.]
    
    # Finviz Screener URL Parameters (v=111 is overview)
    # titans: f=cap_mega,sh_avgvol_o10
    # momentum: f=cap_large,sec_technology
    finviz_filters: str 

@dataclass
class StrategyProfile:
    name: str
    description: str
    criteria: StrategyCriteria

# 1. 🔵 The Titans (Blue Chip)
# Focus: Mega Cap, Steady, Liquidity.
TITANS_PROFILE = StrategyProfile(
    name="The_Titans",
    description="Mega Cap / High Liquidity (e.g., NVDA, TSLA, AAPL)",
    criteria=StrategyCriteria(
        min_market_cap=200.0,
        min_volume=100_000,          # Pre-market volume
        min_relative_volume=1.0,     # Normal volume is fine
        gap_min_pct=0.5,
        gap_max_pct=2.0,
        iv_rank_max=50.0,            # Avoid expensive options for steady moves
        preferred_strategies=['LONG_CALL', 'LONG_PUT', 'SHORT_PUT'], # Added Short Put (Bullish Income)
        finviz_filters="f=cap_mega,sh_avgvol_o2,sh_opt_option" # Mega Cap, Avg Vol > 2M, Optionable
    )
)

# 2. 🔥 Momentum (Growth)
# Focus: Growth/Tech, Volatility, Trend Following.
MOMENTUM_PROFILE = StrategyProfile(
    name="Momentum_Growth",
    description="Growth / Crypto / Innovation (e.g., PLTR, COIN)",
    criteria=StrategyCriteria(
        min_market_cap=10.0,
        min_volume=50_000,
        min_relative_volume=1.5,     # Needs some volume pickup
        gap_min_pct=1.0,             # Lowered to 1.0% to capture more large cap moves
        gap_max_pct=10.0,            # Widened max gap
        iv_rank_max=None,            # Tolerate higher IV
        preferred_strategies=['LONG_CALL', 'LONG_PUT', 'SHORT_PUT', 'SHORT_CALL'], # Added Shorts
        finviz_filters="f=cap_midover,sh_opt_option,sec_technology|financial" # Mid+ Cap (>2B), Optionable, Tech/Fin
    )
)

# 3. 🧨 Catalysts (Earnings/News)
# Focus: Gap and Go, Explosive.
CATALYSTS_PROFILE = StrategyProfile(
    name="Catalysts_News",
    description="Stocks with breaking news or earnings gaps",
    criteria=StrategyCriteria(
        min_market_cap=2.0,          # Mid-cap+
        min_volume=200_000,          # Huge volume required for news plays
        min_relative_volume=5.0,     # Massive relative volume
        gap_min_pct=3.0,             # Lowered to 3% to catch more news moves
        gap_max_pct=None,            # No upper limit
        iv_rank_max=None,
        preferred_strategies=['LONG_CALL', 'LONG_PUT', 'SHORT_CALL', 'SHORT_PUT'], # Full Spectrum
        finviz_filters="s=ta_topgainers&f=sh_opt_option" # Top Gainers + Optionable (Crucial fix)
    )
)

ALL_PROFILES = {
    "titans": TITANS_PROFILE,
    "momentum": MOMENTUM_PROFILE,
    "catalysts": CATALYSTS_PROFILE
}

def get_profile_by_ticker(ticker: str, market_cap_b: float) -> StrategyProfile:
    """
    Auto-classify a ticker into a profile based on Market Cap.
    Note: Real classification needs Sector data too, this is a simplified version.
    """
    if market_cap_b >= 200:
        return TITANS_PROFILE
    elif market_cap_b >= 10:
        return MOMENTUM_PROFILE
    else:
        # Default to Catalysts logic (treating small caps as speculative)
        # or fall back to Momentum if it fits sector.
        return MOMENTUM_PROFILE
