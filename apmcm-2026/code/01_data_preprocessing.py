# -*- coding: utf-8 -*-
"""
A题 数据预处理模块
====================
- 2025年12个月训练数据（21列/16列两种格式）
- 2026年3个月预测数据（多sheet .xls格式）
- 列名标准化、缺失值处理、异常值区分、时间特征构造
"""

import pandas as pd
import numpy as np
import glob, os, warnings
warnings.filterwarnings('ignore')

# ===================== 路径配置 =====================
BASE = r"D:\数模竞赛"
DATA_2025 = os.path.join(BASE, r"赛题文本\A题附件\附件1  2025数据集")
DATA_2026 = os.path.join(BASE, r"赛题文本\A题附件\附件2  2026数据集")
OUT_DIR = os.path.join(BASE, "data_cleaned")

# ===================== 1. 2025数据读取与标准化 =====================
def load_2025_data():
    """读取2025年12个月数据，统一列名为21列标准格式"""
    std_cols_21 = ['DATE','TIME','RIVER LEVEL','R/W PUMP DUTY','R/W FLOW',
                   'R/W NTU','R/W CLR','R/W PH','FILT. NTU','C/W WELL LEVEL',
                   'PH','NTU','CLR','CL2','F/RIDE','ALUM','T/W PUMP DUTY',
                   'T/W FLOW','18ML LEVEL','18ML FLOW','REMARKS']

    std_cols_16 = ['Data','Time','River Level','Unnamed: 3','R/W FLOW',
                   'R/W NTU','R/W CLR','Unnamed: 7','FILT. NTU','C/W WELL LEVEL',
                   'Unnamed: 10','NTU','CLR','Unnamed: 13','T/W FLOW','Unnamed: 15']

    col_map_16to21 = {'Data':'DATE','Time':'TIME','River Level':'RIVER LEVEL'}

    all_months = []
    files = sorted(glob.glob(os.path.join(DATA_2025, "*.xlsx")))

    for f in files:
        df = pd.read_excel(f)
        ncols = len(df.columns)
        month_name = os.path.basename(f).replace('.xlsx','')

        if ncols == 21:
            df.columns = std_cols_21
            # 21列格式：保留所有列
        elif ncols == 16:
            df.columns = std_cols_16
            df.rename(columns=col_map_16to21, inplace=True)
            # 16列格式缺失的列填NaN
            for c in std_cols_21:
                if c not in df.columns:
                    df[c] = np.nan

        # DATE标准化
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        df['source_month'] = month_name

        all_months.append(df)
        print(f"  {month_name}: {len(df)} rows, {ncols} cols -> 21 cols")

    df_all = pd.concat(all_months, ignore_index=True)
    print(f"\n2025 total: {len(df_all)} rows, {len(df_all.columns)} cols")
    return df_all

# ===================== 2. 2026数据读取（多sheet） =====================
def load_2026_data():
    """读取2026年3个.xls文件，每月每天一个sheet，保留DATE标识"""
    all_days = []

    for fname in sorted(glob.glob(os.path.join(DATA_2026, "*.xls"))):
        fname_base = os.path.basename(fname)
        # 解析月份: "2026年1月.xls" -> 1
        month = int(fname_base.replace('2026年','').replace('月.xls','').replace('.xls',''))

        xl = pd.ExcelFile(fname, engine='calamine')
        print(f"\n{fname_base}: {len(xl.sheet_names)} sheets")

        for sheet in xl.sheet_names:
            df = pd.read_excel(fname, sheet_name=sheet, engine='calamine')
            # sheet名: "01.01", "20.02" -> day.month
            sheet_clean = sheet.strip()
            try:
                day = int(sheet_clean.split('.')[0])
            except:
                continue

            # 构造DATE
            df['DAY'] = day
            df['MONTH'] = month
            df['DATE'] = pd.to_datetime(f'2026-{month:02d}-{day:02d}', errors='coerce')

            # TIME列可能有空格，标准化
            time_col = [c for c in df.columns if 'TIME' in c.upper() or 'Time' in c][0]
            df.rename(columns={time_col: 'TIME'}, inplace=True)

            all_days.append(df)

    df_all = pd.concat(all_days, ignore_index=True)

    # 标准化列名: 去掉列名尾部空格
    df_all.columns = [c.strip() if isinstance(c, str) else c for c in df_all.columns]

    print(f"\n2026 total: {len(df_all)} rows, {len(df_all.columns)} cols")
    print(f"  Months: {sorted(df_all['MONTH'].unique())}")
    print(f"  Date range: {df_all['DATE'].min()} to {df_all['DATE'].max()}")
    return df_all

# ===================== 3. 数据清洗 =====================
def clean_data(df):
    """统一的数据清洗"""
    df = df.copy()

    # 3.1 数值列转换
    numeric_cols = ['R/W PUMP DUTY','R/W FLOW','R/W NTU','R/W CLR','R/W PH',
                    'FILT. NTU','C/W WELL LEVEL','PH','NTU','CLR','CL2',
                    'F/RIDE','ALUM','T/W FLOW','18ML LEVEL','18ML FLOW',
                    'RIVER LEVEL']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # 3.2 异常值标记（区分设备故障 vs 真实水质异常）
    # NTU类指标：负数或极端跳变标记为设备故障
    for col in ['R/W NTU', 'FILT. NTU', 'NTU']:
        if col in df.columns:
            # 负值 → 传感器故障
            fault_mask = df[col] < 0
            df.loc[fault_mask, col] = np.nan
            # 记录故障数量
            n_fault = fault_mask.sum()
            if n_fault > 0:
                print(f"  {col}: {n_fault} device fault values cleaned (negatives)")

    # 3.3 缺失值处理
    # 时间序列: 前向填充为默认，后向填充兜底
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    # 3.4 构造时间特征
    if 'DATE' in df.columns and 'TIME' in df.columns:
        df['datetime'] = pd.to_datetime(
            df['DATE'].astype(str) + ' ' +
            df['TIME'].astype(str).str.zfill(4).str[:2] + ':' +
            df['TIME'].astype(str).str.zfill(4).str[2:4],
            errors='coerce'
        )
        df['hour'] = df['datetime'].dt.hour
        df['month'] = df['datetime'].dt.month
        df['day'] = df['datetime'].dt.day
        # 循环编码小时（捕捉日周期）
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    return df

# ===================== 4. 主流程 =====================
if __name__ == "__main__":
    print("=" * 60)
    print("Loading 2025 training data...")
    print("=" * 60)
    df_2025 = load_2025_data()
    df_2025 = clean_data(df_2025)

    print("\n" + "=" * 60)
    print("Loading 2026 prediction data...")
    print("=" * 60)
    df_2026 = load_2026_data()
    df_2026 = clean_data(df_2026)

    # 保存
    df_2025.to_pickle(os.path.join(OUT_DIR, "df_2025_clean.pkl"))
    df_2026.to_pickle(os.path.join(OUT_DIR, "df_2026_clean.pkl"))

    print(f"\n{'='*60}")
    print(f"Saved to {OUT_DIR}")
    print(f"  2025: {df_2025.shape}")
    print(f"  2026: {df_2026.shape}")
    print(f"{'='*60}")
