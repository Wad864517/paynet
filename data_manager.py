import os
from datetime import datetime

def get_date_folder(base_dir="data"):
    """获取当天日期文件夹路径，不存在则创建"""
    date_str = datetime.now().strftime("%Y%m%d")
    folder_path = os.path.join(base_dir, date_str)
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"📁 创建日期文件夹: {folder_path}")
    
    return folder_path

def save_to_csv(df, filename, base_dir="data"):
    """将DataFrame保存到当天日期文件夹中"""
    folder_path = get_date_folder(base_dir)
    full_path = os.path.join(folder_path, filename)
    
    df.to_csv(full_path, index=False, encoding="utf-8-sig")
    print(f"💾 数据已保存到: {full_path}")
    
    return full_path

if __name__ == "__main__":
    folder = get_date_folder()
    print(f"✅ 当天数据文件夹: {folder}")
    
    import pandas as pd
    test_df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    save_to_csv(test_df, "test.csv")