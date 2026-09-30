# -*- coding: utf-8 -*-
"""All 5 flowcharts — award-winning paper style."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm
import os, glob

# Font
for d in [os.path.expanduser('~/.matplotlib')]:
    for f in glob.glob(os.path.join(d, 'fontlist*')):
        try: os.remove(f)
        except: pass
fm.fontManager.addfont(r'C:\Windows\Fonts\simhei.ttf')
fm._load_fontmanager(try_read_cache=False)
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

FIG = r'D:\数模竞赛\newfigures'
os.makedirs(FIG, exist_ok=True)

COLORS = {
    'blue':   ['#E3F2FD','#BBDEFB','#90CAF9','#64B5F6','#42A5F5','#2196F3'],
    'green':  ['#E8F5E9','#C8E6C9','#A5D6A7','#81C784','#66BB6A','#4CAF50'],
    'orange': ['#FFF3E0','#FFE0B2','#FFCC80','#FFB74D','#FFA726','#FB8C00'],
    'pink':   ['#FCE4EC','#F8BBD0','#F48FB1','#F06292','#EC407A','#D81B60'],
    'purple': ['#F3E5F5','#E1BEE7','#CE93D8','#BA68C8','#AB47BC','#8E24AA'],
    'grey':   ['#ECEFF1','#CFD8DC','#B0BEC5','#90A4AE','#78909C','#607D8B'],
}

def B(ax, x, y, w, h, text, color, fs=8):
    rect = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.08",
        facecolor=color, edgecolor='#555', linewidth=1.0, alpha=0.93, zorder=2)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=fs, fontweight='bold', zorder=3)

def A(ax, x1, y1, x2, y2, c='#666'):
    ax.annotate('', xy=(x2, y2+0.02), xytext=(x1, y1-0.02),
        arrowprops=dict(arrowstyle='->', color=c, lw=1.5, connectionstyle='arc3,rad=0'))

def save(fig, name):
    for fmt in ['pdf','png']:
        fig.savefig(os.path.join(FIG, f'{name}.{fmt}'), dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  {name}')

# ===== 图1: 总体思路 =====
fig, ax = plt.subplots(figsize=(18, 9))
ax.set_xlim(0,18); ax.set_ylim(0,9); ax.axis('off')
ax.text(9, 8.6, '图1  总体建模思路流程图', ha='center', fontsize=18, fontweight='bold')

# Top: Data
B(ax, 9, 7.7, 8, 0.7, '自来水厂15个月运行监测数据（附件1+附件2）\n每天12次 × 20+监测指标 × 多变量耦合、非线性、时滞性', COLORS['grey'][0], 9)

# Row 1: Problem boxes
row1_y = 6.3
cols = [2.5, 6.5, 10.5, 14.5]
titles = ['问题一：特征筛选与预测', '问题二：动态时滞建模', '问题三：混合预测模型', '问题四：水质风险评价']
t_colors = [COLORS['blue'][1], COLORS['green'][1], COLORS['orange'][1], COLORS['pink'][1]]
for ci, (cx, ti, tc) in enumerate(zip(cols, titles, t_colors)):
    B(ax, cx, row1_y, 3.2, 0.7, ti, tc, 10)

# Row 2: Key methods
row2_y = 5.2
methods = [
    'Spearman → MI → MDI → SHAP\n四层递进特征筛选',
    'AR(p)预白化 → CCF + 滞后MI\n→ ARIMAX(lagged exog)',
    '质量守恒 → RTD → 卷积\n→ BiLSTM + Attention残差修正',
    '超标幅度 × 持续时长\n梯形隶属度模糊综合评价',
]
m_colors = [COLORS['blue'][2], COLORS['green'][2], COLORS['orange'][2], COLORS['pink'][2]]
for ci, (cx, mt, mc) in enumerate(zip(cols, methods, m_colors)):
    B(ax, cx, row2_y, 3.2, 0.85, mt, mc, 8)

# Row 3: Models
row3_y = 4.0
models = [
    'XGBoost(主力) + RF(验证)\n+ 线性回归(基准函数)',
    'ARIMAX(2,0,1)\n+ 格兰杰因果检验',
    'RTD+LSTM混合\n+ 消融实验 + 控制变量法',
    '熵权法+AHP组合赋权\n+ 一票否决规则',
]
for ci, (cx, mo, mc) in enumerate(zip(cols, models, m_colors)):
    B(ax, cx, row3_y, 3.0, 0.75, mo, mc, 8)

# Row 4: Outputs
row4_y = 2.8
outputs = [
    '12项主要因素 + R2=0.734\n预测：2月1/10/20日(Excel)',
    'τ1~τ4时滞参数\nRMSE + R2 + 残差诊断',
    '1-12h预测(21点Excel)\n敏感度系数排序',
    '安全95.6% + 否决2天\n马尔可夫转移矩阵',
]
for ci, (cx, ot, mc) in enumerate(zip(cols, outputs, m_colors)):
    B(ax, cx, row4_y, 3.0, 0.75, ot, mc, 8)

# Bottom: Validation
B(ax, 9, 1.6, 10, 0.7, '第九章 模型的分析与检验：误差分析 + 参数灵敏度 + 鲁棒性检验 + 模型对比', COLORS['purple'][1], 9)
B(ax, 9, 0.7, 6, 0.55, '第十章 模型的评价、改进与推广', COLORS['grey'][1], 9)

# Arrows: Data → Problems
for cx in cols:
    A(ax, 9, 7.35, cx, 6.65)
# Problems → Methods
for cx in cols:
    A(ax, cx, 5.95, cx, 5.62)
# Methods → Models
for cx in cols:
    A(ax, cx, 4.78, cx, 4.38)
# Models → Outputs
for cx in cols:
    A(ax, cx, 3.62, cx, 3.18)
# Outputs → Validation
for cx in cols:
    A(ax, cx, 2.42, 9, 1.95)
# Validation → Conclusion
A(ax, 9, 1.25, 9, 0.98)

save(fig, 'flowchart_overall')

# ===== 问题1流程图 =====
fig, ax = plt.subplots(figsize=(12, 13))
ax.set_xlim(0,12); ax.set_ylim(0,13); ax.axis('off')
ax.text(6, 12.7, '图  问题一建模流程图', ha='center', fontsize=16, fontweight='bold')

y = 12.0
B(ax, 6, y, 8, 0.6, '原始数据：15个月 × 4380行 × 20+变量', COLORS['grey'][0], 9); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 7, 0.6, '数据预处理：异常值区分 + 因果对齐(输入<=预测时刻-HRT) + 缺失填充 + VIF筛选(剔除>10)', COLORS['blue'][0], 8); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.6, '第一层 Spearman相关系数：初筛，排除|rho|<0.1的无关变量', COLORS['blue'][1], 8); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.6, '第二层 互信息(MI)：捕捉任意非线性/非单调依赖，取Top15', COLORS['blue'][1], 8); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.6, '第三层 RF-MDI：树模型增益角度评估变量贡献，取Top15', COLORS['blue'][2], 8); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.6, '第四层 SHAP值：博弈论边际贡献 + 影响方向，确定12项主要因素', COLORS['blue'][3], 8); y-=1.0

# Three model branches
A(ax, 6, y+0.7, 2.5, y+0.15)
A(ax, 6, y+0.7, 6, y+0.15)
A(ax, 6, y+0.7, 9.5, y+0.15)

B(ax, 2.5, y-0.2, 3.0, 0.55, 'XGBoost（主力）\nn=100, lr=0.1', COLORS['orange'][1], 8)
B(ax, 6, y-0.2, 3.0, 0.55, '随机森林（验证）\nn=100, Bagging', COLORS['orange'][2], 8)
B(ax, 9.5, y-0.2, 3.0, 0.55, '线性回归（基准）\nVIF筛选后, 显式函数', COLORS['orange'][3], 8)
y -= 1.0

A(ax, 2.5, y+0.6, 6, y+0.1); A(ax, 6, y+0.6, 6, y+0.1); A(ax, 9.5, y+0.6, 6, y+0.1)

B(ax, 6, y-0.2, 6, 0.6, 'Walk-Forward滚动验证 (3组时间窗口, 取平均RMSE/R2)', COLORS['green'][1], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.1)

B(ax, 6, y-0.2, 6, 0.6, '交叉验证：线性回归系数方向 ↔ SHAP方向一致性检验', COLORS['green'][2], 8); y-=0.8; A(ax,6,y+0.4,6,y+0.1)

# SHAP branch
A(ax, 6, y+0.5, 2.5, y+0.1); A(ax, 6, y+0.5, 9.5, y+0.1)
B(ax, 2.5, y-0.15, 3.5, 0.55, 'SHAP蜂群图\n全局重要性+方向', COLORS['purple'][1], 8)
B(ax, 9.5, y-0.15, 3.5, 0.55, 'SHAP依赖图\n非线性边际效应', COLORS['purple'][1], 8)
y -= 0.8

A(ax, 2.5, y+0.4, 6, y); A(ax, 9.5, y+0.4, 6, y)

B(ax, 6, y-0.2, 5, 0.55, 'Excel输出: 2月1/10/20日 RF|XGBoost|均值', COLORS['grey'][1], 8)

save(fig, 'flowchart_q1')

# ===== 问题2流程图 =====
fig, ax = plt.subplots(figsize=(12, 13))
ax.set_xlim(0,12); ax.set_ylim(0,13); ax.axis('off')
ax.text(6, 12.7, '图  问题二建模流程图', ha='center', fontsize=16, fontweight='bold')

y = 12.0
B(ax, 6, y, 6, 0.6, 'FILT.NTU序列 + 4个外生变量 (4380点)', COLORS['grey'][0], 9); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 5, 0.6, 'ADF平稳性检验：5序列全部平稳(d=0)', COLORS['green'][0], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

# Prewhitening - two parallel branches
A(ax, 6, y+0.4, 3, y); A(ax, 6, y+0.4, 9, y)
B(ax, 3, y-0.2, 4, 0.55, 'AR(p)预白化\n(AIC定阶, 消除自相关)', COLORS['green'][1], 8)
B(ax, 9, y-0.15, 4, 0.55, '滞后互信息(MI)\n(非线性时滞探测)', COLORS['green'][1], 8)
y -= 0.7

A(ax, 3, y+0.3, 6, y); A(ax, 9, y+0.3, 6, y)
B(ax, 6, y-0.2, 5, 0.6, '综合确定统一时滞 tau1~tau4 + Bootstrap 95%CI', COLORS['green'][2], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y-0.2, 4, 0.6, '工艺先验校验：与题目2~6h区间对比', COLORS['green'][3], 8); y-=0.8; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y-0.2, 5, 0.6, '构造滞后外生变量 → ARIMAX(2,0,1)建模', COLORS['orange'][1], 8); y-=0.8; A(ax,6,y+0.4,6,y+0.2)

# Two verification branches
A(ax, 6, y+0.4, 3, y); A(ax, 6, y+0.4, 9, y)
B(ax, 3, y-0.2, 4, 0.6, '格兰杰因果检验\n(p=0.034)', COLORS['orange'][2], 8)
B(ax, 9, y-0.15, 4, 0.6, '残差诊断\n(白噪声/正态/ACF)', COLORS['orange'][2], 8)
y -= 0.8

A(ax, 3, y+0.4, 6, y); A(ax, 9, y+0.4, 6, y)

B(ax, 6, y-0.2, 5, 0.6, '输出: tau参数 + RMSE/R2 + 如实汇报(R/W PH/ALUM无显著时滞)', COLORS['grey'][1], 8)

save(fig, 'flowchart_q2')

# ===== 问题3流程图 =====
fig, ax = plt.subplots(figsize=(12, 13))
ax.set_xlim(0,12); ax.set_ylim(0,13); ax.axis('off')
ax.text(6, 12.7, '图  问题三建模流程图', ha='center', fontsize=16, fontweight='bold')

y = 12.0
B(ax, 6, y, 6, 0.6, '清水池质量守恒方程: V*dC/dt = Qin*Cin - Qout*Cout', COLORS['blue'][0], 9); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.6, 'n级串联CSTR → RTD: E(t)=(N/tau)^N*t^(N-1)*exp(-Nt/tau)/Gamma(N)', COLORS['blue'][1], 8); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

# Two parallel branches
A(ax, 6, y+0.5, 3, y+0.1); A(ax, 6, y+0.5, 9, y+0.1)
B(ax, 3, y-0.1, 4, 0.6, '物理模型 (Stage1)\n卷积: NTU_physical = FILT * E(t)\n(仅作用于清水池)', COLORS['blue'][2], 7)
B(ax, 9, y-0.1, 4, 0.6, '数据驱动 (Stage2)\nBiLSTM + Attention\n(输入<=t时刻)', COLORS['orange'][2], 7)
y -= 0.8

A(ax, 3, y+0.3, 6, y); A(ax, 9, y+0.3, 6, y)
B(ax, 6, y-0.2, 5, 0.6, '混合模型: NTU(t+h) = NTU_physical + Delta_LSTM', COLORS['green'][1], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y-0.2, 5, 0.6, '直接多步预测: h=1~6 (2h~12h), 6个独立LSTM', COLORS['green'][2], 8); y-=0.8; A(ax,6,y+0.4,6,y+0.2)

# Two verification branches
A(ax, 6, y+0.4, 3, y); A(ax, 6, y+0.4, 9, y)
B(ax, 3, y-0.2, 4, 0.6, '消融实验\n纯RTD vs 纯LSTM vs 混合', COLORS['purple'][1], 8)
B(ax, 9, y-0.15, 4, 0.6, '控制变量扰动法\n敏感度系数 S=dy/dx', COLORS['purple'][1], 8)
y -= 0.8

A(ax, 3, y+0.4, 6, y); A(ax, 9, y+0.4, 6, y)

B(ax, 6, y-0.2, 5, 0.6, '突变场景案例 + 预测输出: 2月1/10/20日 7-19时(21点Excel)', COLORS['grey'][1], 8)

save(fig, 'flowchart_q3')

# ===== 问题4流程图 =====
fig, ax = plt.subplots(figsize=(12, 10))
ax.set_xlim(0,12); ax.set_ylim(0,10); ax.axis('off')
ax.text(6, 9.7, '图  问题四建模流程图', ha='center', fontsize=16, fontweight='bold')

y = 9.0
B(ax, 6, y, 6, 0.6, '2026年1-3月小时级NTU数据 (1080行)', COLORS['grey'][0], 9); y-=0.8; A(ax,6,y+0.5,6,y+0.3)

B(ax, 6, y, 6, 0.55, '小时级：逐小时计算超标幅度 eta_h = max(0, NTU_h-1)/1 × 100%', COLORS['pink'][0], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y, 6, 0.55, '日级聚合：最大超标幅度 + 最长连续超标时长(连续4采样点=8h)', COLORS['pink'][1], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y, 5, 0.55, '一票否决检查（最高优先）: NTU>1.5 或 连续>=8h → 直接高风险', COLORS['pink'][2], 8); y-=0.8; A(ax,6,y+0.4,6,y+0.2)

# Two parallel
A(ax, 6, y+0.4, 3, y+0.1); A(ax, 6, y+0.4, 9, y+0.1)
B(ax, 3, y-0.1, 4, 0.55, '梯形隶属度函数\n(4级模糊评价)', COLORS['pink'][3], 8)
B(ax, 9, y-0.1, 4, 0.55, '熵权法+AHP组合赋权\n(lambda=0.5)', COLORS['pink'][3], 8)
y -= 0.8

A(ax, 3, y+0.3, 6, y); A(ax, 9, y+0.3, 6, y)
B(ax, 6, y-0.2, 5, 0.55, 'min算子合成（保守原则）→ 确定日风险等级', COLORS['pink'][4], 8); y-=0.9; A(ax,6,y+0.4,6,y+0.2)

B(ax, 6, y-0.2, 7, 0.6, '输出: 安全86天(95.6%)+低风险1天+中风险1天+否决2天', COLORS['green'][1], 8); y-=0.7; A(ax,6,y+0.4,6,y+0.2)

# Two outputs
A(ax, 6, y+0.5, 3, y+0.1); A(ax, 6, y+0.5, 9, y+0.1)
B(ax, 3, y-0.1, 4, 0.5, '马尔可夫转移概率矩阵\n(97.7%安全保持率)', COLORS['purple'][2], 7)
B(ax, 9, y-0.1, 4, 0.5, '风险归因分析\n(原水浊度-风险关联)', COLORS['purple'][2], 7)

save(fig, 'flowchart_q4')

print('\nAll 5 flowcharts done!')
