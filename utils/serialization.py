import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Any


def _convert_key(key: Any) -> str:
    """
    將字典鍵轉換為字符串格式（JSON 只支持字符串鍵）
    """
    if isinstance(key, pd.Timestamp):
        return key.isoformat()
    elif isinstance(key, (datetime, date)):
        return key.isoformat()
    elif isinstance(key, (np.integer, np.int64, np.int32)):
        return str(int(key))
    elif isinstance(key, (np.floating, np.float64, np.float32)):
        return str(float(key))
    elif key is None:
        return "null"
    else:
        return str(key)


def convert_to_serializable(obj: Any) -> Any:
    """
    遞歸將對象轉換為 JSON 可序列化的格式。
    處理:
    - datetime, date, pd.Timestamp -> ISO format string
    - numpy types -> python native types (int, float, bool)
    - pandas types -> dict/list
    - dict, list -> recursive conversion
    - nan, inf -> None
    - dict keys -> string (JSON requirement)
    """
    if isinstance(obj, dict):
        # 轉換鍵和值（JSON 要求鍵必須是字符串）
        return {_convert_key(k): convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return convert_to_serializable(obj.tolist())
    elif isinstance(obj, pd.DataFrame):
        return convert_to_serializable(obj.to_dict(orient='records'))
    elif isinstance(obj, pd.Series):
        return convert_to_serializable(obj.to_dict())
    elif obj is None:
        return None
    else:
        return obj

class CustomJSONEncoder(json.JSONEncoder):
    """
    自定義 JSON Encoder，用於 json.dump
    處理 pandas Timestamp、numpy 類型、NaN/Inf 等特殊值
    """
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        return super().default(obj)
    
    def encode(self, obj):
        """
        重寫 encode 方法，先預處理數據（轉換字典鍵）
        """
        return super().encode(convert_to_serializable(obj))