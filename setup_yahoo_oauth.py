#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Yahoo Finance 2.0 OAuth 设置向导
帮助用户完成 OAuth 2.0 授权流程
"""

import sys
import logging
import webbrowser
from data_layer.yahoo_finance_v2_client import YahooFinanceV2Client
from config.settings import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "=" * 70)
    print(" " * 15 + "Yahoo Finance 2.0 OAuth 设置向导")
    print("=" * 70)


def check_configuration():
    """检查配置是否完整"""
    print("\n[步骤 1/4] 检查配置...")
    
    issues = []
    
    if not settings.YAHOO_CLIENT_ID:
        issues.append("YAHOO_CLIENT_ID 未设置")
    else:
        print(f"  ✓ Client ID: {settings.YAHOO_CLIENT_ID[:20]}...")
    
    if not settings.YAHOO_CLIENT_SECRET:
        issues.append("YAHOO_CLIENT_SECRET 未设置")
    else:
        print(f"  ✓ Client Secret: {settings.YAHOO_CLIENT_SECRET[:10]}...")
    
    if not settings.YAHOO_REDIRECT_URI:
        issues.append("YAHOO_REDIRECT_URI 未设置")
    else:
        print(f"  ✓ Redirect URI: {settings.YAHOO_REDIRECT_URI}")
    
    if issues:
        print("\n❌ 配置不完整:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n请在 .env 文件中设置以下环境变量:")
        print("  YAHOO_CLIENT_ID=your_client_id")
        print("  YAHOO_CLIENT_SECRET=your_client_secret")
        print("  YAHOO_REDIRECT_URI=https://yourdomain.com/callback")
        return False
    
    print("\n✓ 配置完整")
    return True


def perform_oauth_flow():
    """执行 OAuth 授权流程"""
    print("\n[步骤 2/4] 初始化 OAuth 客户端...")
    
    try:
        client = YahooFinanceV2Client(
            client_id=settings.YAHOO_CLIENT_ID,
            client_secret=settings.YAHOO_CLIENT_SECRET,
            redirect_uri=settings.YAHOO_REDIRECT_URI
        )
        
        print("  ✓ OAuth 客户端已初始化")
        
        # 检查是否已经有有效的 token
        if client.is_authenticated():
            print("\n✓ 已经存在有效的授权 token")
            print("  Token 文件: yahoo_token.json")
            
            answer = input("\n是否要重新授权? (y/n): ")
            if answer.lower() != 'y':
                return client
        
        # 获取授权 URL
        print("\n[步骤 3/4] 获取授权 URL...")
        auth_url, state = client.get_authorization_url()
        
        print("\n" + "=" * 70)
        print("请按照以下步骤完成授权:")
        print("=" * 70)
        print("\n1. 将会自动打开浏览器（或手动访问下面的 URL）")
        print("\n授权 URL:")
        print(f"  {auth_url}")
        print("\n2. 在浏览器中登录您的 Yahoo 账号")
        print("\n3. 授权应用访问您的数据")
        print("\n4. 授权后，浏览器会跳转到回调 URL（可能显示错误页面，这是正常的）")
        print("\n5. 复制浏览器地址栏中的完整 URL")
        print("   （URL 应该类似: https://yourdomain.com/callback?code=xxxxx）")
        print("\n" + "=" * 70)
        
        # 尝试自动打开浏览器
        try:
            print("\n正在打开浏览器...")
            webbrowser.open(auth_url)
        except Exception as e:
            print(f"\n⚠ 无法自动打开浏览器: {e}")
            print("请手动复制上面的 URL 到浏览器中访问")
        
        # 等待用户输入回调 URL
        print("\n[步骤 4/4] 等待授权回调...")
        callback_url = input("\n请粘贴完整的回调 URL: ").strip()
        
        if not callback_url:
            print("\n❌ 未输入回调 URL")
            return None
        
        # 获取 token
        print("\n正在获取 access token...")
        try:
            token = client.fetch_token(callback_url)
            print("\n✓ 成功获取 access token")
            print(f"  Token 已保存到: yahoo_token.json")
            print(f"  Token 过期时间: {token.get('expires_in', 0)} 秒")
            
            return client
            
        except Exception as e:
            print(f"\n❌ 获取 token 失败: {e}")
            print("\n可能的原因:")
            print("  1. 回调 URL 格式不正确")
            print("  2. 授权码已过期（请重新授权）")
            print("  3. Client ID 或 Client Secret 不正确")
            return None
        
    except Exception as e:
        print(f"\n❌ OAuth 流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_api_access(client):
    """测试 API 访问"""
    print("\n" + "=" * 70)
    print("测试 API 访问")
    print("=" * 70)
    
    try:
        print("\n正在获取 AAPL 股票数据...")
        response = client.get_quote('AAPL')
        
        from data_layer.yahoo_finance_v2_client import YahooFinanceV2Helper
        stock_info = YahooFinanceV2Helper.extract_stock_info(response)
        
        if stock_info:
            print("\n✓ API 访问成功!")
            print("\n股票数据:")
            print(f"  代码: {stock_info['ticker']}")
            print(f"  公司: {stock_info['company_name']}")
            print(f"  股价: ${stock_info['current_price']:.2f}")
            print(f"  市盈率: {stock_info['pe_ratio']:.2f}")
            print(f"  EPS: ${stock_info['eps']:.2f}")
            return True
        else:
            print("\n⚠ 无法解析 API 响应")
            return False
            
    except Exception as e:
        print(f"\n❌ API 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print_banner()
    
    # 检查配置
    if not check_configuration():
        sys.exit(1)
    
    # 执行 OAuth 流程
    client = perform_oauth_flow()
    
    if not client:
        print("\n❌ OAuth 授权失败")
        sys.exit(1)
    
    # 测试 API 访问
    if test_api_access(client):
        print("\n" + "=" * 70)
        print("🎉 Yahoo Finance 2.0 API 设置成功!")
        print("=" * 70)
        print("\n您现在可以使用 Yahoo Finance 2.0 API 了")
        print("\n下一步:")
        print("  1. Token 已保存到 yahoo_token.json")
        print("  2. 运行主程序: python main.py --ticker AAPL")
        print("  3. Token 会自动刷新，无需重新授权")
        print("\n" + "=" * 70)
        sys.exit(0)
    else:
        print("\n⚠ OAuth 授权成功，但 API 测试失败")
        print("  请检查网络连接和 API 权限")
        sys.exit(1)


if __name__ == "__main__":
    main()

