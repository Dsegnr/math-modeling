# -*- coding: utf-8 -*-
"""
概念/机理图（纯几何示意，无蒙特卡洛）：
  concept_geometry.png    微构体几何模型与接触阈值判定
  concept_bottleneck.png  球体“面接触瓶颈”机理示意
运行：python code/concept_figures.py
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "图片", "3_正文结果图")


def fig_geometry():
    C.setup_font()
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(15, 6.2))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax2 = fig.add_subplot(1, 2, 2)
    ax2.axis("off")

    # ===== 左侧：matplotlib 三维画布 =====
    s = 5000.0
    ax.set_xlim(-s, s)
    ax.set_ylim(-s, s)
    ax.set_zlim(-s, s)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    # 立方体线框
    corners = np.array([[x, y, z] for x in (-s, s) for y in (-s, s)
                        for z in (-s, s)])
    idx = [(0, 1), (0, 2), (1, 3), (2, 3),
           (4, 5), (4, 6), (5, 7), (6, 7),
           (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in idx:
        ax.plot3D(*zip(corners[a], corners[b]), color="#9AA9BF", lw=1.2)
    # 左右带电面（半透明四边形）
    left = [(-s, -s, -s), (-s, s, -s), (-s, s, s), (-s, -s, s)]
    right = [(s, -s, -s), (s, -s, s), (s, s, s), (s, s, -s)]
    ax.add_collection3d(Poly3DCollection([left], facecolors="#D62728",
                                         alpha=0.22, edgecolors="none"))
    ax.add_collection3d(Poly3DCollection([right], facecolors="#1F77B4",
                                         alpha=0.22, edgecolors="none"))
    # 介质 A 圆柱段（管状）
    rng = np.random.default_rng(7)
    segs = C.sample_rods_c1(8, rng)
    P1, P2 = segs[:, 0], segs[:, 1]
    C.add_cylinder_tubes(ax, P1, P2, ["#B9C0CC"] * len(P1),
                         radius=70.0, alpha=0.70, n=12)
    # 跨接路径（绿色管状，左面→右面）
    path = np.array([(-s, 0, 0), (-1200, 600, -200), (1200, -500, 300),
                     (s, 0, 0)])
    C.add_cylinder_tubes(ax, path[:-1], path[1:], ["#00B050"] * 3,
                         radius=100.0, alpha=0.95, n=12)
    # 介质 B 球（三维球面，放大示意）
    cx, cy, cz, r = 1500.0, -2800.0, 1800.0, 550.0
    u = np.linspace(0, 2 * np.pi, 28)
    v = np.linspace(0, np.pi, 18)
    xs = cx + r * np.outer(np.cos(u), np.sin(v))
    ys = cy + r * np.outer(np.sin(u), np.sin(v))
    zs = cz + r * np.outer(np.ones_like(u), np.cos(v))
    ax.plot_surface(xs, ys, zs, color="#ED7D31", alpha=0.95, shade=True,
                    linewidth=0, edgecolor="none", rstride=1, cstride=1)
    # 标签
    ax.text3D(-s, 0, s * 1.12, "左带电面", color="#C00000", fontsize=10,
              ha="center")
    ax.text3D(s, 0, s * 1.12, "右带电面", color="#1F77B4", fontsize=10,
              ha="center")
    ax.text3D(0, 0, s * 1.35, "微构体 10 μm 立方体（三维示意，比例已放大）",
              color="#1F2A44", fontsize=11, ha="center", fontweight="bold")
    ax.view_init(elev=18, azim=-58)
    fig.text(0.265, 0.045,
             "红面=左带电面 · 蓝面=右带电面 · 灰管=介质A · 绿管=跨接路径 · 橙球=介质B（示意放大）",
             ha="center", fontsize=9.5, color="#4B5563")

    # 右侧：阈值判定示意
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.text(5, 9.35, "接触判定：把几何变成可算模型",
             ha="center", fontsize=13, fontweight="bold", color="#1F2A44")
    rows = [
        ("A-A 接触", "轴线距离 ≤ 61.8 nm", 8.0, 7.2, "#2E5FA3",
         "rods"),
        ("A-B 接触", "轴线-球心距离 ≤ 231.8 nm", 5.4, 4.6, "#7030A0",
         "rod_sphere"),
        ("A-面 接触", "轴线-带电面距离 ≤ 31.8 nm", 2.8, 2.0, "#C00000",
         "rod_face"),
    ]
    for (name, rule, y1, y2, col, kind) in rows:
        ax2.text(0.3, y1, name, fontsize=11.5, fontweight="bold", color=col)
        ax2.text(0.3, y1 - 0.45, rule, fontsize=9.5, color="#4B5563")
        # 右侧小示意图
        x0, x1 = 4.2, 9.6
        ym = y2
        if kind == "rods":
            ax2.plot([x0, x0 + 1.1], [ym + 0.25, ym + 0.25], color="#2E5FA3",
                     lw=4)
            ax2.plot([x1 - 1.1, x1], [ym - 0.25, ym - 0.25], color="#2E5FA3",
                     lw=4)
            ax2.annotate("", xy=(x1 - 1.2, ym), xytext=(x0 + 1.2, ym),
                         arrowprops=dict(arrowstyle="<->", color=col, lw=1.2))
            ax2.text((x0 + x1) / 2, ym + 0.30, "61.8", ha="center",
                     fontsize=9, color=col)
        elif kind == "rod_sphere":
            ax2.plot([x0, x0 + 1.3], [ym, ym], color="#2E5FA3", lw=4)
            cx = x1 - 0.7
            ax2.add_patch(Circle((cx, ym), 0.42, fc="#ED7D31",
                                 ec="#B45309", lw=1.0))
            ax2.add_patch(Circle((cx, ym), 0.05, fc="black"))
            ax2.annotate("", xy=(cx, ym), xytext=(x0 + 1.4, ym),
                         arrowprops=dict(arrowstyle="<->", color=col, lw=1.2))
            ax2.text((x0 + x1) / 2, ym + 0.30, "231.8", ha="center",
                     fontsize=9, color=col)
        else:
            ax2.plot([x0, x0 + 1.3], [ym, ym], color="#2E5FA3", lw=4)
            fx = x1 - 0.4
            ax2.plot([fx, fx], [ym - 0.55, ym + 0.55], color="#C00000", lw=2.5)
            ax2.text(fx + 0.12, ym + 0.55, "带电面", fontsize=8,
                     color="#C00000", ha="left", va="bottom")
            ax2.annotate("", xy=(fx - 0.12, ym), xytext=(x0 + 1.4, ym),
                         arrowprops=dict(arrowstyle="<->", color=col, lw=1.2))
            ax2.text((x0 + x1) / 2, ym + 0.30, "31.8", ha="center",
                     fontsize=9, color=col)
    ax2.text(5, 0.45, "阈值来自题目：R_A=30 nm、R_B=200 nm、表面间距 1.8 nm",
             ha="center", fontsize=9.5, color="#667085")
    fig.tight_layout()
    C.save_fig(fig, os.path.join(FIG, "concept_geometry.png"))


def fig_bottleneck():
    C.setup_font()
    fig, axes = plt.subplots(1, 2, figsize=(14, 6),
                             gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axes[0]
    ax.axis("off")
    ax.set_xlim(-24, 24)
    ax.set_ylim(-12, 13)
    ax.set_aspect("equal")
    # 盒体 x-z 截面
    ax.plot([-20, 20], [-8, -8], color="#9AA9BF", lw=1.2)
    ax.plot([-20, 20], [8, 8], color="#9AA9BF", lw=1.2)
    ax.plot([-20, -20], [-8, 8], color="#D62728", lw=3.5)
    ax.plot([20, 20], [-8, 8], color="#1F77B4", lw=3.5)
    ax.text(-20, 9.2, "左带电面", color="#C00000", fontsize=10,
            fontweight="bold", ha="center")
    ax.text(20, 9.2, "右带电面", color="#1F77B4", fontsize=10,
            fontweight="bold", ha="center")
    # 有效贴面层（夸张）
    ax.add_patch(Rectangle((-20, -8), 1.3, 16, fc="#D62728", alpha=0.18,
                           ec="none"))
    ax.add_patch(Rectangle((18.7, -8), 1.3, 16, fc="#1F77B4", alpha=0.18,
                           ec="none"))
    ax.text(-22.9, 6.0, "有效层\n≈1.8 nm\n（夸张）", ha="center", fontsize=8,
            color="#C00000", va="top")
    ax.text(22.9, 6.0, "有效层\n≈1.8 nm\n（夸张）", ha="center", fontsize=8,
            color="#1F77B4", va="top")
    # B 球（放大示意）
    ax.add_patch(Circle((0, 0), 3.2, fc="#ED7D31", ec="#B45309", lw=1.4,
                        alpha=0.92))
    ax.add_patch(Circle((0, 0), 0.12, fc="black"))
    ax.text(0, -10.2, "B 球（半径 200 nm，示意放大）", ha="center",
            fontsize=9.5, color="#B45309")
    ax.annotate("", xy=(-16.0, 0), xytext=(-3.6, 0),
                arrowprops=dict(arrowstyle="->", color="#C00000", lw=1.4))
    ax.annotate("", xy=(16.0, 0), xytext=(3.6, 0),
                arrowprops=dict(arrowstyle="->", color="#1F77B4", lw=1.4))
    ax.text(-10, 3.1, "球心距面 ≈4800 nm\n需 ≤201.8 nm 才算贴面",
            ha="center", fontsize=8.5, color="#C00000")
    ax.text(10, 3.1, "球心距面 ≈4800 nm\n需 ≤201.8 nm 才算贴面",
            ha="center", fontsize=8.5, color="#1F77B4")
    ax.text(-22, 12.2, "球体“面接触瓶颈”示意（x-z 截面）",
            fontsize=12.5, fontweight="bold", color="#1F2A44")
    # 右：A 圆柱对比
    ax2 = axes[1]
    ax2.axis("off")
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.text(5, 9.3, "对比：A 圆柱的优势", ha="center", fontsize=12.5,
             fontweight="bold", color="#1F2A44")
    ax2.add_patch(Rectangle((0.7, 6.7), 4.6, 0.8, fc="#1F7A3D", alpha=0.9,
                            ec="none"))
    ax2.add_patch(Rectangle((5.3, 6.7), 3.6, 0.8, fc="#1F7A3D", alpha=0.30,
                            ec="none"))
    ax2.annotate("", xy=(9.6, 7.1), xytext=(8.9, 7.1),
                 arrowprops=dict(arrowstyle="-|>", color="#1F7A3D", lw=1.4))
    ax2.plot([0.7, 0.7], [6.2, 7.9], color="#D62728", lw=3)
    ax2.plot([9.3, 9.3], [6.2, 7.9], color="#1F77B4", lw=3)
    ax2.text(5, 5.9, "A 圆柱：长 5000 nm，轴线距面 ≤31.8 nm 即接触（R_A=30 nm）；\n"
                     "易贴面且深入体相，多根链式跨接",
            ha="center", fontsize=10, color="#1F2A44")
    ax2.text(5.0, 8.05, "单根贴面 + 链式跨接", ha="center", fontsize=8.5,
             color="#1F7A3D")
    ax2.text(5, 2.9, "注：两面间距 d≈9600 nm（与左图一致）",
            ha="center", fontsize=8.5, color="#667085")
    ax2.add_patch(FancyBboxPatch((1.0, 3.4), 8.0, 1.5,
                                 boxstyle="round,pad=0.02,rounding_size=0.08",
                                 fc="#FDF3E7", ec="#E3C29B", lw=1.0))
    ax2.text(5, 4.55, "结论：球体即使体相已渗流，也难以同时贴紧两面；\n"
                      "纯 B 需 φ≈61% 仍不达标，成本是纯 A 的 2 倍以上",
            ha="center", va="center", fontsize=10.5, color="#B45309")
    ax2.text(5, 1.8, "→ 混合填充退化为纯 A：φ*=1.359%，成本 14.27 元",
            ha="center", fontsize=11, fontweight="bold", color="#1F7A3D")
    fig.tight_layout()
    C.save_fig(fig, os.path.join(FIG, "concept_bottleneck.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_geometry()
    fig_bottleneck()
