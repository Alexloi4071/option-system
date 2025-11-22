import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import Any

def convert_to_serializable(obj: Any) -> Any:
    """
    遞歸將對象轉換為 JSON 可序列化的格式。
    處理:
    - datetime, date -> ISO format string
    - numpy types -> python native types (int, float, bool)
    - pandas types -> dict/list
    - dict, list -> recursive conversion
    - nan, inf -> None
    """
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(v) for v in obj]
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
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
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