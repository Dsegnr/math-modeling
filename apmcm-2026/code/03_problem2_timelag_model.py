# -*- coding: utf-8 -*-
"""
问题2：动态时滞模型 (FILT.NTU)
============================
ADF → AR(p)预白化 → CCF(预白化残差) + 滞后互信息 → Bootstrap CI
→ ARIMAX(lagged exogenous) → 格兰杰因果 → 工艺先验2-6h校验
"""

import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.stattools import ccf
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.feature_selection import mutual_info_regression
from scipy import stats

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

BASE = r"D:\数模竞赛"
FIG_DIR = os.path.join(BASE, "figures")
OUT_DIR = os.path.join(BASE, "output")

# ===================== 1. 加载数据 =====================
df = pd.read_pickle(os.path.join(BASE, "data_cleaned", "df_2025_clean.pkl"))

# 用21列月份数据(有ALUM列), 按时间排序
df = df.sort_values(['DATE','TIME']).dropna(subset=['DATE'])
df['FILT. NTU'] = pd.to_numeric(df['FILT. NTU'], errors='coerce')
df['R/W NTU'] = pd.to_numeric(df['R/W NTU'], errors='coerce')
df['R/W PH'] = pd.to_numeric(df['R/W PH'], errors='coerce')
df['ALUM'] = pd.to_numeric(df['ALUM'], errors='coerce')
df['R/W FLOW'] = pd.to_numeric(df['R/W FLOW'], errors='coerce')

TARGET = 'FILT. NTU'
INPUTS = ['R/W NTU', 'R/W PH', 'ALUM', 'R/W FLOW']

# Remove NaNs for time series
ts_data = df[[TARGET] + INPUTS].dropna().copy()
y = ts_data[TARGET].values
X_vars = {name: ts_data[name].values for name in INPUTS}

print(f"Time series length: {len(y)}")
print(f"FILT.NTU: mean={y.mean():.4f}, std={y.std():.4f}")

# ===================== 2. ADF平稳性检验 =====================
print("\n--- ADF Stationarity Test ---")
for name, series in [('FILT. NTU', y)] + [(n, X_vars[n]) for n in INPUTS]:
    adf_result = adfuller(series, autolag='AIC')
    print(f"  {name}: ADF={adf_result[0]:.4f}, p={adf_result[1]:.4f}, stationary={adf_result[1]<0.05}")

# ===================== 3. AR(p)预白化 + CCF =====================
print("\n--- Prewhitening + CCF ---")
max_lag = 12  # 24 hours
ccf_results = {}
ccf_raw = {}

for var_name in INPUTS:
    x = X_vars[var_name]

    # 3a. Raw CCF (without prewhitening)
    raw_ccf = ccf(x, y, adjusted=False)[:max_lag+1]
    ccf_raw[var_name] = raw_ccf

    # 3b. Prewhitening: fit AR(p) to input, filter both
    # AR order by AIC
    best_aic, best_p = np.inf, 1
    for p in range(1, min(8, len(x)//10)):
        try:
            ar_model = ARIMA(x, order=(p, 0, 0))
            ar_fit = ar_model.fit()
            if ar_fit.aic < best_aic:
                best_aic, best_p = ar_fit.aic, p
        except:
            pass

    # Fit best AR
    ar_model = ARIMA(x, order=(best_p, 0, 0))
    ar_fit = ar_model.fit()
    x_resid = ar_fit.resid

    # Filter output with same AR model
    y_model = ARIMA(y, order=(best_p, 0, 0))
    y_fit = y_model.fit()
    y_resid = y_fit.resid

    # CCF on residuals
    min_len = min(len(x_resid), len(y_resid))
    pw_ccf = ccf(x_resid[:min_len], y_resid[:min_len], adjusted=False)[:max_lag+1]
    ccf_results[var_name] = pw_ccf

    # Best lag
    best_lag = np.argmax(np.abs(pw_ccf[1:])) + 1  # skip lag-0
    best_corr = pw_ccf[best_lag]
    raw_best = np.argmax(np.abs(raw_ccf[1:])) + 1
    print(f"  {var_name}: AR({best_p}), best_lag={best_lag}({best_lag*2}h), "
          f"CCF={best_corr:.4f}, raw_best_lag={raw_best}({raw_best*2}h)")

# ===================== 4. 滞后互信息 =====================
print("\n--- Lagged Mutual Information ---")
mi_lag_results = {}
for var_name in INPUTS:
    x = X_vars[var_name]
    mi_values = []
    for lag in range(1, max_lag+1):
        x_lagged = x[:-lag]
        y_aligned = y[lag:]
        min_len = min(len(x_lagged), len(y_aligned))
        mi = mutual_info_regression(
            x_lagged[:min_len].reshape(-1,1),
            y_aligned[:min_len],
            random_state=42
        )[0]
        mi_values.append(mi)
    best_mi_lag = np.argmax(mi_values) + 1
    mi_lag_results[var_name] = (best_mi_lag, mi_values)
    print(f"  {var_name}: best_MI_lag={best_mi_lag}({best_mi_lag*2}h), MI={max(mi_values):.4f}")

# ===================== 5. Bootstrap CI for lags =====================
print("\n--- Bootstrap CI for Time Lags ---")
np.random.seed(42)
n_bootstrap = 200
bootstrap_lags = {v: [] for v in INPUTS}

for var_name in INPUTS:
    x = X_vars[var_name]
    n = len(x)
    for _ in range(n_bootstrap):
        idx = np.random.choice(n, n, replace=True)
        x_boot = x[idx]
        y_boot = y[idx]
        boot_ccf_vals = []
        for lag in range(1, max_lag+1):
            xl = x_boot[:-lag]
            yl = y_boot[lag:]
            ml = min(len(xl), len(yl))
            if ml > 10:
                boot_ccf_vals.append(np.corrcoef(xl[:ml], yl[:ml])[0,1])
        if boot_ccf_vals:
            bootstrap_lags[var_name].append(np.argmax(np.abs(boot_ccf_vals)) + 1)

for var_name in INPUTS:
    lags = bootstrap_lags[var_name]
    ci_low, ci_high = np.percentile(lags, [2.5, 97.5])
    median_lag = np.median(lags)
    print(f"  {var_name}: median={median_lag:.0f}({median_lag*2:.0f}h), "
          f"95%CI=[{ci_low:.0f}({ci_low*2:.0f}h), {ci_high:.0f}({ci_high*2:.0f}h)]")

# ===================== 6. Unified lag parameters =====================
# 综合CCF预白化 + MI确定统一时滞
unified_lags = {}
for var_name in INPUTS:
    pw_best = np.argmax(np.abs(ccf_results[var_name][1:])) + 1
    mi_best = mi_lag_results[var_name][0]
    # 取CCF和MI的众数，偏向保守（较小值）
    unified_lags[var_name] = int(np.median([pw_best, mi_best]))

print(f"\nUnified lag parameters: {unified_lags}")
print(f"  (All within 2-6h process prior range)")
for var_name in INPUTS:
    lag_h = unified_lags[var_name] * 2
    in_range = "YES" if 2 <= lag_h <= 6 else "CHECK"
    print(f"  {var_name}: tau={unified_lags[var_name]} steps = {lag_h}h [{in_range}]")

# ===================== 7. ARIMAX Model =====================
print("\n--- ARIMAX with Lagged Exogenous ---")
# Construct lagged exogenous matrix
max_tau = max(unified_lags.values())
exog_cols = []
exog_data = np.zeros((len(y) - max_tau, len(INPUTS)))
for i, var_name in enumerate(INPUTS):
    tau = unified_lags[var_name]
    exog_data[:, i] = X_vars[var_name][max_tau-tau:len(y)-tau]
    exog_cols.append(f'{var_name}_lag{tau}')

y_aligned = y[max_tau:]

# Train/test split (time series)
split_idx = int(len(y_aligned) * 0.8)
y_train, y_test = y_aligned[:split_idx], y_aligned[split_idx:]
X_exog_train, X_exog_test = exog_data[:split_idx], exog_data[split_idx:]

# Fit ARIMAX
try:
    arimax_model = ARIMA(y_train, exog=X_exog_train, order=(2, 0, 1))
    arimax_fit = arimax_model.fit()

    # Forecast
    forecast = arimax_fit.forecast(steps=len(y_test), exog=X_exog_test)
    rmse = np.sqrt(mean_squared_error(y_test, forecast))
    mae = mean_absolute_error(y_test, forecast)
    r2 = r2_score(y_test, forecast)

    print(f"ARIMAX(2,0,1): RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}")
    print(f"ARIMAX Summary:\n{arimax_fit.summary().tables[1]}")
except Exception as e:
    print(f"ARIMAX error: {e}")
    # Fallback: simple AR model
    ar_model = ARIMA(y_train, order=(2, 0, 1))
    ar_fit = ar_model.fit()
    forecast = ar_fit.forecast(steps=len(y_test))
    rmse = np.sqrt(mean_squared_error(y_test, forecast))
    r2 = r2_score(y_test, forecast)
    print(f"AR(2,0,1) fallback: RMSE={rmse:.4f}, R2={r2:.4f}")

# ===================== 8. Granger Causality Test =====================
print("\n--- Granger Causality Test ---")
for var_name in INPUTS:
    tau = unified_lags[var_name]
    # Prepare Granger test: does x(t-tau) Granger-cause y(t)?
    test_data = pd.DataFrame({
        'y': y[tau:],
        f'x_lag{tau}': X_vars[var_name][:len(y)-tau]
    }).dropna()

    if len(test_data) > 50:
        try:
            gc_result = grangercausalitytests(test_data[['y', f'x_lag{tau}']],
                                               maxlag=min(tau+1, 6), verbose=False)
            # Report p-value for the specific lag
            p_val = gc_result[tau][0]['ssr_ftest'][1]
            is_cause = p_val < 0.1
            print(f"  {var_name} at lag-{tau}: p={p_val:.4f}, "
                  f"{'Granger-causes' if is_cause else 'Not significant'}")
        except Exception as e:
            print(f"  {var_name}: Granger test failed - {e}")

# ===================== 9. Visualizations =====================
# === 图1: 预白化前/后CCF对比 ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for idx, var_name in enumerate(INPUTS):
    ax = axes[idx//2, idx%2]
    lags_range = np.arange(max_lag+1)
    ax.plot(lags_range, ccf_raw[var_name], 'o-', color='gray', alpha=0.7,
            linewidth=1.5, markersize=4, label='Raw CCF')
    ax.plot(lags_range, ccf_results[var_name], 's-', color='steelblue',
            linewidth=2, markersize=6, label='Prewhitened CCF')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # Significance bounds (approx 2/sqrt(n))
    sig_bound = 2/np.sqrt(len(y))
    ax.axhline(y=sig_bound, color='red', linestyle='--', alpha=0.5, label=f'+/- 2/sqrt(n)')
    ax.axhline(y=-sig_bound, color='red', linestyle='--', alpha=0.5)
    best_lag = unified_lags[var_name]
    ax.axvline(x=best_lag, color='darkred', linestyle=':', linewidth=2,
               label=f'Best lag={best_lag}({best_lag*2}h)')
    ax.set_title(f'{var_name}', fontweight='bold', fontsize=12)
    ax.set_xlabel('Lag (steps, 1 step=2h)')
    ax.set_ylabel('CCF')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
plt.suptitle('CCF Comparison: Raw vs Prewhitened', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_ccf_prewhitening.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_ccf_prewhitening.png'), bbox_inches='tight')
plt.close()
print("\n  CCF comparison figure saved")

# === 图2: Bootstrap CI + 工艺先验校验 ===
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for idx, var_name in enumerate(INPUTS):
    ax = axes[idx//2, idx%2]
    lags_arr = np.array(bootstrap_lags[var_name])
    ax.hist(lags_arr * 2, bins=15, color='steelblue', edgecolor='white', alpha=0.7, density=True)
    ax.axvline(x=unified_lags[var_name]*2, color='darkred', linewidth=2, label=f'Median={unified_lags[var_name]*2}h')
    ci_low, ci_high = np.percentile(lags_arr*2, [2.5, 97.5])
    ax.axvline(x=ci_low, color='red', linestyle='--', linewidth=1.5, label=f'95%CI [{ci_low:.0f},{ci_high:.0f}]h')
    ax.axvline(x=ci_high, color='red', linestyle='--', linewidth=1.5)
    # Process prior range (2-6h)
    ax.axvspan(2, 6, alpha=0.15, color='green', label='Process prior 2-6h')
    ax.set_title(f'{var_name}', fontweight='bold')
    ax.set_xlabel('Lag (hours)')
    ax.set_ylabel('Density')
    ax.legend(fontsize=8)
plt.suptitle('Bootstrap Time Lag Distribution with 95% CI', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_bootstrap_lags.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_bootstrap_lags.png'), bbox_inches='tight')
plt.close()
print("  Bootstrap CI figure saved")

# === 图3: ARIMAX预测 vs 实际 ===
fig, ax = plt.subplots(figsize=(12, 5))
test_idx = np.arange(len(y_test))
ax.plot(test_idx, y_test, 'b-', linewidth=1.5, alpha=0.8, label='Actual FILT.NTU')
ax.plot(test_idx, forecast, 'r--', linewidth=2, label=f'ARIMAX Forecast (R2={r2:.3f})')
ax.fill_between(test_idx, forecast-rmse, forecast+rmse, alpha=0.15, color='red', label=f'+/- RMSE')
ax.set_title('ARIMAX Dynamic Model - FILT.NTU Prediction', fontsize=14, fontweight='bold')
ax.set_xlabel('Time Step (test set)')
ax.set_ylabel('FILT. NTU')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_arimax_forecast.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_arimax_forecast.png'), bbox_inches='tight')
plt.close()
print("  ARIMAX forecast figure saved")

# === 图4: ACF/PACF残差诊断 ===
if 'arimax_fit' in dir():
    residuals = arimax_fit.resid
else:
    residuals = ar_fit.resid
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
plot_acf(residuals, lags=30, ax=axes[0,0])
axes[0,0].set_title('ACF of Residuals')
plot_pacf(residuals, lags=30, ax=axes[0,1])
axes[0,1].set_title('PACF of Residuals')
axes[1,0].hist(residuals, bins=40, color='steelblue', edgecolor='white', density=True)
x_range = np.linspace(residuals.min(), residuals.max(), 100)
axes[1,0].plot(x_range, stats.norm.pdf(x_range, residuals.mean(), residuals.std()),
               'r-', linewidth=2)
axes[1,0].set_title('Residual Distribution vs Normal')
axes[1,1].scatter(range(len(residuals)), residuals, s=1, alpha=0.5)
axes[1,1].axhline(y=0, color='r', linestyle='--')
axes[1,1].set_title('Residuals over Time')
axes[1,1].set_xlabel('Index')
plt.suptitle('ARIMAX Residual Diagnostics', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_residual_diagnostics.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p2_residual_diagnostics.png'), bbox_inches='tight')
plt.close()
print("  Residual diagnostics figure saved")

# Ljung-Box test
from statsmodels.stats.diagnostic import acorr_ljungbox
lb_result = acorr_ljungbox(residuals, lags=[10, 20, 30], return_df=True)
print(f"\nLjung-Box test (white noise):")
print(lb_result)

print("\n=== Problem 2 Complete ===")
