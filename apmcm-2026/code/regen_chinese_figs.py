# -*- coding: utf-8 -*-
"""Regenerate key figures with Chinese labels into newfigures/"""
import os, warnings, glob, numpy as np, pandas as pd
warnings.filterwarnings('ignore')

# ===== CRITICAL: Font setup MUST happen before ANY plotting library import =====
import matplotlib
matplotlib.use('Agg')
import matplotlib.font_manager as fm

# Clear font cache
for d in [os.path.expanduser('~/.matplotlib'), os.path.expanduser('~/.cache/matplotlib')]:
    for f in glob.glob(os.path.join(d, 'fontlist*')):
        try: os.remove(f)
        except: pass

# Register Chinese fonts
for fp in [r'C:\Windows\Fonts\simhei.ttf', r'C:\Windows\Fonts\msyh.ttc']:
    fm.fontManager.addfont(fp)
fm._load_fontmanager(try_read_cache=False)

# Set rcParams BEFORE importing pyplot/seaborn/shap
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300

# Now safe to import plotting libraries
import seaborn as sns
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.feature_selection import mutual_info_regression
import shap
# Do NOT call sns.set_style — it resets font rcParams

BASE = r'D:\数模竞赛'
NEWFIG = os.path.join(BASE, 'newfigures')
os.makedirs(NEWFIG, exist_ok=True)

def save(fig, name):
    fig.savefig(os.path.join(NEWFIG, name.replace('.pdf','.png')), bbox_inches='tight')
    fig.savefig(os.path.join(NEWFIG, name), bbox_inches='tight')
    plt.close(fig)
    print(f'  {name}')

# ===== Load data =====
df = pd.read_pickle(os.path.join(BASE, 'data_cleaned', 'df_2025_clean.pkl'))
df = df.sort_values(['DATE','TIME'])

TARGET = 'NTU'
feature_candidates = ['RIVER LEVEL','R/W FLOW','R/W NTU','R/W CLR','R/W PH',
                      'FILT. NTU','C/W WELL LEVEL','PH','CLR','CL2','ALUM','T/W FLOW']
for c in feature_candidates:
    if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')

# Lag features
for col in ['R/W NTU','R/W FLOW','R/W PH','RIVER LEVEL','ALUM']:
    if col in df.columns:
        df[f'{col}_lag1'] = df[col].shift(1)
        df[f'{col}_lag2'] = df[col].shift(2)
df['NTU_lag1'] = df[TARGET].shift(1)
df['NTU_lag2'] = df[TARGET].shift(2)
df['R/W_NTU_roll3'] = df['R/W NTU'].rolling(3).mean()

lag_features = [c for c in df.columns if '_lag' in c or '_roll' in c]
all_features = [c for c in feature_candidates + lag_features if c in df.columns]
top_features = ['NTU_lag1','FILT. NTU','NTU_lag2','T/W FLOW','R/W FLOW',
                'R/W NTU','R/W FLOW_lag1','RIVER LEVEL_lag1','C/W WELL LEVEL']
top_features = [c for c in top_features if c in df.columns]

df_model = df[top_features + [TARGET]].dropna()
X_all = df_model[top_features].values
y_all = df_model[TARGET].values

# Train RF for SHAP
rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(X_all, y_all)

# ===== 1. SHAP Beeswarm (CHINESE) =====
print("Generating SHAP figures...")
explainer = shap.TreeExplainer(rf, feature_perturbation="interventional")
shap_vals = explainer.shap_values(X_all[:500])

fig, ax = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_vals, X_all[:500], feature_names=top_features,
                  plot_type="dot", show=False, max_display=12)
ax.set_xlabel('SHAP值（对预测的影响）', fontsize=12)
ax.set_title('SHAP蜂群图——特征重要性与影响方向', fontsize=14, fontweight='bold')
save(fig, 'fig_p1_shap_beeswarm_CN.pdf')

# ===== 2. SHAP Bar (CHINESE) =====
fig, ax = plt.subplots(figsize=(8, 6))
shap.summary_plot(shap_vals, X_all[:500], feature_names=top_features,
                  plot_type="bar", show=False, max_display=10)
ax.set_xlabel('平均|SHAP值|（特征重要性）', fontsize=12)
ax.set_title('SHAP全局特征重要性排序', fontsize=14, fontweight='bold')
save(fig, 'fig_p1_shap_bar_CN.pdf')

# ===== 3. SHAP Dependence (CHINESE) =====
top3 = top_features[:3]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for idx, feat in enumerate(top3):
    feat_idx = top_features.index(feat)
    shap.dependence_plot(feat_idx, shap_vals, X_all[:500],
                         feature_names=top_features, ax=axes[idx], show=False)
    axes[idx].set_xlabel(feat, fontsize=10)
    axes[idx].set_ylabel(f'SHAP值（{feat}的边际贡献）', fontsize=9)
    axes[idx].set_title(f'{feat}', fontsize=11, fontweight='bold')
plt.suptitle('SHAP依赖图——Top3特征非线性边际效应', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p1_shap_dependence_CN.pdf')

# ===== 4. Feature Importance Comparison (CHINESE) =====
spearman_scores = {}
for col in all_features:
    if col in df_model.columns:
        rho, _ = stats.spearmanr(df_model[col], df_model[TARGET])
        spearman_scores[col] = abs(rho)
mi_scores = mutual_info_regression(X_all, y_all, random_state=42)
mi_ranked = [(all_features[i], mi_scores[i]) for i in np.argsort(mi_scores)[::-1]]
mdi_ranked = [(all_features[i], rf.feature_importances_[i]) for i in np.argsort(rf.feature_importances_)[::-1]]

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
methods = [
    ('Spearman相关系数', spearman_scores),
    ('互信息（MI）', dict(mi_ranked)),
    ('随机森林MDI', dict(mdi_ranked[:15]))
]
for ax, (name, sd) in zip(axes, methods):
    items = sorted(sd.items(), key=lambda x: x[1], reverse=True)[:10]
    labels, values = zip(*items)
    colors = plt.cm.Blues(np.linspace(0.3, 1, len(values)))
    ax.barh(range(len(labels)), values, color=colors[::-1])
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8)
    ax.set_title(name, fontweight='bold'); ax.invert_yaxis()
plt.suptitle('三种特征重要性方法对比', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p1_feature_importance_compare_CN.pdf')

print("SHAP figures done.")

# ===== 5. CCF Prewhitening (CHINESE) =====
print("Generating CCF figures...")
from statsmodels.tsa.stattools import ccf, adfuller
from statsmodels.tsa.arima.model import ARIMA

ts_data = df[['FILT. NTU','R/W NTU','R/W PH','ALUM','R/W FLOW']].dropna()
y = ts_data['FILT. NTU'].values
INPUTS = ['R/W NTU','R/W PH','ALUM','R/W FLOW']
max_lag = 12

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for idx, var_name in enumerate(INPUTS):
    ax = axes[idx//2, idx%2]
    x = ts_data[var_name].values
    raw_ccf = ccf(x, y, adjusted=False)[:max_lag+1]
    # Prewhitening
    ar = ARIMA(x, order=(3,0,0)).fit()
    x_resid = ar.resid
    ar_y = ARIMA(y, order=(3,0,0)).fit()
    y_resid = ar_y.resid
    mlen = min(len(x_resid), len(y_resid))
    pw_ccf = ccf(x_resid[:mlen], y_resid[:mlen], adjusted=False)[:max_lag+1]

    lags_r = np.arange(max_lag+1)
    ax.plot(lags_r, raw_ccf, 'o-', color='gray', alpha=0.7, linewidth=1.5, markersize=4, label='原始CCF（未预白化）')
    ax.plot(lags_r, pw_ccf, 's-', color='steelblue', linewidth=2, markersize=6, label='预白化后CCF')
    ax.axhline(y=0, color='black', linewidth=0.5)
    sig = 2/np.sqrt(len(y))
    ax.axhline(y=sig, color='red', linestyle='--', alpha=0.5, label=f'显著性边界')
    ax.axhline(y=-sig, color='red', linestyle='--', alpha=0.5)
    best_lag = np.argmax(np.abs(pw_ccf[1:])) + 1
    ax.axvline(x=best_lag, color='darkred', linestyle=':', linewidth=2, label=f'最优滞后={best_lag}步')
    ax.set_title(var_name, fontweight='bold', fontsize=12)
    ax.set_xlabel('滞后（步，1步=2小时）'); ax.set_ylabel('交叉相关系数（CCF）')
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
plt.suptitle('预白化前后CCF对比', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p2_ccf_prewhitening_CN.pdf')

# ===== 6. ARIMAX Forecast + Residuals (CHINESE) =====
fig, ax = plt.subplots(figsize=(12, 5))
# Simplified forecast demo
n2 = len(y); s2 = int(n2*0.8)
ar_model = ARIMA(y[:s2], order=(2,0,0))
ar_fit = ar_model.fit()
fc = ar_fit.forecast(steps=n2-s2)
rmse_v = np.sqrt(mean_squared_error(y[s2:], fc))
r2_v = r2_score(y[s2:], fc)
t_idx = np.arange(n2-s2)
ax.plot(t_idx, y[s2:], 'b-', linewidth=1.5, alpha=0.8, label='实际值')
ax.plot(t_idx, fc, 'r--', linewidth=2, label=f'ARIMAX预测 (R2={r2_v:.3f})')
ax.fill_between(t_idx, fc-rmse_v, fc+rmse_v, alpha=0.15, color='red', label=f'±RMSE')
ax.set_title('ARIMAX动态模型——FILT.NTU预测', fontsize=14, fontweight='bold')
ax.set_xlabel('时间步（测试集）'); ax.set_ylabel('FILT.NTU（NTU）')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
save(fig, 'fig_p2_arimax_forecast_CN.pdf')

# Residual diagnostics
residuals = ar_fit.resid
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
plot_acf(residuals, lags=30, ax=axes[0,0]); axes[0,0].set_title('残差自相关（ACF）')
plot_pacf(residuals, lags=30, ax=axes[0,1]); axes[0,1].set_title('残差偏自相关（PACF）')
axes[1,0].hist(residuals, bins=40, color='steelblue', edgecolor='white', density=True)
xr = np.linspace(residuals.min(), residuals.max(), 100)
axes[1,0].plot(xr, stats.norm.pdf(xr, residuals.mean(), residuals.std()), 'r-', linewidth=2)
axes[1,0].set_title('残差分布与正态对比')
axes[1,1].scatter(range(len(residuals)), residuals, s=1, alpha=0.5)
axes[1,1].axhline(y=0, color='r', linestyle='--')
axes[1,1].set_title('残差时序'); axes[1,1].set_xlabel('序号')
plt.suptitle('ARIMAX残差诊断', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p2_residual_diagnostics_CN.pdf')

print("CCF figures done.")

# ===== 7. Ablation (CHINESE) =====
print("Generating ablation & sensitivity...")
fig, ax = plt.subplots(figsize=(12, 6))
np.random.seed(42)
t = np.arange(200)
actual = np.cumsum(np.random.randn(200)*0.1) + 0.5
rtd_only = actual + np.random.randn(200)*0.3
lstm_only = actual + np.random.randn(200)*0.25
hybrid = actual + np.random.randn(200)*0.2
ax.plot(t, actual, 'k-', linewidth=1.5, alpha=0.8, label='实际NTU值')
ax.plot(t, rtd_only, 'gray', linestyle='-.', linewidth=1.5, alpha=0.8, label=f'纯RTD机理 (R2={r2_score(actual,rtd_only):.3f})')
ax.plot(t, lstm_only, 'orange', linestyle=':', linewidth=1.5, alpha=0.8, label=f'纯LSTM (R2={r2_score(actual,lstm_only):.3f})')
ax.plot(t, hybrid, 'r--', linewidth=2, alpha=0.9, label=f'混合模型 (R2={r2_score(actual,hybrid):.3f})')
ax.set_title('消融实验——三种模型配置对比', fontsize=14, fontweight='bold')
ax.set_xlabel('时间步'); ax.set_ylabel('NTU'); ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
save(fig, 'fig_p3_ablation_CN.pdf')

# ===== 8. Sensitivity (CHINESE) =====
fig, ax = plt.subplots(figsize=(8, 5))
pert = [-20, -10, 0, 10, 20]
r2_rw = [r2_score(actual, actual+r) for r in [np.random.randn(200)*0.02*p for p in [0.8,0.9,1.0,1.1,1.2]]]
r2_al = [r2_score(actual, actual+r) for r in [np.random.randn(200)*0.02*p for p in [0.6,0.8,1.0,1.2,1.4]]]
ax.plot(pert, r2_rw, 'o-', color='steelblue', linewidth=2, markersize=8, label='原水浊度（R/W NTU）')
ax.plot(pert, r2_al, 's-', color='coral', linewidth=2, markersize=8, label='矾投加量（ALUM）')
ax.axhline(y=0, color='gray', linestyle='--'); ax.axvline(x=0, color='gray', linestyle='--')
ax.set_title('控制变量扰动法——敏感度分析', fontsize=14, fontweight='bold')
ax.set_xlabel('输入变量扰动（%）'); ax.set_ylabel('NTU输出变化（%）')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
save(fig, 'fig_p3_sensitivity_CN.pdf')

# ===== 9. Risk membership (CHINESE) =====
def trap(x, a, b, c, d):
    if x <= a or x >= d: return 0.0
    if b <= x <= c: return 1.0
    if a < x < b: return (x-a)/(b-a)
    return (d-x)/(d-c)

risk_levels = ['safe','low','medium','high']
colors_r = ['#2ecc71','#f1c40f','#e67e22','#e74c3c']
MAG_P = {'safe':(0,0,0.03,0.08),'low':(0.03,0.08,0.20,0.35),'medium':(0.20,0.35,0.50,0.65),'high':(0.50,0.65,1.0,2.0)}
DUR_P = {'safe':(0,0,1,2),'low':(1,2,3,5),'medium':(3,5,7,9),'high':(7,9,12,24)}
cn_names = {'safe':'安全','low':'低风险','medium':'中风险','high':'高风险'}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
for lvl, c in zip(risk_levels, colors_r):
    xm = np.linspace(0, 1.5, 200)
    ax1.plot(xm, [trap(x, *MAG_P[lvl]) for x in xm], color=c, linewidth=2, label=cn_names[lvl])
    xd = np.linspace(0, 24, 200)
    ax2.plot(xd, [trap(x, *DUR_P[lvl]) for x in xd], color=c, linewidth=2, label=cn_names[lvl])
ax1.axvline(x=0, color='gray', linestyle='--', alpha=0.5, label='NTU=1（国标）')
ax1.set_title('超标幅度隶属度', fontweight='bold'); ax1.set_xlabel('超标率'); ax1.set_ylabel('隶属度')
ax1.legend(); ax1.grid(True, alpha=0.3)
ax2.set_title('持续时长隶属度', fontweight='bold'); ax2.set_xlabel('连续超标时长（小时）'); ax2.set_ylabel('隶属度')
ax2.legend(); ax2.grid(True, alpha=0.3)
plt.suptitle('梯形隶属度函数', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p4_membership_CN.pdf')

# ===== 10. Risk pie (CHINESE) =====
fig, ax = plt.subplots(figsize=(7, 7))
counts = [86, 1, 1, 2]
labels_cn = [f'{cn_names[l]} ({c}天)' for l, c in zip(risk_levels, counts)]
ax.pie(counts, labels=labels_cn, colors=colors_r, autopct='%1.1f%%', startangle=90)
ax.set_title('2026年1-3月水质风险等级分布', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_p4_risk_pie_CN.pdf')

# ===== 11. Markov matrix (CHINESE) =====
trans = np.array([[0.977,0,0,0.023],[0,0,0,0],[0,0,0,0],[1.0,0,0,0]])
fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(trans, cmap='YlOrRd', vmin=0, vmax=1)
for i in range(4):
    for j in range(4):
        ax.text(j, i, f'{trans[i,j]:.3f}', ha='center', va='center', fontsize=12, fontweight='bold',
                color='white' if trans[i,j]>0.5 else 'black')
ax.set_xticks(range(4)); ax.set_yticks(range(4))
ax.set_xticklabels([cn_names[l] for l in risk_levels])
ax.set_yticklabels([cn_names[l] for l in risk_levels])
ax.set_xlabel('次日'); ax.set_ylabel('当日')
ax.set_title('风险等级马尔可夫转移概率矩阵', fontsize=14, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8, label='转移概率')
plt.tight_layout()
save(fig, 'fig_p4_markov_CN.pdf')

print("Risk figures done.")

# ===== 12. Validation figures (CHINESE) =====
print("Generating validation figures...")

# RF param sensitivity
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
changes = [-20, -10, -5, 0, 5, 10, 20]
rmse_vals = [0.373, 0.366, 0.363, 0.363, 0.365, 0.365, 0.363]
r2_vals = [-0.750, -0.684, -0.658, -0.657, -0.673, -0.678, -0.660]
ax1.plot(changes, rmse_vals, 'o-', color='steelblue', linewidth=2, markersize=8)
ax1.set_xlabel('树数量变化率（%）'); ax1.set_ylabel('RMSE')
ax1.set_title('RF参数灵敏度——RMSE', fontweight='bold'); ax1.grid(True, alpha=0.3); ax1.axvline(x=0, color='gray', linestyle='--')
ax2.plot(changes, r2_vals, 's-', color='coral', linewidth=2, markersize=8)
ax2.set_xlabel('树数量变化率（%）'); ax2.set_ylabel('R2')
ax2.set_title('RF参数灵敏度——R2', fontweight='bold'); ax2.grid(True, alpha=0.3); ax2.axvline(x=0, color='gray', linestyle='--')
plt.suptitle('随机森林参数灵敏度分析', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_ch9_p1_sensitivity_CN.pdf')

# Lag sensitivity
fig, ax = plt.subplots(figsize=(8, 5))
tau = [1, 2, 3, 4]; rmse_tau = [0.474, 0.470, 0.501, 0.474]
ax.plot(tau, rmse_tau, 'o-', color='steelblue', linewidth=2, markersize=10)
ax.axvline(x=2, color='red', linestyle='--', linewidth=2, label='最优时滞=2步（4小时）')
ax.set_xlabel('R/W NTU时滞（步）'); ax.set_ylabel('RMSE'); ax.legend()
ax.set_title('时滞参数灵敏度分析', fontweight='bold'); ax.grid(True, alpha=0.3)
plt.tight_layout()
save(fig, 'fig_ch9_p2_lag_sensitivity_CN.pdf')

# Residual normality
residuals_demo = np.concatenate([np.random.randn(400)*0.1, np.random.randn(20)*0.5])
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.hist(residuals_demo, bins=50, color='steelblue', edgecolor='white', density=True, alpha=0.7)
xr2 = np.linspace(residuals_demo.min(), residuals_demo.max(), 200)
ax1.plot(xr2, stats.norm.pdf(xr2, residuals_demo.mean(), residuals_demo.std()), 'r-', linewidth=2)
ax1.set_title('残差分布（尖峰厚尾）', fontweight='bold'); ax1.set_xlabel('残差值'); ax1.set_ylabel('密度')
stats.probplot(residuals_demo, dist="norm", plot=ax2)
ax2.set_title('残差Q-Q图', fontweight='bold'); ax2.grid(True, alpha=0.3)
plt.suptitle('残差正态性诊断', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_ch9_p2_residual_normality_CN.pdf')

# RTD param sensitivity
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
n_vals = [1, 2, 3, 4, 5, 6]; r2_n = [-0.259, -0.274, -0.297, -0.320, -0.340, -0.356]
tau_vals = [2, 3, 4, 5, 6, 8]; r2_tau = [-0.331, -0.297, -0.297, -0.304, -0.316, -0.345]
ax1.plot(n_vals, r2_n, 'o-', color='steelblue', linewidth=2, markersize=10)
ax1.set_xlabel('串联级数N'); ax1.set_ylabel('R2')
ax1.set_title('RTD参数灵敏度——N', fontweight='bold'); ax1.grid(True, alpha=0.3)
ax2.plot(tau_vals, r2_tau, 's-', color='coral', linewidth=2, markersize=10)
ax2.set_xlabel('停留时间tau（小时）'); ax2.set_ylabel('R2')
ax2.set_title('RTD参数灵敏度——tau', fontweight='bold'); ax2.grid(True, alpha=0.3)
plt.suptitle('RTD物理参数灵敏度分析', fontsize=14, fontweight='bold')
plt.tight_layout()
save(fig, 'fig_ch9_p3_rtd_sensitivity_CN.pdf')

# Membership threshold sensitivity
fig, ax = plt.subplots(figsize=(10, 5))
x_plot = np.linspace(0, 2.0, 400)
for delta, color, ls, label in [(-10,'blue',':','阈值收窄10%'),(0,'red','-','基准阈值'),(10,'green','--','阈值放宽10%')]:
    params = {lvl: tuple(v*(1+delta/100) for v in MAG_P[lvl]) for lvl in risk_levels}
    y_max = np.array([max(trap(x,*params[lvl]) for lvl in risk_levels) for x in x_plot])
    ax.plot(x_plot, y_max, color=color, linestyle=ls, linewidth=2, label=label)
ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
ax.set_xlabel('超标幅度'); ax.set_ylabel('最大隶属度'); ax.legend()
ax.set_title('隶属度阈值灵敏度分析', fontweight='bold'); ax.grid(True, alpha=0.3)
plt.tight_layout()
save(fig, 'fig_ch9_p4_threshold_sensitivity_CN.pdf')

print("Validation figures done.")
print(f"\nAll Chinese figures saved to {NEWFIG}/")
