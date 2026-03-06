"""
Task 20.3 驗證腳本 - 運行 Bug Exploration Test (Task 11)
"""
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 直接導入測試函數
import importlib.util

def load_test_function(file_path, function_name):
    """動態加載測試函數"""
    spec = importlib.util.spec_from_file_location("test_module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)

def run_tests():
    """運行 Task 20 相關的 bug exploration test"""
    print("=" * 80)
    print("Task 20.3: 驗證 Bug Exploration Test (Task 11)")
    print("=" * 80)
    
    # 加載測試函數
    test_dir = os.path.dirname(__file__)
    test_module_status = load_test_function(
        os.path.join(test_dir, "test_bug_exploration_module_status.py"),
        "test_module_execution_status"
    )
    
    print(f"\n{'=' * 80}")
    print(f"運行測試: Task 11 - Module Execution Status")
    print(f"{'=' * 80}")
    
    try:
        # 這些測試返回 bug_confirmed，如果為 False 表示 bug 已修復（測試通過）
        bug_confirmed = test_module_status()
        if not bug_confirmed:
            print(f"\n✓ Task 11: Module Execution Status - PASSED (Bug已修復)")
            print("\n✓ 測試通過！Task 20.3 完成。")
            return 0
        else:
            print(f"\n✗ Task 11: Module Execution Status - FAILED (Bug仍存在)")
            return 1
    except Exception as e:
        print(f"\n✗ Task 11: Module Execution Status - ERROR")
        print(f"  錯誤: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
