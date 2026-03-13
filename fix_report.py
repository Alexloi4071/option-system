import sys

def main():
    path = 'd:/option_trading_system/output_layer/report_generator.py'
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8')

    old_block1 = '''        if 'call' in results:\r
            call = results['call']\r
            report += f"│ 📈 Call 期權:\\n"\r
            report += f"│   理論價格: ${call.get('option_price', 0):.2f}\\n"\r
            report += f"│   d1: {call.get('d1', 0):.6f}\\n"\r
            report += f"│   d2: {call.get('d2', 0):.6f}\\n"\r
            report += "│\\n"'''
    new_block1 = '''        if 'call' in results:\r
            call = results['call']\r
            report += f"│ 📈 Call 期權:\\n"\r
            report += f"│   理論價格: ${call.get('option_price', 0):.2f}\\n"\r
            if 'd1' in call and float(call.get('d1', 0)) != 0.0:\r
                report += f"│   d1: {call.get('d1', 0):.6f}\\n"\r
            if 'd2' in call and float(call.get('d2', 0)) != 0.0:\r
                report += f"│   d2: {call.get('d2', 0):.6f}\\n"\r
            report += "│\\n"'''

    old_block2 = '''        if 'put' in results:\r
            put = results['put']\r
            report += f"│ 📉 Put 期權:\\n"\r
            report += f"│   理論價格: ${put.get('option_price', 0):.2f}\\n"\r
            report += f"│   d1: {put.get('d1', 0):.6f}\\n"\r
            report += f"│   d2: {put.get('d2', 0):.6f}\\n"'''
    new_block2 = '''        if 'put' in results:\r
            put = results['put']\r
            report += f"│ 📉 Put 期權:\\n"\r
            report += f"│   理論價格: ${put.get('option_price', 0):.2f}\\n"\r
            if 'd1' in put and float(put.get('d1', 0)) != 0.0:\r
                report += f"│   d1: {put.get('d1', 0):.6f}\\n"\r
            if 'd2' in put and float(put.get('d2', 0)) != 0.0:\r
                report += f"│   d2: {put.get('d2', 0):.6f}\\n"'''

    if old_block1 in content and old_block2 in content:
        content = content.replace(old_block1, new_block1).replace(old_block2, new_block2)
        with open(path, 'wb') as f:
            f.write(content.encode('utf-8'))
        print('SUCCESS')
    else:
        print('TARGET NOT FOUND')
        print("Block 1 found:", old_block1 in content)
        print("Block 2 found:", old_block2 in content)

if __name__ == "__main__":
    main()
