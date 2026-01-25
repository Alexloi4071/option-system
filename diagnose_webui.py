#!/usr/bin/env python3
"""
WebUI Diagnostic Script - checks for common issues
"""

import os
import sys
import json
from pathlib import Path

def check_project_structure():
    """Check if all necessary files exist"""
    base_path = Path("D:/option_trading_system/option_trading_system/option-system-main")
    
    print("🔍 Checking Project Structure...")
    
    # Core files
    required_files = [
        "web_layer/app.py",
        "web_layer/templates/index.html", 
        "web_layer/static/js/app.js",
        "web_layer/static/css/custom.css",
        "main.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    # Check JavaScript modules
    js_modules = [
        "web_layer/static/js/modules/core.js",
        "web_layer/static/js/modules/strategies.js", 
        "web_layer/static/js/modules/greeks.js",
        "web_layer/static/js/modules/advanced.js",
        "web_layer/static/js/modules/signals.js"
    ]
    
    print("\n📁 JavaScript Modules:")
    for module in js_modules:
        full_path = base_path / module
        if full_path.exists():
            print(f"   ✅ {module}")
        else:
            print(f"   ❌ {module} - MISSING")
            missing_files.append(module)
    
    # Check chart files
    chart_files = [
        "web_layer/static/js/charts/price-range.js",
        "web_layer/static/js/charts/pnl-curve.js",
        "web_layer/static/js/charts/vol-smile.js",
        "web_layer/static/js/charts/gex-oi.js",
        "web_layer/static/js/charts/hv-trend.js",
        "web_layer/static/js/charts/iv-gauge.js"
    ]
    
    print("\n📊 Chart Files:")
    for chart in chart_files:
        full_path = base_path / chart
        if full_path.exists():
            print(f"   ✅ {chart}")
        else:
            print(f"   ❌ {chart} - MISSING")
            missing_files.append(chart)
    
    return missing_files

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking Dependencies...")
    
    required_packages = [
        "flask", "pandas", "numpy", "yfinance", 
        "requests", "ib_insync", "fredapi"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    return missing_packages

def check_file_contents():
    """Check for common issues in file contents"""
    base_path = Path("D:/option_trading_system/option_trading_system/option-system-main")
    
    print("\n📄 Checking File Contents...")
    
    issues = []
    
    # Check HTML for script references
    html_file = base_path / "web_layer/templates/index.html"
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for script tags
        if '/static/js/app.js' not in content:
            issues.append("app.js not referenced in HTML")
            
        if 'Chart.js' not in content:
            issues.append("Chart.js CDN missing")
            
        if 'Alpine.js' not in content:
            issues.append("Alpine.js CDN missing")
    
    # Check app.py for routes
    app_file = base_path / "web_layer/app.py"
    if app_file.exists():
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '@app.route(\'/\')' not in content:
            issues.append("Main route '/' missing in app.py")
            
        if "@app.route('/api/analyze'" not in content:
            issues.append("Analysis API route missing")
    
    return issues

def main():
    print("🔧 WebUI Diagnostic Tool")
    print("=" * 50)
    
    missing_files = check_project_structure()
    missing_packages = check_dependencies() 
    content_issues = check_file_contents()
    
    print(f"\n📋 Summary:")
    print(f"   Missing files: {len(missing_files)}")
    print(f"   Missing packages: {len(missing_packages)}")
    print(f"   Content issues: {len(content_issues)}")
    
    if missing_files:
        print(f"\n❌ Missing Files:")
        for file in missing_files:
            print(f"   - {file}")
    
    if missing_packages:
        print(f"\n📦 Install Missing Packages:")
        print(f"   pip install {' '.join(missing_packages)}")
    
    if content_issues:
        print(f"\n⚠️ Content Issues:")
        for issue in content_issues:
            print(f"   - {issue}")
    
    if not missing_files and not missing_packages and not content_issues:
        print(f"\n✅ No major issues detected!")
        print(f"\n🚀 To start the WebUI:")
        print(f"   cd D:/option_trading_system/option_trading_system/option-system-main")
        print(f"   python web_layer/app.py")
        print(f"   Then open http://127.0.0.1:5000 in your browser")

if __name__ == "__main__":
    main()