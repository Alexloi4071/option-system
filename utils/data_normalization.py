"""
數據標準化工具 - 統一處理 NaN/Inf 值

本模塊提供統一的數值處理函數，確保整個系統對 NaN/Inf 值的處理一致。

使用示例:
    from utils.data_normalization import normalize_numeric_value, safe_format_value
    
    # 標準化數值
    value = normalize_numeric_value(np.nan, default=0.0)  # 返回 0.0
    
    # 安全格式化
    text = safe_format_value(150.256, '.2f', '$')  # 返回 "$150.26"
"""

import numpy as np
import math
from typing import Any, Union


def normalize_numeric_value(
    value: Any,
    default: Any = None
) -> Union[float, int, Any]:
    """
    統一處理數值，將 NaN/Inf 轉為默認值
    
    參數:
        value: 待處理的數值
        default: 當 value 為 NaN/Inf 時返回的默認值
    
    返回:
        標準化後的數值或默認值
    
    示例:
        >>> normalize_numeric_value(np.nan, default=0.0)
        0.0
        >>> normalize_numeric_value(np.inf, default='NA')
        'NA'
        >>> normalize_numeric_value(0.5123456789, default=None)
        0.5123456789
    """
    if value is None:
        return default
    
    # NumPy 浮點類型
    if isinstance(value, (np.floating, np.float64, np.float32)):
        if np.isnan(value) or np.isinf(value):
            return default
        return float(value)
    
    # Python float
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return default
        return value
    
    # NumPy 整數類型
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    
    # 其他類型直接返回
    return value


def safe_format_value(
    value: Any,
    fmt: str = '.2f',
    prefix: str = '',
    suffix: str = '',
    na_value: str = 'N/A'
) -> str:
    """
    安全格式化數值為字符串
    
    參數:
        value: 待格式化的值
        fmt: 格式化字符串 (如 '.2f', '.4f')
        prefix: 前綴 (如 '$')
        suffix: 後綴 (如 '%')
        na_value: NaN/None 時顯示的字符串
    
    返回:
        格式化後的字符串
    
    示例:
        >>> safe_format_value(150.256, '.2f', '$')
        '$150.26'
        >>> safe_format_value(np.nan, na_value='N/A')
        'N/A'
        >>> safe_format_value(0.25, '.2%', suffix='')
        '25.00%'
    """
    # 先標準化值
    normalized = normalize_numeric_value(value, default=None)
    
    if normalized is None:
        return na_value
    
    try:
        formatted = f"{normalized:{fmt}}"
        return f"{prefix}{formatted}{suffix}"
    except (ValueError, TypeError):
        return na_value


def is_valid_numeric(value: Any) -> bool:
    """
    檢查值是否為有效的數值（非 None、非 NaN、非 Inf）
    
    參數:
        value: 待檢查的值
    
    返回:
        bool: 是否為有效數值
    
    示例:
        >>> is_valid_numeric(150.0)
        True
        >>> is_valid_numeric(np.nan)
        False
        >>> is_valid_numeric(None)
        False
    """
    if value is None:
        return False
    
    if isinstance(value, (np.floating, np.float64, np.float32)):
        return not (np.isnan(value) or np.isinf(value))
    
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    
    if isinstance(value, (int, np.integer)):
        return True
    
    return False
