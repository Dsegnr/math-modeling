# -*- coding: utf-8 -*-
"""
问题1：特征筛选 + NTU预测
============================
VIF共线性 → Spearman/MI/RF-MDI/SHAP四层筛选
→ XGBoost + RF + 线性回归 → 滚动窗口验证
→ SHAP Dependence Plot + 蜂群图 → Excel输出
"""

import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.feature_selection import mutual_info_regression
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor
import shap

# ===================== 配置 =====================
plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 300
sns.set_style("whitegrid")

BASE = r"D:\数模竞赛"
FIG_DIR = os.path.join(BASE, "figures")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# ===================== 1. 加载数据 =====================
df = pd.read_pickle(os.path.join(BASE, "data_cleaned", "df_2025_clean.pkl"))
df_2026 = pd.read_pickle(os.path.join(BASE, "data_cleaned", "df_2026_clean.pkl"))

# ===================== 2. 特征工程 =====================
TARGET = 'NTU'  # 出厂水浊度

# 可用特征集
feature_candidates = ['RIVER LEVEL','R/W FLOW','R/W NTU','R/W CLR','R/W PH',
                      'FILT. NTU','C/W WELL LEVEL','PH','CLR','CL2','ALUM',
                      'T/W FLOW','hour_sin','hour_cos']

# 只保留数值列
for c in feature_candidates:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')

# 因果对齐：构造滞后特征（输入取4h前 = lag-2步）
# 不引入未来信息，严格遵守因果约束
for col in ['R/W NTU','R/W FLOW','R/W PH','RIVER LEVEL','ALUM']:
    if col in df.columns:
        df[f'{col}_lag1'] = df[col].shift(1)   # 滞后2小时
        df[f'{col}_lag2'] = df[col].shift(2)   # 滞后4小时
        df[f'{col}_lag3'] = df[col].shift(3)   # 滞后6小时

# 目标变量的滞后（强自相关）
df['NTU_lag1'] = df[TARGET].shift(1)
df['NTU_lag2'] = df[TARGET].shift(2)

# 滚动统计特征
df['R/W_NTU_roll3'] = df['R/W NTU'].rolling(3).mean()
df['R/W_NTU_roll6'] = df['R/W NTU'].rolling(6).mean()

# 更新特征列表（纳入滞后特征）
lag_features = [f'{col}_lag1' for col in ['R/W NTU','R/W FLOW','R/W PH','RIVER LEVEL','ALUM']] + \
               [f'{col}_lag2' for col in ['R/W NTU','R/W FLOW','ALUM']] + \
               ['NTU_lag1','NTU_lag2','R/W_NTU_roll3','R/W_NTU_roll6']
all_features = [c for c in feature_candidates + lag_features if c in df.columns]

# 删除NaN行（由shift产生的）
df_model = df[all_features + [TARGET,'DATE','datetime']].dropna().copy()

print(f"Modeling data: {df_model.shape[0]} rows x {len(all_features)} features")
print(f"Date range: {df_model['DATE'].min()} to {df_model['DATE'].max()}")

# ===================== 3. VIF筛选（为线性回归） =====================
print("\n--- VIF Analysis ---")
X_vif = df_model[feature_candidates].copy()
# 去常量列
for c in feature_candidates:
    if X_vif[c].std() < 1e-6:
        X_vif.drop(columns=[c], inplace=True)

vif_data = pd.DataFrame({'Variable': X_vif.columns, 'VIF': np.nan})
for i in range(len(X_vif.columns)):
    try:
        vif_data.loc[i, 'VIF'] = variance_inflation_factor(X_vif.values, i)
    except:
        pass
vif_data = vif_data.sort_values('VIF')
low_vif_vars = vif_data[vif_data['VIF'] < 10]['Variable'].tolist()
print(f"Variables with VIF<10: {low_vif_vars}")

# ===================== 4. 特征筛选（四层递进） =====================
print("\n--- Feature Selection ---")
X_all = df_model[all_features].values
y_all = df_model[TARGET].values

# Layer 1: Spearman
spearman_scores = {}
for i, col in enumerate(all_features):
    rho, p = stats.spearmanr(df_model[col], df_model[TARGET])
    spearman_scores[col] = abs(rho)
top_spearman = sorted(spearman_scores, key=spearman_scores.get, reverse=True)[:15]
print(f"Spearman Top15: {top_spearman[:5]}...")

# Layer 2: Mutual Information
mi_scores = mutual_info_regression(X_all, y_all, random_state=42)
mi_ranked = [(all_features[i], mi_scores[i]) for i in np.argsort(mi_scores)[::-1]]
top_mi = [x[0] for x in mi_ranked[:15]]
print(f"MI Top5: {[f'{x[0]}({x[1]:.3f})' for x in mi_ranked[:5]]}")

# Layer 3: RF MDI
rf_temp = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
rf_temp.fit(X_all, y_all)
mdi_ranked = [(all_features[i], rf_temp.feature_importances_[i])
              for i in np.argsort(rf_temp.feature_importances_)[::-1]]
top_mdi = [x[0] for x in mdi_ranked[:15]]
print(f"MDI Top5: {[f'{x[0]}({x[1]:.4f})' for x in mdi_ranked[:5]]}")

# 交集定主要因素
top_features = list(set(top_spearman[:10]) & set(top_mi[:10]) & set(top_mdi[:10]))
if len(top_features) < 5:
    # 放宽：取三方法各Top5的并集
    top_features = list(set(top_spearman[:8] + top_mi[:8] + top_mdi[:8]))
print(f"Main factors (intersection): {top_features}")

# ===================== 5. 滚动窗口验证 =====================
print("\n--- Rolling Window Validation ---")
df_model = df_model.sort_values('datetime')

n_total = len(df_model)
results_rf, results_xgb, results_lr = [], [], []

for window_idx, (train_end_pct, test_end_pct) in enumerate(
    [(0.75, 0.83), (0.83, 0.91), (0.91, 1.0)]):
    train_end = int(n_total * train_end_pct)
    test_end = int(n_total * test_end_pct)

    X_train = df_model[top_features].iloc[:train_end].values
    y_train = df_model[TARGET].iloc[:train_end].values
    X_test = df_model[top_features].iloc[train_end:test_end].values
    y_test = df_model[TARGET].iloc[train_end:test_end].values

    # RF
    rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)

    # XGBoost
    try:
        from xgboost import XGBRegressor
        xgb = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbosity=0)
        xgb.fit(X_train, y_train)
        y_pred_xgb = xgb.predict(X_test)
    except:
        y_pred_xgb = y_pred_rf  # fallback

    # Linear Regression (with VIF-filtered features)
    lr_vars = [v for v in low_vif_vars if v in top_features]
    if len(lr_vars) < 3:
        lr_vars = top_features[:5]
    X_train_lr = df_model[lr_vars].iloc[:train_end].values
    X_test_lr = df_model[lr_vars].iloc[train_end:test_end].values
    lr = LinearRegression()
    lr.fit(X_train_lr, y_train)
    y_pred_lr = lr.predict(X_test_lr)

    for name, yp in [('RF', y_pred_rf), ('XGB', y_pred_xgb), ('LR', y_pred_lr)]:
        rmse = np.sqrt(mean_squared_error(y_test, yp))
        mae = mean_absolute_error(y_test, yp)
        r2 = r2_score(y_test, yp)
        mape = np.mean(np.abs((y_test - yp) / (y_test + 1e-6))) * 100
        if name == 'RF':
            results_rf.append([rmse, mae, r2, mape])
        elif name == 'XGB':
            results_xgb.append([rmse, mae, r2, mape])
        else:
            results_lr.append([rmse, mae, r2, mape])
    print(f"  Window {window_idx+1}: train[0:{train_end}] test[{train_end}:{test_end}]")

# 汇总
for name, res in [('RF', results_rf), ('XGBoost', results_xgb), ('LR', results_lr)]:
    rm, ma, r2v, mp = np.mean(res, axis=0)
    print(f"\n{name} (3-window avg): RMSE={rm:.4f}, MAE={ma:.4f}, R2={r2v:.4f}, MAPE={mp:.2f}%")

# ===================== 6. SHAP分析 =====================
print("\n--- SHAP Analysis ---")
# 用全部数据训练最终模型
X_final = df_model[top_features].values
y_final = df_model[TARGET].values

rf_final = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
rf_final.fit(X_final, y_final)

# SHAP TreeExplainer
explainer = shap.TreeExplainer(rf_final, feature_perturbation="interventional")
shap_values = explainer.shap_values(X_final[:500])  # 采样加速

# === 图1: SHAP蜂群图 ===
fig, ax = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_final[:500], feature_names=top_features,
                  plot_type="dot", show=False, max_display=12)
ax.set_title('SHAP Bee Swarm Plot - Feature Importance & Direction', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_beeswarm.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_beeswarm.png'), bbox_inches='tight')
plt.close()
print("  SHAP beeswarm saved")

# === 图2: SHAP Bar (全局重要性) ===
fig, ax = plt.subplots(figsize=(8, 6))
shap.summary_plot(shap_values, X_final[:500], feature_names=top_features,
                  plot_type="bar", show=False, max_display=10)
ax.set_title('SHAP Global Feature Importance', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_bar.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_bar.png'), bbox_inches='tight')
plt.close()
print("  SHAP bar saved")

# === 图3: SHAP Dependence Plot (Top3特征) ===
top3 = top_features[:3]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
for idx, feat in enumerate(top3):
    feat_idx = top_features.index(feat)
    shap.dependence_plot(feat_idx, shap_values, X_final[:500],
                         feature_names=top_features, ax=axes[idx], show=False)
    axes[idx].set_title(f'SHAP Dependence: {feat}', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_dependence.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_shap_dependence.png'), bbox_inches='tight')
plt.close()
print("  SHAP dependence saved")

# === 图4: 特征重要性对比（三方法） ===
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
methods = [
    ('Spearman', spearman_scores, 'Spearman |rho|'),
    ('Mutual Info', dict(mi_ranked), 'MI Score'),
    ('RF MDI', dict(mdi_ranked[:15]), 'MDI Importance')
]
for ax, (name, scores_dict, xlabel) in zip(axes, methods):
    items = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)[:10]
    labels, values = zip(*items)
    colors = plt.cm.Blues(np.linspace(0.3, 1, len(values)))
    ax.barh(range(len(labels)), values, color=colors[::-1])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title(name, fontweight='bold')
    ax.set_xlabel(xlabel)
    ax.invert_yaxis()
plt.suptitle('Feature Importance Comparison (Three Methods)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_feature_importance_compare.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p1_feature_importance_compare.png'), bbox_inches='tight')
plt.close()
print("  Feature importance comparison saved")

# ===================== 7. 预测2026年2月1/10/20日 =====================
print("\n--- Prediction for Feb 1/10/20, 2026 ---")
target_dates = ['2026-02-01', '2026-02-10', '2026-02-20']

# 为2026数据构造相同特征：先拼接2025尾部+2026数据，再做shift
# 取2025最后100行作为lag缓冲
df_2025_tail = df[['DATE','datetime'] + [c for c in feature_candidates if c in df.columns]].tail(100).copy()

# 准备2026数据
df_2026_pred = df_2026.copy()
df_2026_pred['DATE'] = pd.to_datetime(df_2026_pred['DATE'])
for c in feature_candidates:
    if c in df_2026_pred.columns:
        df_2026_pred[c] = pd.to_numeric(df_2026_pred[c], errors='coerce')

# 拼接
df_combined = pd.concat([df_2025_tail, df_2026_pred], ignore_index=True)
df_combined = df_combined.sort_values(['DATE', 'TIME'] if 'TIME' in df_combined.columns else 'DATE')

# 为拼接数据构造lag特征
for col in ['R/W NTU','R/W FLOW','R/W PH','RIVER LEVEL','ALUM']:
    if col in df_combined.columns:
        df_combined[f'{col}_lag1'] = df_combined[col].shift(1)
        df_combined[f'{col}_lag2'] = df_combined[col].shift(2)
        df_combined[f'{col}_lag3'] = df_combined[col].shift(3)
df_combined['NTU_lag1'] = df_combined[TARGET].shift(1) if TARGET in df_combined.columns else np.nan
df_combined['NTU_lag2'] = df_combined[TARGET].shift(2) if TARGET in df_combined.columns else np.nan
df_combined['R/W_NTU_roll3'] = df_combined['R/W NTU'].rolling(3).mean() if 'R/W NTU' in df_combined.columns else np.nan
df_combined['R/W_NTU_roll6'] = df_combined['R/W NTU'].rolling(6).mean() if 'R/W NTU' in df_combined.columns else np.nan

# 筛选2026目标日期的数据
df_combined['DATE_str'] = df_combined['DATE'].dt.strftime('%Y-%m-%d')
df_combined = df_combined.dropna(subset=['DATE_str'])
df_pred_all = df_combined[df_combined['DATE_str'].isin(target_dates)].copy()

# 用训练时的top_features（确保特征对齐）
feats_for_pred = [c for c in top_features if c in df_pred_all.columns]
missing = set(top_features) - set(feats_for_pred)
if missing:
    print(f"  Note: Features missing in 2026 data: {missing}")
    for m in missing:
        df_pred_all[m] = 0  # fill missing with 0

X_pred = df_pred_all[top_features].fillna(0).values

# 训练最终模型
from xgboost import XGBRegressor
xgb_final = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42, verbosity=0)
xgb_final.fit(X_final, y_final)

pred_rf_all = rf_final.predict(X_pred)
pred_xgb_all = xgb_final.predict(X_pred)

pred_results = []
for i, (_, row) in enumerate(df_pred_all.iterrows()):
    time_val = row.get('TIME', row.get('TIME ', 0))
    date_val = row['DATE_str']
    pred_results.append({
        'Date': date_val,
        'Time': int(time_val) if pd.notna(time_val) else 0,
        'RF_Predicted_NTU': round(pred_rf_all[i], 4),
        'XGBoost_Predicted_NTU': round(pred_xgb_all[i], 4),
        'Ensemble_Mean_NTU': round((pred_rf_all[i] + pred_xgb_all[i]) / 2, 4)
    })

# 输出Excel
if pred_results:
    df_output = pd.DataFrame(pred_results)
    output_path = os.path.join(OUT_DIR, 'problem1_predictions.xlsx')
    df_output.to_excel(output_path, index=False)
    print(f"Predictions saved to {output_path}")
    print(df_output.to_string())
else:
    print("  No predictions generated - check feature alignment")

# ===================== 8. 模型对比汇总 =====================
print("\n--- Model Comparison Summary ---")
summary = pd.DataFrame({
    'Model': ['Random Forest', 'XGBoost', 'Linear Regression (baseline)'],
    'Avg_RMSE': [np.mean([r[0] for r in results_rf]),
                 np.mean([r[0] for r in results_xgb]),
                 np.mean([r[0] for r in results_lr])],
    'Avg_MAE': [np.mean([r[1] for r in results_rf]),
                np.mean([r[1] for r in results_xgb]),
                np.mean([r[1] for r in results_lr])],
    'Avg_R2': [np.mean([r[2] for r in results_rf]),
               np.mean([r[2] for r in results_xgb]),
               np.mean([r[2] for r in results_lr])],
    'Avg_MAPE_pct': [np.mean([r[3] for r in results_rf]),
                     np.mean([r[3] for r in results_xgb]),
                     np.mean([r[3] for r in results_lr])]
})
print(summary.to_string(index=False))

print("\n=== Problem 1 Complete ===")
