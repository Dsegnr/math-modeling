# ACM2600174 附件（支撑材料）说明

> 2026“华数杯”A 题《微构体中填充导电介质的仿真优化》
> 本附件用于支撑论文中的模型、结果与结论；所有文件不含参赛者身份与学校信息。

## 目录结构

```
ACM2600174附件\
├── code\              全部源程序（22 个 .py，含问题一~四、第九章、绘图与文档构建脚本）
├── figures\           全部成品图（32 张，1+4+X 分目录）
├── tables\            全部结果表（output/tables，24 个 CSV）
├── data\
│   └── processed\      实验原始记录（q2_mc_raw.csv 33000 行、q3_bisect_trace.csv）
├── 结果汇总.md         高精度正式结果汇总
├── requirements.txt    Python 依赖清单
└── README.md          本说明
```

## 运行环境

- Python 3.12（Windows）；建议安装 requirements.txt 中的依赖。
- 核心依赖：numpy、pandas、scipy、matplotlib、openpyxl。
- 运行前请将 `code\` 目录加入 Python 路径（脚本内部已自动处理）。

## 复现命令（在项目根目录执行）

```powershell
# 问题一（确定性判定）
python code/q1_connectivity.py

# 问题二（高精度，M=3000，相变区加密；含断点续跑）
python code/q2_high.py --m 3000 --workers 8

# 问题三（拟合反解⊕概率二分，细化+3 种子终验）
python code/q3_high_verify.py --workers 8 --resume

# 问题四（纯B延伸+混合细化+候选终验）
python code/q4_high_refine.py --workers 8

# 第九章敏感性（4 图 4 表）与补充检验（3 图 5 表）
python code/ch9_sensitivity.py --workers 8
python code/ch9_analysis.py

# 数据驱动补图与概念图
python code/data_figures.py
python code/concept_figures.py
```

说明：正式结果已全部落盘在 `tables\` 与 `data\processed\`；重新运行可复现（固定随机流、逐样本记录）。

## 数据与口径说明

- 口径：C1（介质完全位于微构体内部，越界构型不合法、拒绝重采）；卷回口径（A1/B1）对照见第九章。
- 阈值：A-A 61.8、A-B 231.8、B-B 401.8、A-面 31.8、B-面 201.8 nm（表面间距 1.8 nm）。
- 成本单位：元（微构体体积 1000 μm³ × 元/μm³）；正式结论：φ*=1.36%，最优纯 A 成本 14.27 元。
- 所有结果表与论文正文数字一致；AI 工具使用详情见论文附录。
