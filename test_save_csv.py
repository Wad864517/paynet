import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_manager import save_to_csv, get_date_folder

print("="*60)
print("🧪 测试 save_to_csv 函数")
print("="*60)

date_str = datetime.now().strftime("%Y%m%d")
print(f"\n📅 当前日期: {date_str}")
print(f"📁 数据文件夹: {get_date_folder()}")

dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10)][::-1]

test_df = pd.DataFrame({
    '日期': dates,
    '开盘': np.random.uniform(20, 25, 10).round(2),
    '收盘': np.random.uniform(20, 25, 10).round(2),
    '最高': np.random.uniform(20, 26, 10).round(2),
    '最低': np.random.uniform(19, 24, 10).round(2),
    '成交量': np.random.randint(100000, 500000, 10),
    '涨跌幅': np.random.uniform(-5, 5, 10).round(2),
    'MA5': np.random.uniform(21, 24, 10).round(2),
    'MACD': np.random.uniform(-0.5, 0.5, 10).round(3),
    'RSI': np.random.uniform(30, 70, 10).round(1)
})

print("\n📊 测试数据预览:")
print(test_df.to_string())

print("\n" + "="*60)
print("💾 开始保存测试数据...")
print("="*60)

save_to_csv(test_df, "test_kline_600196.csv")

save_to_csv(test_df[['日期', 'MA5', 'MACD', 'RSI']], "test_indicators_600196.csv")

flow_df = pd.DataFrame({
    '日期': dates,
    '主力净流入': np.random.randint(-200000000, 200000000, 10),
    '超大单净流入': np.random.randint(-100000000, 100000000, 10),
    '大单净流入': np.random.randint(-50000000, 50000000, 10),
    '小单净流入': np.random.randint(-50000000, 50000000, 10)
})

save_to_csv(flow_df, "test_money_flow_600196.csv")

print("\n✅ 所有测试数据保存完成!")
print("\n" + "="*60)
print("🔍 验证文件是否正确保存:")
print("="*60)

import os
folder_path = get_date_folder()
files = os.listdir(folder_path)
print(f"\n📂 {folder_path} 目录下的文件:")
for f in files:
    f_path = os.path.join(folder_path, f)
    size = os.path.getsize(f_path)
    print(f"  - {f} ({size} bytes)")

print("\n📝 读取保存的文件验证内容:")
loaded_df = pd.read_csv(os.path.join(folder_path, "test_kline_600196.csv"), encoding="utf-8-sig")
print(loaded_df[['日期', '开盘', '收盘', '成交量']].to_string())