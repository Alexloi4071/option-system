# output_layer/strategy_scenario_generator.py
"""
策略場景生成器

為不同期權策略生成適當的到期股價場景。

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

from dataclasses import dataclass
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyScenario:
    """策略場景數據類"""
    price_change_pct: float      # 價格變化百分比 (如 -0.10 表示下跌 10%)
    stock_price_at_expiry: float # 到期股價
    scenario_label: str          # 場景標籤（如「下跌10%」）


class StrategyScenarioGenerator:
    """
    策略場景生成器
    
    為不同期權策略（Long Call, Long Put, Short Call, Short Put）
    生成適當的到期股價場景。
    
    Requirements:
    - 1.1: 為每個策略方向使用不同的到期股價場景
    - 1.2: Long Call 包含股價下跌 10%、維持不變、上漲 10%、上漲 20%
    - 1.3: Long Put 包含股價下跌 20%、下跌 10%、維持不變、上漲 10%
    - 1.4: Short Call 包含股價維持不變、上漲 5%、上漲 10%、上漲 20%
    - 1.5: Short Put 包含股價下跌 20%、下跌 10%、下跌 5%、維持不變
    """
    
    # 各策略的場景配置（價格變化百分比）
    LONG_CALL_SCENARIOS = [-0.10, 0.00, 0.10, 0.20]   # 下跌10%, 不變, 上漲10%, 上漲20%
    LONG_PUT_SCENARIOS = [-0.20, -0.10, 0.00, 0.10]   # 下跌20%, 下跌10%, 不變, 上漲10%
    SHORT_CALL_SCENARIOS = [0.00, 0.05, 0.10, 0.20]   # 不變, 上漲5%, 上漲10%, 上漲20%
    SHORT_PUT_SCENARIOS = [-0.20, -0.10, -0.05, 0.00] # 下跌20%, 下跌10%, 下跌5%, 不變
    
    # 策略類型映射
    STRATEGY_SCENARIOS = {
        'long_call': LONG_CALL_SCENARIOS,
        'long_put': LONG_PUT_SCENARIOS,
        'short_call': SHORT_CALL_SCENARIOS,
        'short_put': SHORT_PUT_SCENARIOS,
        # 模塊名稱映射
        'module7_long_call': LONG_CALL_SCENARIOS,
        'module8_long_put': LONG_PUT_SCENARIOS,
        'module9_short_call': SHORT_CALL_SCENARIOS,
        'module10_short_put': SHORT_PUT_SCENARIOS,
    }
    
    @classmethod
    def _format_scenario_label(cls, pct: float) -> str:
        """
        格式化場景標籤
        
        Args:
            pct: 價格變化百分比（如 -0.10 表示下跌 10%）
            
        Returns:
            場景標籤字符串（如「下跌10%」、「維持不變」、「上漲20%」）
        """
        if pct == 0.0:
            return "維持不變"
        elif pct < 0:
            return f"下跌{abs(pct) * 100:.0f}%"
        else:
            return f"上漲{pct * 100:.0f}%"
    
    @classmethod
    def get_scenarios(cls, strategy_type: str, stock_price: float) -> List[StrategyScenario]:
        """
        獲取指定策略的場景列表
        
        Args:
            strategy_type: 策略類型，支持以下值：
                - 'long_call', 'long_put', 'short_call', 'short_put'
                - 'module7_long_call', 'module8_long_put', 'module9_short_call', 'module10_short_put'
            stock_price: 當前股價
            
        Returns:
            StrategyScenario 列表，包含該策略的所有場景
            
        Raises:
            ValueError: 如果策略類型無效或股價無效
        """
        # 驗證輸入
        if stock_price is None or stock_price <= 0:
            raise ValueError(f"股價必須為正數，收到: {stock_price}")
        
        # 標準化策略類型
        strategy_key = strategy_type.lower().strip()
        
        if strategy_key not in cls.STRATEGY_SCENARIOS:
            raise ValueError(
                f"無效的策略類型: {strategy_type}。"
                f"支持的類型: {list(cls.STRATEGY_SCENARIOS.keys())}"
            )
        
        # 獲取該策略的場景配置
        scenario_pcts = cls.STRATEGY_SCENARIOS[strategy_key]
        
        # 生成場景列表
        scenarios = []
        for pct in scenario_pcts:
            expiry_price = stock_price * (1 + pct)
            scenario = StrategyScenario(
                price_change_pct=pct,
                stock_price_at_expiry=round(expiry_price, 2),
                scenario_label=cls._format_scenario_label(pct)
            )
            scenarios.append(scenario)
        
        logger.debug(f"為 {strategy_type} 生成了 {len(scenarios)} 個場景")
        return scenarios
    
    @classmethod
    def get_scenario_prices(cls, strategy_type: str, stock_price: float) -> List[float]:
        """
        獲取指定策略的到期股價列表（簡化版）
        
        Args:
            strategy_type: 策略類型
            stock_price: 當前股價
            
        Returns:
            到期股價列表
        """
        scenarios = cls.get_scenarios(strategy_type, stock_price)
        return [s.stock_price_at_expiry for s in scenarios]
    
    @classmethod
    def get_scenario_labels(cls, strategy_type: str) -> List[str]:
        """
        獲取指定策略的場景標籤列表
        
        Args:
            strategy_type: 策略類型
            
        Returns:
            場景標籤列表
        """
        strategy_key = strategy_type.lower().strip()
        
        if strategy_key not in cls.STRATEGY_SCENARIOS:
            raise ValueError(f"無效的策略類型: {strategy_type}")
        
        scenario_pcts = cls.STRATEGY_SCENARIOS[strategy_key]
        return [cls._format_scenario_label(pct) for pct in scenario_pcts]
    
    @classmethod
    def get_scenario_percentages(cls, strategy_type: str) -> List[float]:
        """
        獲取指定策略的價格變化百分比列表
        
        Args:
            strategy_type: 策略類型
            
        Returns:
            價格變化百分比列表
        """
        strategy_key = strategy_type.lower().strip()
        
        if strategy_key not in cls.STRATEGY_SCENARIOS:
            raise ValueError(f"無效的策略類型: {strategy_type}")
        
        return list(cls.STRATEGY_SCENARIOS[strategy_key])
