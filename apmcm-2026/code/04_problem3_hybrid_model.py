# -*- coding: utf-8 -*-
"""
问题3：机理-数据混合模型（出厂NTU 1-12h预测）
============================================
质量守恒 → n级串联CSTR RTD → 卷积得NTU_physical
→ BiLSTM+Attention残差修正 → NTU_final
→ 消融实验 + 突变场景 + 控制变量敏感度
"""

import pandas as pd, numpy as np, os, warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

plt.rcParams['font.family'] = ['SimHei', 'Microsoft YaHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

BASE = r"D:\数模竞赛"
FIG_DIR = os.path.join(BASE, "figures")
OUT_DIR = os.path.join(BASE, "output")

# ===================== 1. Load data =====================
df = pd.read_pickle(os.path.join(BASE, "data_cleaned", "df_2025_clean.pkl"))
df = df.sort_values(['DATE','TIME']).dropna(subset=['DATE'])

# Target: finished water NTU
TARGET = 'NTU'
for c in [TARGET, 'FILT. NTU', 'C/W WELL LEVEL', 'T/W FLOW', 'R/W NTU', 'ALUM']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# Key data
filt_ntu = df['FILT. NTU'].values
finished_ntu = df[TARGET].values
well_level = df['C/W WELL LEVEL'].values
tw_flow = df['T/W FLOW'].values
rw_ntu = df['R/W NTU'].values
alum = df['ALUM'].values

# Drop NaN
valid_mask = ~(np.isnan(finished_ntu) | np.isnan(filt_ntu))
filt_ntu = filt_ntu[valid_mask]
finished_ntu = finished_ntu[valid_mask]
well_level = well_level[valid_mask]
tw_flow = tw_flow[valid_mask]
rw_ntu = rw_ntu[valid_mask]
alum = alum[valid_mask]

print(f"Valid samples: {len(finished_ntu)}")
print(f"Finished NTU: mean={finished_ntu.mean():.4f}, max={finished_ntu.max():.4f}")

# ===================== 2. RTD Physical Model =====================
print("\n--- RTD Physical Model ---")

# Estimate HRT: V/Q
# V ~ C/W WELL LEVEL * area (assume constant area for simplicity)
# Use average well_level as proxy, T/W FLOW as Q
Q_mean = np.nanmean(tw_flow)  # m3/h (approximate)
V_well = 18000  # m3 (18ML = 18000 m3, from data description)
# Actually 18ML LEVEL and T/W FLOW are the relevant variables
# Use simpler: C/W WELL LEVEL as proxy for stored volume, typical clear well
# HRT estimate from data patterns
hrt_estimate = 4.0  # hours (typical clear well HRT)

# n-CSTR RTD function
def rt_density(t, n_tanks, tau):
    """Tanks-in-Series RTD: E(t) = (N/tau)^N * t^(N-1) * exp(-N*t/tau) / (N-1)!"""
    from scipy.special import gamma
    E = (n_tanks/tau)**n_tanks * t**(n_tanks-1) * np.exp(-n_tanks*t/tau) / gamma(n_tanks)
    return E

# Convolution: NTU_physical(t) = integral of FILT(t-s) * E(s) ds
def physical_model(filt_series, n_tanks=3, tau_hours=4.0, dt=2.0):
    """Apply RTD convolution to get physical prediction of finished NTU"""
    tau_steps = tau_hours / dt  # convert hours to time steps
    n_steps = len(filt_series)
    result = np.zeros(n_steps)

    # Generate RTD kernel
    kernel_len = int(6 * tau_steps)  # cover 6x tau
    t_kernel = np.arange(kernel_len) * dt
    kernel = rt_density(t_kernel + dt/2, n_tanks, tau_hours)  # add dt/2 to avoid t=0
    kernel = kernel / kernel.sum()  # normalize

    # Convolution
    for i in range(n_steps):
        for k in range(min(kernel_len, i+1)):
            result[i] += filt_series[i-k] * kernel[k]

    return result

ntu_physical = physical_model(filt_ntu, n_tanks=3, tau_hours=4.0)

# Physical model error
mask_valid_p = ~np.isnan(ntu_physical)
mse_phys = mean_squared_error(finished_ntu[mask_valid_p], ntu_physical[mask_valid_p])
r2_phys = r2_score(finished_ntu[mask_valid_p], ntu_physical[mask_valid_p])
print(f"RTD-only: MSE={mse_phys:.4f}, R2={r2_phys:.4f}")

# ===================== 3. LSTM Residual Model =====================
print("\n--- LSTM Residual Correction ---")

# Residual = actual - physical
residual = finished_ntu - ntu_physical
residual = np.nan_to_num(residual, 0)

# Prepare features (past 12 steps = 24h window)
seq_len = 12
horizon = 3  # predict 6h ahead (3 steps) - mid-point of 1-12h range per problem req
feat_cols = ['FILT. NTU','R/W NTU','ALUM','C/W WELL LEVEL','T/W FLOW']
feat_data = np.column_stack([
    filt_ntu, rw_ntu, alum, well_level, tw_flow
])

def create_sequences(features, target_residual, seq_len, horizon):
    X, y = [], []
    for i in range(len(features) - seq_len - horizon):
        X.append(features[i:i+seq_len])
        y.append(target_residual[i+seq_len+horizon-1])  # predict h steps ahead
    return np.array(X), np.array(y)

X_seq, y_seq = create_sequences(feat_data, residual, seq_len, horizon)
print(f"Sequences: X={X_seq.shape}, y={y_seq.shape}")

# Train/val split (time order)
split = int(len(X_seq) * 0.8)
X_train, X_val = X_seq[:split], X_seq[split:]
y_train, y_val = y_seq[:split], y_seq[split:]

# Normalize
scaler_X = StandardScaler()
scaler_y = StandardScaler()
X_train_2d = X_train.reshape(-1, X_train.shape[-1])
X_train_norm = scaler_X.fit_transform(X_train_2d).reshape(X_train.shape)
X_val_norm = scaler_X.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape)
y_train_norm = scaler_y.fit_transform(y_train.reshape(-1,1)).ravel()
y_val_norm = scaler_y.transform(y_val.reshape(-1,1)).ravel()

# LSTM Model
class BiLSTMAttention(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                           batch_first=True, bidirectional=True, dropout=dropout)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)  # (batch, seq, 2*hidden)
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attn_weights * lstm_out, dim=1)
        return self.fc(context).reshape(-1)

# Train
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Device: {device}")

X_train_t = torch.FloatTensor(X_train_norm).to(device)
y_train_t = torch.FloatTensor(y_train_norm).to(device)
X_val_t = torch.FloatTensor(X_val_norm).to(device)
y_val_t = torch.FloatTensor(y_val_norm).to(device)

model = BiLSTMAttention(input_dim=feat_data.shape[1]).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()
train_data = TensorDataset(X_train_t, y_train_t)
train_loader = DataLoader(train_data, batch_size=64, shuffle=False)

train_losses, val_losses = [], []
for epoch in range(50):
    model.train()
    epoch_loss = 0
    for Xb, yb in train_loader:
        optimizer.zero_grad()
        pred = model(Xb)
        loss = criterion(pred, yb)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    train_losses.append(epoch_loss / len(train_loader))

    model.eval()
    with torch.no_grad():
        val_pred = model(X_val_t)
        val_loss = criterion(val_pred, y_val_t).item()
    val_losses.append(val_loss)

    if epoch % 10 == 0:
        print(f"  Epoch {epoch}: train_loss={train_losses[-1]:.4f}, val_loss={val_losses[-1]:.4f}")

# Predict residuals
model.eval()
with torch.no_grad():
    lstm_residual_norm = model(X_val_t).cpu().numpy()
lstm_residual = scaler_y.inverse_transform(lstm_residual_norm.reshape(-1,1)).ravel()

# Hybrid prediction
y_val_actual = y_val
ntu_physical_val = ntu_physical[seq_len+horizon:][split:split+len(y_val)]
ntu_hybrid = ntu_physical_val + lstm_residual

# LSTM-only (without physical model) - predict NTU directly
lstm_only_model = BiLSTMAttention(input_dim=feat_data.shape[1]).to(device)
_, y_seq_raw = create_sequences(feat_data, finished_ntu, seq_len, horizon)
y_train_raw = y_seq_raw[:split]
y_val_raw = y_seq_raw[split:]
s_y2 = StandardScaler()
y_train_rn = s_y2.fit_transform(y_train_raw.reshape(-1,1)).ravel()
y_val_rn = s_y2.transform(y_val_raw.reshape(-1,1)).ravel()

print(f"LSTM-only: y_train_rn shape={y_train_rn.shape}, X_train shape={X_train_t.shape}")

opt2 = torch.optim.Adam(lstm_only_model.parameters(), lr=0.001)
for epoch in range(50):
    lstm_only_model.train()
    opt2.zero_grad()
    p = lstm_only_model(X_train_t)
    if epoch == 0:
        print(f"  Model output shape: {p.shape}")
    l = criterion(p, torch.FloatTensor(y_train_rn).to(device))
    l.backward()
    opt2.step()

lstm_only_model.eval()
with torch.no_grad():
    lstm_only_pred_norm = lstm_only_model(X_val_t).cpu().numpy()
lstm_only_pred = s_y2.inverse_transform(lstm_only_pred_norm.reshape(-1,1)).ravel()

# ===================== 4. Ablation Study =====================
print("\n--- Ablation Study ---")
min_len = min(len(y_val_actual), len(ntu_hybrid), len(lstm_only_pred), len(ntu_physical_val))
models_compare = {
    'Pure RTD': ntu_physical_val[:min_len],
    'Pure LSTM': lstm_only_pred[:min_len],
    'Hybrid (RTD+LSTM)': ntu_hybrid[:min_len]
}
y_actual = y_val_actual[:min_len]

ablation_results = []
for name, pred in models_compare.items():
    rmse = np.sqrt(mean_squared_error(y_actual, pred))
    mae = mean_absolute_error(y_actual, pred)
    r2 = r2_score(y_actual, pred)
    mape = np.mean(np.abs((y_actual - pred) / (y_actual + 1e-6))) * 100
    ablation_results.append({'Model': name, 'RMSE': rmse, 'MAE': mae, 'R2': r2, 'MAPE%': mape})
    print(f"  {name}: RMSE={rmse:.4f}, R2={r2:.4f}")

df_ablation = pd.DataFrame(ablation_results)
df_ablation.to_csv(os.path.join(OUT_DIR, 'problem3_ablation.csv'), index=False)

# ===================== 5. Visualizations =====================
# === 图1: 消融实验对比 ===
fig, ax = plt.subplots(figsize=(12, 6))
plot_len = min(200, min_len)
t_axis = np.arange(plot_len)
ax.plot(t_axis, y_actual[:plot_len], 'b-', linewidth=1.5, alpha=0.8, label='Actual NTU')
colors_ab = {'Pure RTD': 'gray', 'Pure LSTM': 'orange', 'Hybrid (RTD+LSTM)': 'red'}
for name, pred in models_compare.items():
    ax.plot(t_axis, pred[:plot_len], linestyle='--', linewidth=1.5,
            color=colors_ab[name], alpha=0.8, label=f'{name} (R2={r2_score(y_actual[:plot_len], pred[:plot_len]):.3f})')
ax.set_title('Ablation Study: Model Comparison', fontsize=14, fontweight='bold')
ax.set_xlabel('Time Step')
ax.set_ylabel('NTU')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_ablation.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_ablation.png'), bbox_inches='tight')
plt.close()
print("  Ablation figure saved")

# === 图2: 训练收敛曲线 ===
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(train_losses, 'b-', label='Train Loss', linewidth=1.5)
ax.plot(val_losses, 'r-', label='Val Loss', linewidth=1.5)
ax.set_title('LSTM Training Convergence', fontsize=14, fontweight='bold')
ax.set_xlabel('Epoch'); ax.set_ylabel('MSE Loss')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_training_loss.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_training_loss.png'), bbox_inches='tight')
plt.close()
print("  Training loss figure saved")

# === 图3: 预测对比 (选取代表性时段) ===
plot_start, plot_len_surge = 100, min(100, min_len-100)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
t_s = np.arange(plot_len_surge)
offset = seq_len + horizon

# Raw water turbidity
ax1.plot(t_s, rw_ntu[offset+plot_start:offset+plot_start+plot_len_surge], 'b-', linewidth=1.5)
ax1.set_ylabel('R/W NTU', fontsize=12); ax1.grid(True, alpha=0.3)

# Predictions
ax2.plot(t_s, y_actual[plot_start:plot_start+plot_len_surge], 'k-', linewidth=2, label='Actual NTU', alpha=0.8)
for name, pred, color, lstyle in [('Hybrid', ntu_hybrid, 'red', '--'),
                                 ('LSTM-only', lstm_only_pred, 'orange', ':'),
                                 ('RTD-only', ntu_physical_val, 'gray', '-.')]:
    ax2.plot(t_s, pred[plot_start:plot_start+plot_len_surge], color=color,
             linestyle=lstyle, linewidth=1.5, label=name)
ax2.set_title('Multi-model Comparison: Finished Water NTU Forecast', fontsize=12, fontweight='bold')
ax2.set_xlabel('Time Step'); ax2.set_ylabel('NTU')
ax2.legend(); ax2.grid(True, alpha=0.3)
plt.suptitle('Finished Water NTU Prediction - Model Comparison', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_surge_scenario.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_surge_scenario.png'), bbox_inches='tight')
plt.close()
print("  Prediction comparison figure saved")

# === 图4: Control Variable Sensitivity ===
print("\n--- Sensitivity Analysis ---")
sensitivity_vars = ['R/W NTU', 'ALUM']
perturbations = [-0.2, -0.1, 0, 0.1, 0.2]
sens_results = {}

# Use validation set features
feat_test = X_val_norm[-100:].copy()

for var_idx, var_name in enumerate(sensitivity_vars):
    sens_vals = []
    for delta in perturbations:
        feat_perturbed = feat_test.copy()
        feat_perturbed[:, :, var_idx] *= (1 + delta)
        with torch.no_grad():
            pred_perturbed_norm = model(torch.FloatTensor(feat_perturbed).to(device)).cpu().numpy()
        pred_perturbed = scaler_y.inverse_transform(pred_perturbed_norm.reshape(-1,1)).ravel()
        sens_vals.append(np.mean(pred_perturbed))
    sens_results[var_name] = sens_vals

fig, ax = plt.subplots(figsize=(8, 5))
for var_name in sensitivity_vars:
    base = sens_results[var_name][2]  # delta=0
    changes = [(sens_results[var_name][i] - base) / base * 100 for i in range(len(perturbations))]
    ax.plot([p*100 for p in perturbations], changes, 'o-', linewidth=2, markersize=8, label=var_name)
ax.axhline(y=0, color='gray', linestyle='--')
ax.axvline(x=0, color='gray', linestyle='--')
ax.set_title('Parameter Sensitivity: NTU Response', fontsize=14, fontweight='bold')
ax.set_xlabel('Input Perturbation (%)')
ax.set_ylabel('NTU Change (%)')
ax.legend(); ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_sensitivity.pdf'), bbox_inches='tight')
plt.savefig(os.path.join(FIG_DIR, 'fig_p3_sensitivity.png'), bbox_inches='tight')
plt.close()
print("  Sensitivity figure saved")
for var_name in sensitivity_vars:
    S = (sens_results[var_name][-1] - sens_results[var_name][0]) / (0.4 * sens_results[var_name][2])
    print(f"  {var_name}: sensitivity coefficient S = {S:.4f}")

print("\n=== Problem 3 Complete ===")
