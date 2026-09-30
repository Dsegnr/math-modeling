# -*- coding: utf-8 -*-
"""
问题4：水质风险评价
==================
小时级幅度+日级时长 → 梯形隶属度模糊综合评价 → 熵权+AHP组合赋权
→ 一票否决(>1.5NTU或连续≥8h直接高风险) → 马尔可夫转移矩阵
"""

import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

BASE = r"D:\数模竞赛"
FIG_DIR = os.path.join(BASE, "figures")
OUT_DIR = os.path.join(BASE, "output")

# ===================== 1. 加载2026数据 =====================
df = pd.read_pickle(os.path.join(BASE, "data_cleaned", "df_2026_clean.pkl"))
df['NTU'] = pd.to_numeric(df['NTU'], errors='coerce')
df['DATE'] = pd.to_datetime(df['DATE'])

# 筛选用到的列
df_risk = df[['DATE','TIME','NTU','MONTH','DAY']].dropna(subset=['DATE','NTU'])
df_risk['hour'] = df_risk['TIME'].astype(int) // 100
df_risk = df_risk.sort_values(['DATE','hour'])

print(f"Risk data: {len(df_risk)} rows, Date range: {df_risk['DATE'].min()} to {df_risk['DATE'].max()}")

# ===================== 2. 小时级 → 日级聚合 =====================
STANDARD = 1.0  # 国标

daily_records = []
for date, group in df_risk.groupby('DATE'):
    ntu_vals = group['NTU'].values
    n_total = len(ntu_vals)

    # 超标幅度 (每个小时)
    exceed_magnitudes = np.maximum(0, (ntu_vals - STANDARD) / STANDARD)  # η

    # 持续时长: 最长连续超标段
    exceeded = (ntu_vals > STANDARD).astype(int)
    max_consecutive = 0
    current_run = 0
    for v in exceeded:
        if v == 1:
            current_run += 1
            max_consecutive = max(max_consecutive, current_run)
        else:
            current_run = 0
    exceed_hours = max_consecutive * 2  # 转换为小时 (每步2h)

    # 日平均超标幅度
    avg_exceed = np.mean(exceed_magnitudes) if n_total > 0 else 0
    max_exceed = np.max(exceed_magnitudes) if n_total > 0 else 0
    max_ntu = np.max(ntu_vals) if n_total > 0 else 0

    daily_records.append({
        'DATE': date,
        'month': date.month,
        'day': date.day,
        'avg_NTU': np.mean(ntu_vals),
        'max_NTU': max_ntu,
        'avg_exceed_magnitude': avg_exceed,
        'max_exceed_magnitude': max_exceed,
        'continuous_exceed_hours': exceed_hours,
        'exceed_count': int(np.sum(exceeded)),
    })

df_daily = pd.DataFrame(daily_records)
print(f"\nDaily records: {len(df_daily)} days")

# ===================== 3. 一票否决 =====================
VETO_NTU = 1.5  # 超标50%
VETO_HOURS = 8   # 连续超标8h

df_daily['veto'] = (
    (df_daily['max_NTU'] > VETO_NTU) |
    (df_daily['continuous_exceed_hours'] >= VETO_HOURS)
)
n_veto = df_daily['veto'].sum()
print(f"One-vote veto triggered: {n_veto} / {len(df_daily)} days ({n_veto/len(df_daily)*100:.1f}%)")

# ===================== 4. 梯形隶属度函数 =====================
def trapezoid_mf(x, a, b, c, d):
    """梯形隶属度: 0-a上升, a-b平台, b-c下降, c-d归零"""
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return (x - a) / (b - a)
    if c < x < d:
        return (d - x) / (d - c)
    return 0.0

# 超标幅度 隶属度参数（调整后——更敏感捕获短时超标）
MAG_PARAMS = {
    'safe':     (0, 0, 0.03, 0.08),     # η<3% 绝对安全(放宽)
    'low':      (0.03, 0.08, 0.20, 0.35), # 3%-20% 低风险
    'medium':   (0.20, 0.35, 0.50, 0.65), # 20%-50% 中风险
    'high':     (0.50, 0.65, 1.0, 2.0),    # >50% 高风险
}

# 持续时长 隶属度参数 (小时)（调整后）
DUR_PARAMS = {
    'safe':     (0, 0, 1, 2),       # <1h 安全
    'low':      (1, 2, 3, 5),       # 1-3h 低风险(放宽)
    'medium':   (3, 5, 7, 9),       # 3-7h 中风险
    'high':     (7, 9, 12, 24),     # >7h 高风险
}

# ===================== 5. 组合赋权 =====================
# Entropy weight
def entropy_weight(data):
    data = np.array(data)
    data_norm = (data - data.min(axis=0)) / (data.max(axis=0) - data.min(axis=0) + 1e-10)
    p = data_norm / data_norm.sum(axis=0)
    e = -np.sum(p * np.log(p + 1e-10), axis=0) / np.log(len(data))
    w = (1 - e) / np.sum(1 - e)
    return w

# AHP weights: 超标幅度比持续时长稍微重要 → 判断矩阵
ahp_weights = np.array([0.55, 0.45])  # [幅度权重, 时长权重]

# Data for entropy
risk_data = df_daily[['avg_exceed_magnitude','continuous_exceed_hours']].values
ent_w = entropy_weight(risk_data)
print(f"Entropy weights: magnitude={ent_w[0]:.4f}, duration={ent_w[1]:.4f}")

# Combined: λ=0.5
lam = 0.5
combined_w = lam * ahp_weights + (1 - lam) * ent_w
print(f"Combined weights: magnitude={combined_w[0]:.4f}, duration={combined_w[1]:.4f}")

# ===================== 6. 模糊综合评价 =====================
risk_levels = ['safe', 'low', 'medium', 'high']
results = []

for _, row in df_daily.iterrows():
    if row['veto']:
        results.append('高风险(一票否决)')
        continue

    mag = row['max_exceed_magnitude']  # 用最大超标幅度防短时峰值稀释
    dur = row['continuous_exceed_hours']

    # 隶属度
    mag_mf = {lvl: trapezoid_mf(mag, *MAG_PARAMS[lvl]) for lvl in risk_levels}
    dur_mf = {lvl: trapezoid_mf(dur, *DUR_PARAMS[lvl]) for lvl in risk_levels}

    # 加权 + min算子合成
    scores = {}
    for lvl in risk_levels:
        scores[lvl] = min(
            combined_w[0] * mag_mf[lvl] + (1-combined_w[0]) * 0,
            combined_w[1] * dur_mf[lvl] + (1-combined_w[1]) * 0
        )
        # 简化为加权隶属度的min
        w_mag = np.sqrt(mag_mf[lvl])  # 几何平均
        w_dur = np.sqrt(dur_mf[lvl])
        scores[lvl] = combined_w[0] * mag_mf[lvl] + combined_w[1] * dur_mf[lvl]

    best_level = max(scores, key=scores.get)
    results.append(best_level)

df_daily['risk_level'] = results

# ===================== 7. 统计输出 =====================
print("\n--- Risk Level Distribution (Jan-Mar 2026) ---")
level_counts = df_daily['risk_level'].value_counts()
for lvl in risk_levels:
    cnt = level_counts.get(lvl, 0)
    print(f"  {lvl}: {cnt} days ({cnt/len(df_daily)*100:.1f}%)")
veto_days = df_daily['veto'].sum()
print(f"  一票否决: {veto_days} days")

# March detail
df_march = df_daily[df_daily['month'] == 3].copy()
print(f"\nMarch 2026 risk levels:")
print(df_march[['day','avg_NTU','max_NTU','continuous_exceed_hours','risk_level']].to_string())

# Save to Excel
output_cols = ['DATE','avg_NTU','max_NTU','avg_exceed_magnitude','continuous_exceed_hours','risk_level']
df_daily[output_cols].to_excel(os.path.join(OUT_DIR, 'problem4_risk_assessment.xlsx'), index=False)
df_march[output_cols].to_excel(os.path.join(OUT_DIR, 'problem4_march_detail.xlsx'), index=False)

# ===================== 8. 马尔可夫转移矩阵 =====================
print("\n--- Markov Transition Matrix ---")
risk_map = {'safe': 0, 'low': 1, 'medium': 2, 'high': 3}
risks = [r for r in df_daily['risk_level'] if r in risk_map]
risks_simple = [r if r in risk_map else 'high' for r in df_daily['risk_level']]
risks_codes = [risk_map.get(r, 3) for r in risks_simple]

trans_matrix = np.zeros((4, 4))
for i in range(len(risks_codes) - 1):
    trans_matrix[risks_codes[i], risks_codes[i+1]] += 1
trans_matrix = trans_matrix / (trans_matrix.sum(axis=1, keepdims=True) + 1e-10)

print("  From\\To    Safe   Low    Med    High")
for i, lvl_from in enumerate(risk_levels):
    row_str = f"  {lvl_from:8s}"
    for j in range(4):
        row_str += f"  {trans_matrix[i,j]:.3f}"
    print(row_str)

# ===================== 9. 风险归因分析 =====================
print("\n--- Risk Attribution ---")
# Spearman: daily raw water NTU vs risk level
# Merge with raw water data
rw_col = 'R/W NTU'
if rw_col in df.columns:
    daily_rw = df.groupby('DATE')[rw_col].mean().reset_index()
    daily_rw['DATE'] = pd.to_datetime(daily_rw['DATE'])
    df_attrib = df_daily.merge(daily_rw, on='DATE', how='left')

    risk_num = df_attrib['risk_level'].map({'safe': 0, 'low': 1, 'medium': 2, 'high': 3})
    if '高风险(一票否决)' in df_attrib['risk_level'].values:
        risk_num = df_attrib['risk_level'].map({'safe': 0, 'low': 1, 'medium': 2, 'high': 3, '高风险(一票否决)': 3})
    from scipy import stats
    rho, p = stats.spearmanr(df_attrib[rw_col].dropna(), risk_num.dropna())
    print(f"  Spearman(R/W NTU, risk_level) = {rho:.4f} (p={p:.4f})")

# ===================== 10. Visualizations =====================
# === 图1: 风险等级饼图 ===
fig, ax = plt.subplots(figsize=(7, 7))
counts = [level_counts.get(lvl, 0) for lvl in risk_levels]
colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
ax.pie(counts, labels=[f'{lvl}\n({cnt}d)' for lvl, cnt in zip(risk_levels, counts)],
       colors=colors, autopct='%1.1f%%', startangle=90)
ax.set_title('Water Quality Risk Level Distribution\n(Jan-Mar 2026)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_risk_pie.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_risk_pie.png'), bbox_inches='tight')
plt.close()
print("  Risk pie chart saved")

# === 图2: 日风险等级时间序列 ===
fig, ax = plt.subplots(figsize=(14, 5))
dates = df_daily['DATE'].values
risk_numeric = [risk_map.get(r, 3) for r in df_daily['risk_level']]
risk_numeric = [risk_map.get(r.split('(')[0], 3) if '(' in str(r) else risk_map.get(r, 3)
                for r in df_daily['risk_level']]
colors_ts = [colors[r] for r in risk_numeric]
ax.bar(range(len(dates)), np.ones(len(dates)), color=colors_ts, width=1.0)
ax.axhline(y=0, color='black', linewidth=0.5)
# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=colors[i], label=risk_levels[i]) for i in range(4)]
ax.legend(handles=legend_elements, loc='upper right')
ax.set_yticks([])
ax.set_title('Daily Risk Level Timeline (Jan-Mar 2026)', fontsize=14, fontweight='bold')
ax.set_xlabel('Day Index')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_risk_timeline.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_risk_timeline.png'), bbox_inches='tight')
plt.close()
print("  Risk timeline saved")

# === 图3: 隶属度函数可视化 ===
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

x_mag = np.linspace(0, 1.5, 200)
for lvl, color in zip(risk_levels, colors):
    y = [trapezoid_mf(x, *MAG_PARAMS[lvl]) for x in x_mag]
    ax1.plot(x_mag, y, color=color, linewidth=2, label=lvl)
ax1.axvline(x=0, color='gray', linestyle='--', alpha=0.5, label='NTU=1 (standard)')
ax1.set_title('Exceedance Magnitude Membership', fontweight='bold')
ax1.set_xlabel('Exceedance Rate (eta)'); ax1.set_ylabel('Membership')
ax1.legend(); ax1.grid(True, alpha=0.3)

x_dur = np.linspace(0, 24, 200)
for lvl, color in zip(risk_levels, colors):
    y = [trapezoid_mf(x, *DUR_PARAMS[lvl]) for x in x_dur]
    ax2.plot(x_dur, y, color=color, linewidth=2, label=lvl)
ax2.set_title('Duration Membership', fontweight='bold')
ax2.set_xlabel('Continuous Exceedance (hours)'); ax2.set_ylabel('Membership')
ax2.legend(); ax2.grid(True, alpha=0.3)

plt.suptitle('Trapezoidal Membership Functions', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_membership.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_membership.png'), bbox_inches='tight')
plt.close()
print("  Membership functions saved")

# === 图4: 马尔可夫转移热力图 ===
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(trans_matrix, cmap='YlOrRd', vmin=0, vmax=1)
for i in range(4):
    for j in range(4):
        ax.text(j, i, f'{trans_matrix[i,j]:.3f}', ha='center', va='center',
                fontsize=12, fontweight='bold',
                color='white' if trans_matrix[i,j] > 0.5 else 'black')
ax.set_xticks(range(4)); ax.set_yticks(range(4))
ax.set_xticklabels(risk_levels); ax.set_yticklabels(risk_levels)
ax.set_xlabel('To (t+1)'); ax.set_ylabel('From (t)')
ax.set_title('Risk Level Markov Transition Matrix', fontsize=14, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_markov.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p4_markov.png'), bbox_inches='tight')
plt.close()
print("  Markov matrix saved")

print("\n=== Problem 4 Complete ===")
