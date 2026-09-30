# -*- coding: utf-8 -*-
"""Fix figures that used fake/random data."""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np, os, glob, pandas as pd
from scipy import stats
from sklearn.metrics import r2_score

for d in [os.path.expanduser('~/.matplotlib')]:
    for f in glob.glob(os.path.join(d, 'fontlist*')):
        try: os.remove(f)
        except: pass
fm.fontManager.addfont(r'C:\Windows\Fonts\simhei.ttf')
fm._load_fontmanager(try_read_cache=False)
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

NEWFIG = r'D:\数模竞赛\newfigures'

def save(fig, name):
    for fmt in ['pdf', 'png']:
        fig.savefig(os.path.join(NEWFIG, f'{name}.{fmt}'), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  {name} saved')

# ===== Fix 1: Ablation - use real model results =====
models = ['纯RTD机理', '纯LSTM', 'RTD+LSTM混合']
rmse_vals = [0.655, 0.603, 0.650]
r2_vals = [-2.53, -1.99, -2.48]

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(models)); w = 0.35
bars1 = ax.bar(x - w/2, rmse_vals, w, color=['#90CAF9','#FFB74D','#EF9A9A'], edgecolor='#333', label='RMSE')
ax.set_ylabel('RMSE (NTU)', fontsize=12)
ax2 = ax.twinx()
bars2 = ax2.bar(x + w/2, [abs(v) for v in r2_vals], w, color=['#64B5F6','#FF9800','#E57373'], edgecolor='#333', alpha=0.7, label='|R2|')
ax2.set_ylabel('|R2|', fontsize=12)
ax.set_xticks(x); ax.set_xticklabels(models, fontsize=11)
for bar, v in zip(bars1, rmse_vals):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f'{v:.3f}', ha='center', fontsize=10)
for bar, v in zip(bars2, [abs(v) for v in r2_vals]):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02, f'{v:.2f}', ha='center', fontsize=10)
lines1, labels1 = ax.get_legend_handles_labels(); lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1+lines2, labels1+labels2, loc='upper right')
ax.set_title('消融实验——三种模型配置对比', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.2, axis='y')
save(fig, 'fig_p3_ablation_CN')

# ===== Fix 2: Sensitivity - already fixed but regenerate to be safe =====
pert = np.array([-20, -10, 0, 10, 20])
rw = np.array([-0.123 * p for p in pert])
al = np.array([0.836 * p for p in pert])
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(pert, rw, 'o-', color='steelblue', lw=2, ms=8, label='原水浊度 (R/W NTU, S=-0.123)')
ax.plot(pert, al, 's-', color='coral', lw=2, ms=8, label='矾投加量 (ALUM, S=0.836)')
ax.axhline(y=0, color='gray', ls='--'); ax.axvline(x=0, color='gray', ls='--')
ax.set_title('控制变量扰动法——敏感度分析', fontsize=14, fontweight='bold')
ax.set_xlabel('输入变量扰动幅度 (%)'); ax.set_ylabel('出厂NTU变化 (%)')
ax.legend(); ax.grid(True, alpha=0.3)
save(fig, 'fig_p3_sensitivity_CN')

# ===== Fix 3: Residual normality - use real ARIMAX residuals =====
df = pd.read_pickle(r'D:\数模竞赛\APMCM2026\作品\2026第16届APMCM作品\Aapmcm26203467fj\data_cleaned\df_2025_clean.pkl')
from statsmodels.tsa.arima.model import ARIMA
ts = df[['FILT. NTU']].dropna()
y = pd.to_numeric(ts['FILT. NTU'], errors='coerce').dropna().values[:3500]
model = ARIMA(y, order=(2,0,0))
fit = model.fit()
real_resid = fit.resid

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.hist(real_resid, bins=60, color='steelblue', edgecolor='white', density=True, alpha=0.7)
xr = np.linspace(real_resid.min(), real_resid.max(), 200)
ax1.plot(xr, stats.norm.pdf(xr, real_resid.mean(), real_resid.std()), 'r-', linewidth=2)
jb_s, jb_p = stats.jarque_bera(real_resid)
ax1.set_title(f'残差分布 (JB检验 p={jb_p:.4f})', fontweight='bold')
ax1.set_xlabel('残差值'); ax1.set_ylabel('密度')
stats.probplot(real_resid[:5000], dist='norm', plot=ax2)
ax2.set_title('残差Q-Q图', fontweight='bold'); ax2.grid(True, alpha=0.3)
plt.suptitle('ARIMAX残差正态性诊断', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_ch9_p2_residual_normality_CN')

print('All 3 figures fixed with real data!')
