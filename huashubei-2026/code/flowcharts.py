# -*- coding: utf-8 -*-
"""
流程图生成（科研论文高级版）：编号里程碑时间轴风格。
  - 白底、细线、编号圆点、轻量卡片；无粗框、无“方块+粗箭头”的 PPT 感；
  - 总体思路 = 横向里程碑；单问 = 纵向编号时间轴；问题三/四 = 双通道汇流。
输出到 图片/：fig00_overall_flow.png, fig_q1_flow.png ... fig_q4_flow.png
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG1 = os.path.join(BASE, "图片", "1_总思路流程图")
FIG2 = os.path.join(BASE, "图片", "2_各问思路流程图")

ACCENT = "#2E5FA3"
GREEN = "#1F7A3D"
ORANGE = "#B45309"
LINE = "#C3CDDC"
TITLE_C = "#1F2A44"
SUB_C = "#667085"


def canvas(w=12, h=4.0):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(w, h))
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def save(fig, name, folder=FIG2):
    C.save_fig(fig, os.path.join(folder, name))


def card(ax, x, y, w, h, fc="#F7F9FC", ec="#D8DEE9", lw=0.9):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.01,rounding_size=0.06",
                       fc=fc, ec=ec, lw=lw, zorder=2)
    ax.add_patch(p)


def overall_flow():
    fig, ax = canvas(w=13, h=3.3)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 3.3)
    ax.axhspan(0.45, 3.05, color="#F7F9FC", zorder=0)
    steps = [
        ("输入", "附件数据\n题目参数", ORANGE),
        ("问题一", "是否连通", ACCENT),
        ("问题二", "导通概率", ACCENT),
        ("问题三", "阈值反解", ACCENT),
        ("问题四", "成本优化", ACCENT),
        ("交付", "结果输出\n图表 · 论文", GREEN),
    ]
    xs = np.linspace(1.0, 12.0, len(steps))
    y = 1.92
    ax.plot([xs[0], xs[-1] + 0.3], [y, y], color="#9AA9BF", lw=1.4,
            zorder=1)
    ax.annotate("", xy=(xs[-1] + 0.35, y), xytext=(xs[-1] + 0.02, y),
                arrowprops=dict(arrowstyle="-|>", color="#9AA9BF", lw=1.4))
    for i, (tag, txt, col) in enumerate(steps):
        x = xs[i]
        ax.scatter([x], [y], s=175, color=col, edgecolor="white", lw=1.5,
                   zorder=3)
        ax.text(x, y, str(i + 1), ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold", zorder=4)
        ax.text(x, y + 0.42, tag, ha="center", fontsize=11,
                fontweight="bold", color=TITLE_C)
        ax.text(x, y - 0.40, txt, ha="center", fontsize=8.6, color="#4B5563",
                va="top")
    # 统一方法内核：左/右边界与问题一、问题四圆心对齐，一行文字不堆砌
    yb0, yb1 = 0.58, 1.04
    ax.axhspan(yb0, yb1, xmin=xs[1] / 13, xmax=xs[4] / 13,
               color="#E9EEF5", zorder=0)
    ax.plot([xs[1], xs[4]], [yb1, yb1], color="#B9C6D9", lw=0.9, zorder=1)
    ax.text((xs[1] + xs[4]) / 2, (yb0 + yb1) / 2,
            "统一方法内核：几何距离判定 · 图连通判定 · 统计推断",
            ha="center", va="center", fontsize=8.5, color="#334155")
    save(fig, "fig00_overall_flow.png", FIG1)


def vertical(steps, name, result_idx=None, w=9.5, h=5.8):
    fig, ax = canvas(w=w, h=h)
    n = len(steps)
    ytop = n + 0.30
    ax.set_xlim(0, 9.5)
    ax.set_ylim(0.4, ytop)
    ax.plot([1.0, 1.0], [0.72, ytop - 0.08], color=LINE, lw=1.1, zorder=1)
    for i, (t, s) in enumerate(steps):
        y = ytop - 0.5 - i * 0.88
        is_res = result_idx is not None and i == result_idx
        col = GREEN if is_res else ACCENT
        fc = "#E8F6EC" if is_res else "#F7F9FC"
        ec = GREEN if is_res else "#D8DEE9"
        ax.scatter([1.0], [y], s=110, color=col, edgecolor="white", lw=1.3,
                   zorder=3)
        ax.text(1.0, y, str(i + 1), ha="center", va="center", fontsize=9.5,
                color="white", fontweight="bold", zorder=4)
        card(ax, 1.6, y - 0.31, 7.4, 0.62, fc=fc, ec=ec)
        ax.text(1.95, y + 0.10, t, fontsize=10.5, fontweight="bold",
                color=TITLE_C, va="center")
        ax.text(1.95, y - 0.14, s, fontsize=8.5, color=SUB_C, va="center")
    save(fig, name)


def stage_flow(title, stages, name, w=11, h=6.8):
    """阶段泳道式流程图：顶部标题条 + 每层左侧阶段标签框 + 右侧步骤卡；
    行内右向箭头、行间向下箭头；一层一色。"""
    fig, ax = canvas(w=w, h=h)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, h)
    top = h - 0.55
    bar = FancyBboxPatch((0.35, top - 0.40), 10.3, 0.62,
                         boxstyle="round,pad=0.01,rounding_size=0.08",
                         fc=TITLE_C, ec="none", zorder=3)
    ax.add_patch(bar)
    ax.text(5.5, top - 0.09, title, ha="center", va="center", fontsize=13,
            color="white", fontweight="bold", zorder=4)
    n = len(stages)
    row_h = (top - 1.10) / n
    palette = [ACCENT, ORANGE, GREEN, "#7030A0", "#C00000"]
    for i, (stag, cards) in enumerate(stages):
        color = palette[i % len(palette)]
        ytop = top - 1.15 - i * row_h
        ybot = ytop - row_h + 0.22
        lab = FancyBboxPatch((0.5, ybot + 0.08), 1.55, row_h - 0.16,
                             boxstyle="round,pad=0.01,rounding_size=0.07",
                             fc=color, ec="none", zorder=2)
        ax.add_patch(lab)
        ax.text(1.275, (ybot + ytop) / 2, stag, ha="center", va="center",
                fontsize=10.5, color="white", fontweight="bold", zorder=3)
        ncard = len(cards)
        x0, x1 = 2.45, 10.6
        gap = 0.28
        cw = (x1 - x0 - gap * (ncard - 1)) / ncard
        for j, (ct, cs) in enumerate(cards):
            cx = x0 + j * (cw + gap)
            card(ax, cx, ybot + 0.08, cw, row_h - 0.16, fc="#FFFFFF",
                 ec=color, lw=1.1)
            cy = (ybot + ytop) / 2
            if cs:
                ax.text(cx + cw / 2, cy + 0.13, ct, ha="center",
                        va="center", fontsize=9.6, fontweight="bold",
                        color=TITLE_C)
                ax.text(cx + cw / 2, cy - 0.17, cs, ha="center",
                        va="center", fontsize=7.6, color=SUB_C)
            else:
                ax.text(cx + cw / 2, cy, ct, ha="center", va="center",
                        fontsize=9.6, fontweight="bold", color=TITLE_C)
            if j < ncard - 1:
                ax.annotate("", xy=(cx + cw + gap - 0.04, cy),
                            xytext=(cx + cw + 0.04, cy),
                            arrowprops=dict(arrowstyle="-|>", color=color,
                                            lw=1.1, ls=(0, (3, 2)),
                                            alpha=0.75))
        if i < n - 1:
            ym = ybot - 0.04
            ax.annotate("", xy=(5.5, ym - 0.10), xytext=(5.5, ym + 0.12),
                        arrowprops=dict(arrowstyle="-|>", color="#8FA0B8",
                                        lw=1.3))
    save(fig, name)


def q1_flow():
    stage_flow("问题一：微构体连通性判定流程图", [
        ("数据准备", [
            ("附件解析", "三个分表，每行 = 介质 A 有效段"),
            ("数据解读", "截断分段存储；周期镜像段共线"),
        ]),
        ("模型构建", [
            ("几何图模型", "节点 = 段 + 左右带电面"),
            ("阈值设定", "A-A 61.8 nm · A-面 31.8 nm"),
        ]),
        ("连通判定", [
            ("距离计算", "三维线段最近点，批量向量化"),
            ("并查集", "左面与右面是否同根"),
        ]),
        ("结论输出", [
            ("三组结论", "组1 不导通；组2、组3 导通"),
            ("交付物", "接触网络图 · 连通簇统计"),
        ]),
    ], "fig_q1_flow.png")


def q2_flow():
    stage_flow("问题二：导通概率蒙特卡洛流程图", [
        ("数量换算", [
            ("数量换算", "N = φ·V微构体 / V圆柱"),
        ]),
        ("随机生成", [
            ("C1 采样", "位置均匀 · 方向球面均匀"),
            ("完全悬浮", "介质不越出微构体，越界重采"),
        ]),
        ("蒙特卡洛", [
            ("单构型判定", "复用问题一内核：上下贯穿=导通"),
            ("并行统计", "P_hat = 导通数/M，M=3000/点"),
        ]),
        ("统计推断", [
            ("Wilson 区间", "95% 置信区间"),
            ("收敛与种子", "收敛诊断 · 多种子复现"),
        ]),
        ("结论输出", [
            ("p-φ 相变曲线", "0.5%→0.060 · 1.0%→0.730"),
        ]),
    ], "fig_q2_flow.png")


def dual_flow(left, right, merge, name):
    """双通道时间轴：左=方法一，右=方法二，底部汇流。"""
    fig, ax = canvas(w=11, h=6.0)
    n = max(len(left), len(right))
    ytop = n + 0.9
    ax.set_xlim(0, 11)
    ax.set_ylim(0.2, ytop)
    ax.text(2.2, ytop - 0.12, "方法一", fontsize=9.5, color=ORANGE,
            fontweight="bold", ha="center")
    ax.text(8.8, ytop - 0.12, "方法二", fontsize=9.5, color=ACCENT,
            fontweight="bold", ha="center")
    ax.plot([2.2, 2.2], [0.95, ytop - 0.62], color=LINE, lw=1.1, zorder=1)
    ax.plot([8.8, 8.8], [0.95, ytop - 0.62], color=LINE, lw=1.1, zorder=1)
    for i, (t, s) in enumerate(left):
        y = ytop - 0.95 - i * 0.90
        ax.scatter([2.2], [y], s=95, color=ORANGE, edgecolor="white", lw=1.2,
                   zorder=3)
        ax.text(2.2, y, str(i + 1), ha="center", va="center", fontsize=9,
                color="white", fontweight="bold", zorder=4)
        card(ax, 2.75, y - 0.29, 3.4, 0.58, fc="#FDF3E7", ec="#E3C29B")
        ax.text(3.0, y + 0.09, t, fontsize=9.5, fontweight="bold",
                color=TITLE_C, va="center")
        ax.text(3.0, y - 0.13, s, fontsize=7.8, color=SUB_C, va="center")
    for i, (t, s) in enumerate(right):
        y = ytop - 0.95 - i * 0.90
        ax.scatter([8.8], [y], s=95, color=ACCENT, edgecolor="white", lw=1.2,
                   zorder=3)
        ax.text(8.8, y, str(i + 1), ha="center", va="center", fontsize=9,
                color="white", fontweight="bold", zorder=4)
        card(ax, 4.85, y - 0.29, 3.4, 0.58)
        ax.text(5.1, y + 0.09, t, fontsize=9.5, fontweight="bold",
                color=TITLE_C, va="center")
        ax.text(5.1, y - 0.13, s, fontsize=7.8, color=SUB_C, va="center")
    # 汇流（先汇于一点，再单线入框，避免穿框/交叉）
    ax.plot([2.2, 5.5], [0.98, 0.88], color=LINE, lw=1.1)
    ax.plot([8.8, 5.5], [0.98, 0.88], color=LINE, lw=1.1)
    ax.plot([5.5, 5.5], [0.88, 0.80], color=LINE, lw=1.1)
    ax.annotate("", xy=(5.5, 0.77), xytext=(5.5, 0.87),
                arrowprops=dict(arrowstyle="-|>", color=LINE, lw=1.1))
    ax.scatter([5.5], [0.72], s=115, color=GREEN, edgecolor="white", lw=1.3,
               zorder=3)
    ax.text(5.5, 0.72, "4", ha="center", va="center", fontsize=11,
            color="white", fontweight="bold", zorder=4)
    card(ax, 3.3, 0.22, 4.4, 0.50, fc="#E8F6EC", ec=GREEN)
    ax.text(5.5, 0.47, merge, fontsize=9, fontweight="bold",
            color=TITLE_C, ha="center", va="center")
    save(fig, name)


def q3_flow():
    stage_flow("问题三：临界体积分数双方法互证流程图", [
        ("粗扫与拟合", [
            ("粗扫 MC", "0.5%~1.5%，11 个 φ"),
            ("渗透模型拟合", "sigmoid / 幂律，AIC 选优"),
        ]),
        ("双方法互证", [
            ("拟合反解", "由渗透模型反演：1.298%"),
            ("概率二分", "CI 决策规则：1.376%"),
        ]),
        ("细化定稿", [
            ("邻域扫描", "N 层面 M=3000"),
            ("φ*=1.359%", "N=961，CI 下界≥0.90"),
        ]),
        ("终验交付", [
            ("3 种子终验", "合并 M=9000，P=0.911"),
            ("95% CI", "[0.905, 0.917] √ 终验通过"),
        ]),
    ], "fig_q3_flow.png")


def q4_flow():
    stage_flow("问题四：混合填充最低成本优化流程图", [
        ("基线标定", [
            ("纯 A 曲线", "φ*_A=1.359%"),
            ("纯 B 延伸", "φ*_B≈61%，未达标"),
            ("等效体积", "w=φ*_A/φ*_B≈0.022"),
        ]),
        ("理论层", [
            ("等效体积 LP", "φ_eff=φA+w·φB → 极点"),
            ("LP 极点", "退化为纯 A（14.27 元）"),
        ]),
        ("工程层", [
            ("代理曲面+2D 优化", "混合候选 11817 元"),
            ("真实 MC 验证", "P=0.818<0.9 否决 → 必须验证"),
        ]),
        ("最优交付", [
            ("最优方案", "纯 A，成本 14.27 元"),
            ("成本-概率前沿", "全部真实 MC 点"),
        ]),
    ], "fig_q4_flow.png")


if __name__ == "__main__":
    os.makedirs(FIG1, exist_ok=True)
    os.makedirs(FIG2, exist_ok=True)
    # 图1（fig00_overall_flow.png）已由用户提供定稿版，
    # 存放于 图片\1_总思路流程图\，代码不再覆盖；仅重绘四问流程图。
    # 问题一流程图（fig_q1_flow.png）已由用户提供定稿版（GPT 绘制+人工改字），
    # 存放于 图片\2_各问思路流程图\，代码不再覆盖。
    # 问题二流程图（fig_q2_flow.png）已由用户提供定稿版（GPT 绘制），
    # 存放于 图片\2_各问思路流程图\，代码不再覆盖。
    # 问题三流程图（fig_q3_flow.png）已由用户提供定稿版（GPT 绘制），
    # 存放于 图片\2_各问思路流程图\，代码不再覆盖。
    # 问题四流程图（fig_q4_flow.png）已由用户提供定稿版（GPT 绘制），
    # 存放于 图片\2_各问思路流程图\，代码不再覆盖。
    # 5 张流程图均为人工/GPT 定稿版，flowcharts.py 仅保留生成函数备查，不再输出覆盖。
