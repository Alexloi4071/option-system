"""
Task 19.5 驗證腳本 - 運行 Preservation Tests
驗證 Layer 4 Report Preservation 要求
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
    """運行 Task 19 相關的 preservation tests"""
    print("=" * 80)
    print("Task 19.5: 驗證 Preservation Tests - Layer 4 Report Preservation")
    print("=" * 80)
    
    # 加載測試函數
    test_dir = os.path.dirname(__file__)
    test_preservation = load_test_function(
        os.path.join(test_dir, "test_preservation_properties.py"),
        "test_all_preservation_properties"
    )
    
    print(f"\n{'=' * 80}")
    print(f"運行測試: Preservation Properties")
    print(f"{'=' * 80}")
    
    try:
        # 運行所有 preservation tests
        test_preservation()
        print(f"\n✓ Preservation Tests - PASSED")
        print("\n✓ 所有測試通過！Task 19.5 完成。")
        return 0
    except AssertionError as e:
        print(f"\n✗ Preservation Tests - FAILED")
        print(f"  錯誤: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Preservation Tests - ERROR")
        print(f"  錯誤: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
