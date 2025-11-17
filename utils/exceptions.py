"""
自定義異常類

本模塊定義了系統中使用的自定義異常類，用於更精確的錯誤處理和報告。

異常層次結構:
- InvalidInputError: 輸入參數驗證失敗
- ConvergenceError: 迭代計算未收斂
- DataSourceError: 所有數據源失敗

使用示例:
    from utils.exceptions import InvalidInputError
    
    if stock_price <= 0:
        raise InvalidInputError(
            "股價必須大於0",
            parameter="stock_price",
            value=stock_price
        )
"""


class InvalidInputError(ValueError):
    """
    輸入參數無效異常
    
    當輸入參數不符合要求時拋出此異常。
    
    屬性:
        message (str): 錯誤描述信息
        parameter (str): 無效的參數名稱
        value: 無效的參數值
        expected (str): 期望的參數要求描述
    
    示例:
        >>> raise InvalidInputError(
        ...     "股價必須大於0",
        ...     parameter="stock_price",
        ...     value=-100,
        ...     expected="正數"
        ... )
    """
    
    def __init__(
        self,
        message: str,
        parameter: str = None,
        value=None,
        expected: str = None
    ):
        """
        初始化 InvalidInputError
        
        參數:
            message: 錯誤描述信息
            parameter: 無效的參數名稱（可選）
            value: 無效的參數值（可選）
            expected: 期望的參數要求描述（可選）
        """
        self.message = message
        self.parameter = parameter
        self.value = value
        self.expected = expected
        
        # 構建詳細的錯誤信息
        error_parts = [message]
        
        if parameter:
            error_parts.append(f"參數: {parameter}")
        
        if value is not None:
            error_parts.append(f"實際值: {value}")
        
        if expected:
            error_parts.append(f"期望: {expected}")
        
        full_message = " | ".join(error_parts)
        super().__init__(full_message)
    
    def __str__(self):
        """返回格式化的錯誤信息"""
        return super().__str__()


class ConvergenceError(RuntimeError):
    """
    迭代計算未收斂異常
    
    當迭代算法（如 Newton-Raphson）在最大迭代次數內未能收斂時拋出此異常。
    
    屬性:
        message (str): 錯誤描述信息
        iterations (int): 已執行的迭代次數
        tolerance (float): 收斂容差
        current_error (float): 當前誤差值
        algorithm (str): 算法名稱
    
    示例:
        >>> raise ConvergenceError(
        ...     "隱含波動率計算未收斂",
        ...     iterations=100,
        ...     tolerance=0.0001,
        ...     current_error=0.005,
        ...     algorithm="Newton-Raphson"
        ... )
    """
    
    def __init__(
        self,
        message: str,
        iterations: int = None,
        tolerance: float = None,
        current_error: float = None,
        algorithm: str = None
    ):
        """
        初始化 ConvergenceError
        
        參數:
            message: 錯誤描述信息
            iterations: 已執行的迭代次數（可選）
            tolerance: 收斂容差（可選）
            current_error: 當前誤差值（可選）
            algorithm: 算法名稱（可選）
        """
        self.message = message
        self.iterations = iterations
        self.tolerance = tolerance
        self.current_error = current_error
        self.algorithm = algorithm
        
        # 構建詳細的錯誤信息
        error_parts = [message]
        
        if algorithm:
            error_parts.append(f"算法: {algorithm}")
        
        if iterations is not None:
            error_parts.append(f"迭代次數: {iterations}")
        
        if tolerance is not None:
            error_parts.append(f"收斂容差: {tolerance}")
        
        if current_error is not None:
            error_parts.append(f"當前誤差: {current_error}")
        
        full_message = " | ".join(error_parts)
        super().__init__(full_message)
    
    def __str__(self):
        """返回格式化的錯誤信息"""
        return super().__str__()


class DataSourceError(RuntimeError):
    """
    數據源失敗異常
    
    當所有可用的數據源都失敗時拋出此異常。
    
    屬性:
        message (str): 錯誤描述信息
        data_type (str): 請求的數據類型
        attempted_sources (list): 嘗試過的數據源列表
        last_error (str): 最後一個數據源的錯誤信息
    
    示例:
        >>> raise DataSourceError(
        ...     "無法獲取期權 Greeks 數據",
        ...     data_type="option_greeks",
        ...     attempted_sources=["IBKR", "Yahoo V2", "Self-Calculated"],
        ...     last_error="計算失敗: 缺少波動率數據"
        ... )
    """
    
    def __init__(
        self,
        message: str,
        data_type: str = None,
        attempted_sources: list = None,
        last_error: str = None
    ):
        """
        初始化 DataSourceError
        
        參數:
            message: 錯誤描述信息
            data_type: 請求的數據類型（可選）
            attempted_sources: 嘗試過的數據源列表（可選）
            last_error: 最後一個數據源的錯誤信息（可選）
        """
        self.message = message
        self.data_type = data_type
        self.attempted_sources = attempted_sources or []
        self.last_error = last_error
        
        # 構建詳細的錯誤信息
        error_parts = [message]
        
        if data_type:
            error_parts.append(f"數據類型: {data_type}")
        
        if attempted_sources:
            sources_str = ", ".join(attempted_sources)
            error_parts.append(f"嘗試的數據源: {sources_str}")
        
        if last_error:
            error_parts.append(f"最後錯誤: {last_error}")
        
        full_message = " | ".join(error_parts)
        super().__init__(full_message)
    
    def __str__(self):
        """返回格式化的錯誤信息"""
        return super().__str__()
