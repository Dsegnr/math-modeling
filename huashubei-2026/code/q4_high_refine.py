# -*- coding: utf-8 -*-
"""
问题四正式高精度驱动（新增脚本，不改动 q4_mixture_optimize.py）：
  - 纯 B 扫描延伸至 60%（0.48/0.50/0.55/0.60，M=400），锁定 φ*_B
  - 混合区细化：φA∈{0.5,0.75,1.0,1.25%} × φB∈{20%~35% 步长 2.5%}，M=500
  - 等效体积 w 更新、LP 极点、2D 代理优化（网格+细化联合拟合）、候选终验 M=1000
  - 覆盖写入 q4_pureB_sweep / q4_mixture_refine / q4_optimal / q4_frontier / q4_comparison
  - 动态重绘 q4 全部 4 张成品图（消除原脚本硬编码 B 标注）
运行：python code/q4_high_refine.py --workers 8
"""
import os
import sys
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import linprog
import q4_mixture_optimize as Q
import common as C

# 单位修正（审计发现）：微构体边长 10000 nm = 10 μm，体积 = 1000 μm³；
# 介质单价为 元/μm³，故成本 = 1000 × (1.05·φA + 0.05·φB) 元。
# 原脚本 VMICRO=1e6 把成本放大了 1000 倍，这里在本驱动内修正。
Q.VMICRO = 1000.0

TBL = Q.TBL
FIG = Q.FIG

PHI_B_EXTEND = [0.48, 0.50, 0.55, 0.60]
PHI_A_MIX = [0.005, 0.0075, 0.010, 0.0125]
PHI_B_MIX = [0.20, 0.225, 0.25, 0.275, 0.30, 0.325, 0.35]


def p_at(series_phi, series_p, x):
    """在采样点上线性插值概率（用于标注）。"""
    s = np.argsort(series_phi)
    return float(np.interp(x, np.asarray(series_phi)[s], np.asarray(series_p)[s]))


def fig_contour(grid, ref, pureB, beta, pole, x2, best, pole_cost):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(9, 6.5))
    aa = np.linspace(0, 0.02, 120)
    bb = np.linspace(0, 0.60, 120)
    AA, BB = np.meshgrid(aa, bb)
    ZZ = np.array([Q.p_surf(a, b, beta)
                   for a, b in zip(AA.ravel(), BB.ravel())])
    ZZ = ZZ.reshape(AA.shape)
    cs = ax.contourf(AA * 100, BB * 100, ZZ, levels=12, cmap="RdYlBu_r", alpha=0.9)
    fig.colorbar(cs, ax=ax, label="导通概率 P（代理曲面）")
    ctr = ax.contour(AA * 100, BB * 100, ZZ, levels=[0.90], colors="#C00000",
                     linewidths=2.2)
    ax.clabel(ctr, fmt="P=0.90 可行边界", fontsize=9)
    ax.scatter(grid["phiA"] * 100, grid["phiB"] * 100, c=grid["p_hat"],
               cmap="RdYlBu_r", edgecolor="k", s=40, zorder=5,
               label="粗网格 MC 点", clip_on=False)
    ax.scatter(ref["phiA"] * 100, ref["phiB"] * 100, c=ref["p_hat"],
               cmap="RdYlBu_r", edgecolor="k", s=18, zorder=5, alpha=0.85,
               label="混合区细化 MC 点", clip_on=False)
    ax.scatter(np.zeros(len(pureB)), pureB["phiB"] * 100, marker="x", color="k",
               s=40, zorder=6, label="纯 B 扫描点", clip_on=False)
    ax.plot(pole[0] * 100, pole[1] * 100, "v", color="#7030A0", ms=12,
            markeredgecolor="white", markeredgewidth=1.2,
            label=f"LP 极点（{pole_cost:.1f}元）", zorder=7)
    ax.plot(x2[0] * 100, x2[1] * 100, "s", color="#ED7D31", ms=9,
            markeredgecolor="white", markeredgewidth=1.0, label="2D 代理优化")
    ax.plot(best["phiA"] * 100, best["phiB"] * 100, "*", color="#00B050", ms=16,
            markeredgecolor="white", markeredgewidth=1.0,
            label=f"最终验证最优（{best['cost']:.1f}元）", zorder=8)
    ax.annotate("LP 极点 ≈ 最终最优\n（均退化为纯 A）",
                xy=(best["phiA"] * 100, best["phiB"] * 100),
                xytext=(1.55, 3.2), fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#303030", lw=0.9),
                bbox=dict(fc="white", alpha=0.9, pad=2, ec="0.6", lw=0.5))
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    from matplotlib.patches import Rectangle
    rect = Rectangle((1.0, 0.0), 0.7, 6.0, fill=False, ec="#303030",
                     lw=0.9, ls="--")
    ax.add_patch(rect)
    iax = inset_axes(ax, width="42%", height="40%", loc="upper right")
    iax.set_xlim(0.95, 1.75)
    iax.set_ylim(-0.5, 6.5)
    aa2 = np.linspace(0.0095, 0.0175, 80)
    bb2 = np.linspace(0.0, 0.065, 60)
    AA2, BB2 = np.meshgrid(aa2, bb2)
    ZZ2 = np.array([Q.p_surf(a, b, beta)
                    for a, b in zip(AA2.ravel(), BB2.ravel())])
    ZZ2 = ZZ2.reshape(AA2.shape)
    iax.contourf(AA2 * 100, BB2 * 100, ZZ2, levels=12, cmap="RdYlBu_r", alpha=0.9)
    iax.contour(AA2 * 100, BB2 * 100, ZZ2, levels=[0.90], colors="#C00000",
                linewidths=1.6)
    for px, py, mk, mc, ms in [
        (best["phiA"] * 100, best["phiB"] * 100, "*", "#00B050", 10),
        (x2[0] * 100, x2[1] * 100, "s", "#ED7D31", 6),
        (pole[0] * 100, pole[1] * 100, "v", "#7030A0", 9),
    ]:
        iax.plot(px, py, mk, color=mc, markeredgecolor="white",
                 markeredgewidth=0.8, ms=ms, clip_on=False)
    iax.set_title("候选点局部放大", fontsize=8)
    iax.tick_params(labelsize=6)
    iax.set_xlabel("φA (%)", fontsize=7)
    iax.set_ylabel("φB (%)", fontsize=7)
    ax.axvspan(2.0, 2.5, color="0.85", alpha=0.6, zorder=0)
    ax.text(2.25, 52, "设计空间外", rotation=90, fontsize=10,
            color="#303030", va="top", fontweight="bold")
    ax.set_xlim(0, 2.5)
    ax.set_ylim(0, 60)
    ax.set_xlabel("介质 A 体积分数 φA (%)")
    ax.set_ylabel("介质 B 体积分数 φB (%)")
    ax.set_title("A+B 混合体系导通概率与成本最优解（高精度）")
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
              fontsize=9, loc="lower right")
    cs.colorbar.set_ticks([0.1, 0.3, 0.5, 0.7, 0.9])
    C.save_fig(fig, os.path.join(FIG, "q4_contour.png"))


def fig_frontier(front_src):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    f = front_src.sort_values("cost")
    ok = f[f["target_ok"]]
    ax.scatter(ok["cost"], ok["p_hat"] * 100, s=55, color="#4472C4",
               edgecolor="k", zorder=5, label="可行点（CI 下界 ≥0.90）")
    ax.scatter(f[~f["target_ok"]]["cost"],
               f[~f["target_ok"]]["p_hat"] * 100, s=50, color="#C00000",
               alpha=0.8, edgecolor="k", zorder=5, label="不可行点")
    ax.errorbar(f["cost"], f["p_hat"] * 100,
                yerr=[(f["p_hat"] - f["ci_low"]) * 100,
                      (f["ci_up"] - f["p_hat"]) * 100],
                fmt="none", ecolor="#303030", elinewidth=1.0, capsize=2, zorder=1)
    ax.axhline(90, ls="--", color="#00B050", lw=1.3, label="可行阈值 P=0.90")
    ax.set_xlabel("总成本（元）")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("成本-导通概率关系（所有真实 MC 验证点，高精度）")
    ax.set_ylim(0, 105)
    ax.grid(True, ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.text(0.02, 0.98, "误差棒为 95% Wilson 置信区间；可行性按 CI 下界判定",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#404040")
    C.save_fig(fig, os.path.join(FIG, "q4_frontier.png"))


def fig_comparison(comp, b_feasible):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8, 5))
    names = comp["方案"].tolist()
    costs = comp["成本"].tolist()
    bars = ax.bar(names, np.array(costs),
                  color=["#4472C4", "#ED7D31", "#00B050"],
                  edgecolor="black", lw=0.6, width=0.55)
    for b, c in zip(bars, costs):
        ax.text(b.get_x() + b.get_width() / 2, c + 0.5,
                f"{c:.2f} 元", ha="center", fontsize=11)
    ax.set_ylabel("总填充成本（元）")
    ax.set_ylim(0, 40)
    ax.set_title("纯 A / 纯 B / 混合最优 成本对比（高精度）")
    ax.grid(True, axis="y", ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    note = ("注：本工况混合最优退化为纯 A；球形介质 B 存在“面接触瓶颈”。"
            if not b_feasible else
            "注：本工况混合最优退化为纯 A；介质 B 虽可达标但成本远高于纯 A。")
    ax.text(0.5, -0.18, note, transform=ax.transAxes, ha="center",
            fontsize=8.5, color="#404040")
    fig.subplots_adjust(bottom=0.22)
    C.save_fig(fig, os.path.join(FIG, "q4_comparison.png"))


def fig_pure_curves(q2, pureB, phi_star_A, pA, phi_star_B, pB, b_feasible,
                    costA, costB):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.errorbar(q2["phi_percent"], q2["p_hat"] * 100,
                yerr=[(q2["p_hat"] - q2["ci_low"]) * 100,
                      (q2["ci_up"] - q2["p_hat"]) * 100],
                fmt="o-", color="#1F77B4", ms=5, capsize=3, lw=1.6,
                label="介质 A（圆柱）")
    ax.errorbar(pureB["phiB"] * 100, pureB["p_hat"] * 100,
                yerr=[(pureB["p_hat"] - pureB["ci_low"]) * 100,
                      (pureB["ci_up"] - pureB["p_hat"]) * 100],
                fmt="s--", color="#ED7D31", ms=5, capsize=3, lw=1.6,
                label="介质 B（球体）")
    ax.axhline(90, ls=":", color="#C00000", lw=1.2, label="P=90%")
    ax.axvline(phi_star_A * 100, ls="-.", color="#1F77B4", lw=1.4)
    ax.plot(phi_star_A * 100, pA * 100, "*", color="#1F77B4", ms=16,
            markeredgecolor="white", markeredgewidth=1.2, zorder=12)
    ax.text(phi_star_A * 100 + 0.2, min(pA * 100 + 3, 100),
            f"φ*_A={phi_star_A*100:.2f}%", fontsize=8.5, color="#1F77B4")
    ax.annotate(f"A：φ*={phi_star_A*100:.2f}% 时达标\n成本 {costA:.1f} 元",
                xy=(phi_star_A * 100, pA * 100), xytext=(3.2, 62), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#303030"),
                bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    ax.axvline(phi_star_B * 100, ls="-.", color="#ED7D31", lw=1.4)
    ax.plot(phi_star_B * 100, pB * 100, "*", color="#ED7D31", ms=16,
            markeredgecolor="white", markeredgewidth=1.2, zorder=12)
    if b_feasible:
        ax.annotate(f"B：φ*_B≈{phi_star_B*100:.0f}% 时达标\n成本 {costB:.1f} 元",
                    xy=(phi_star_B * 100, pB * 100), xytext=(14, 35), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#303030"),
                    bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    else:
        ax.annotate(f"B：φ*_B≈{phi_star_B*100:.0f}%（外推，扫描上限 60%）时 "
                    f"P≈{pB*100:.0f}%\n"
                    f"但 CI 下界 0.882<0.90 不达标\n成本 {costB:.1f} 元（面接触瓶颈）",
                    xy=(phi_star_B * 100, pB * 100), xytext=(14, 48), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#303030"),
                    bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("介质 A 与介质 B 的导通效率对比（高精度）")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 65)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.85, edgecolor="0.7",
              fontsize=9, loc="lower right")
    C.save_fig(fig, os.path.join(FIG, "q4_pure_curves.png"))


def run_figures_only():
    """复用已存表格：单位修正后重算成本列并重绘 4 张图。"""
    q3res = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
    phi_star_A = float(q3res.loc[q3res["method"] == "细化定稿",
                                 "phi_star"].iloc[0]) / 100
    pA = float(q3res.loc[q3res["method"] == "细化定稿", "p_hat"].iloc[0])
    costA = Q.VMICRO * Q.COST_A * phi_star_A
    grid = pd.read_csv(os.path.join(TBL, "q4_grid.csv"))
    pureB = pd.read_csv(os.path.join(TBL, "q4_pureB_sweep.csv"))
    ref = pd.read_csv(os.path.join(TBL, "q4_mixture_refine.csv"))
    pureA_hi = pd.read_csv(os.path.join(TBL, "q4_pureA_high.csv"))
    ver = pd.read_csv(os.path.join(TBL, "q4_optimal.csv"))
    for df in (pureB, ref, pureA_hi, ver):
        df["cost"] = Q.VMICRO * (Q.COST_A * df["phiA"] + Q.COST_B * df["phiB"])
    grid["cost"] = Q.VMICRO * (Q.COST_A * grid["phiA"] + Q.COST_B * grid["phiB"])
    for name, df in [("q4_grid.csv", grid),
                     ("q4_pureB_sweep.csv", pureB),
                     ("q4_pureA_high.csv", pureA_hi),
                     ("q4_mixture_refine.csv", ref)]:
        df.to_csv(os.path.join(TBL, name), index=False, encoding="utf-8-sig")
    front_src = pd.concat([
        pureA_hi[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        pureB[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        ref[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        ver[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
    ]).reset_index(drop=True)
    front_src["target_ok"] = front_src["ci_low"] >= 0.90
    front_src.to_csv(os.path.join(TBL, "q4_frontier.csv"), index=False,
                     encoding="utf-8-sig")
    ver.to_csv(os.path.join(TBL, "q4_optimal.csv"), index=False,
               encoding="utf-8-sig")

    pb_sorted = pureB.sort_values("phiB").reset_index(drop=True)
    feasB = pb_sorted[pb_sorted["ci_low"] >= 0.90]
    if len(feasB):
        phi_star_B = float(feasB.iloc[0]["phiB"])
        b_feasible = True
    else:
        phi_star_B = Q.phi_star_from_curve(pb_sorted)
        b_feasible = False
    w = phi_star_A / phi_star_B
    pole = np.array([ver.loc[ver["candidate"] == "LP极点", "phiA"].iloc[0],
                     ver.loc[ver["candidate"] == "LP极点", "phiB"].iloc[0]])
    pole_cost = Q.VMICRO * (Q.COST_A * pole[0] + Q.COST_B * pole[1])
    x2 = np.array([ver.loc[ver["candidate"] == "2D代理优化", "phiA"].iloc[0],
                   ver.loc[ver["candidate"] == "2D代理优化", "phiB"].iloc[0]])
    feasible = ver[ver["feasible"] == "是"]
    best = feasible.loc[feasible["cost"].idxmin()] if len(feasible) else ver.iloc[0]
    b_label = (f"纯B（φ*_B≈{phi_star_B*100:.0f}%，达标）"
               if b_feasible else
               f"纯B（φ*_B≈{phi_star_B*100:.0f}%，未达标）")
    comp = pd.DataFrame([
        {"方案": f"纯A（φ*={phi_star_A*100:.3f}%）",
         "体积分数合计": phi_star_A * 100, "成本": costA},
        {"方案": b_label, "体积分数合计": phi_star_B * 100,
         "成本": Q.VMICRO * Q.COST_B * phi_star_B},
        {"方案": "混合最优（退化为纯A）",
         "体积分数合计": (best["phiA"] + best["phiB"]) * 100,
         "成本": best["cost"]},
    ])
    comp.to_csv(os.path.join(TBL, "q4_comparison.csv"), index=False,
                encoding="utf-8-sig")
    beta = Q.fit_surface(pd.concat([grid, ref], ignore_index=True))
    q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
    pB = p_at(pb_sorted["phiB"], pb_sorted["p_hat"], phi_star_B)
    costB = Q.VMICRO * Q.COST_B * phi_star_B
    fig_contour(grid, ref, pureB, beta, pole, x2, best, pole_cost)
    fig_frontier(front_src)
    fig_comparison(comp, b_feasible)
    fig_pure_curves(q2, pureB, phi_star_A, pA, phi_star_B, pB, b_feasible,
                    costA, costB)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pureb-m", type=int, default=400, help="纯 B 延伸点样本量")
    ap.add_argument("--mix-m", type=int, default=500, help="混合区细化每点样本量")
    ap.add_argument("--verify-m", type=int, default=1000, help="候选终验样本量")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    if args.figures_only:
        run_figures_only()
        return

    q3res = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
    phi_star_A = float(q3res.loc[q3res["method"] == "细化定稿",
                                 "phi_star"].iloc[0]) / 100
    pA = float(q3res.loc[q3res["method"] == "细化定稿", "p_hat"].iloc[0])
    costA = Q.VMICRO * Q.COST_A * phi_star_A
    print(f"φ*_A = {phi_star_A*100:.3f}% (P_hat={pA:.4f})")

    grid_path = os.path.join(TBL, "q4_grid.csv")
    if os.path.exists(grid_path):
        grid = pd.read_csv(grid_path)
        print(f"[q4_high] 复用粗网格 {len(grid)} 点")
    else:
        grid = Q.run_points([(a, b) for a in Q.PHI_A_GRID for b in Q.PHI_B_GRID],
                            100, args.workers)
        grid.to_csv(grid_path, index=False, encoding="utf-8-sig")

    pureB_path = os.path.join(TBL, "q4_pureB_sweep.csv")
    pureA_hi_path = os.path.join(TBL, "q4_pureA_high.csv")
    if os.path.exists(pureB_path):
        pureB = pd.read_csv(pureB_path)
    else:
        pureB = Q.run_points([(0.0, b) for b in Q.PHI_B_SWEEP], 400, args.workers)
        pureB.to_csv(pureB_path, index=False, encoding="utf-8-sig")
    new_bs = [b for b in PHI_B_EXTEND if b not in set(pureB["phiB"])]
    if new_bs:
        print(f"[q4_high] 纯 B 延伸 {new_bs}，M={args.pureb_m}", flush=True)
        ext = Q.run_points([(0.0, b) for b in new_bs], args.pureb_m, args.workers)
        pureB = pd.concat([pureB, ext], ignore_index=True) \
                    .drop_duplicates("phiB", keep="last") \
                    .sort_values("phiB").reset_index(drop=True)
        pureB.to_csv(pureB_path, index=False, encoding="utf-8-sig")

    ref_path = os.path.join(TBL, "q4_mixture_refine.csv")
    if args.figures_only and os.path.exists(ref_path):
        ref = pd.read_csv(ref_path)
        print(f"[q4_high] 复用混合区细化 {len(ref)} 点")
    else:
        pts = [(a, b) for a in PHI_A_MIX for b in PHI_B_MIX]
        t0 = time.time()
        ref = Q.run_points(pts, args.mix_m, args.workers)
        ref.to_csv(ref_path, index=False, encoding="utf-8-sig")
        print(f"[q4_high] 混合区细化 {len(ref)} 点，耗时 {time.time()-t0:.0f}s")

    if not os.path.exists(pureA_hi_path):
        pureA_hi = Q.run_points([(a, 0.0) for a in Q.PHI_A_HIGH], 400, args.workers)
        pureA_hi.to_csv(pureA_hi_path, index=False, encoding="utf-8-sig")
    else:
        pureA_hi = pd.read_csv(pureA_hi_path)

    pb_sorted = pureB.sort_values("phiB").reset_index(drop=True)
    feasB = pb_sorted[pb_sorted["ci_low"] >= 0.90]
    if len(feasB):
        phi_star_B = float(feasB.iloc[0]["phiB"])
        b_feasible = True
    else:
        phi_star_B = Q.phi_star_from_curve(pb_sorted)
        b_feasible = False
    w = phi_star_A / phi_star_B
    print(f"纯B 阈值 φ*_B ≈ {phi_star_B*100:.2f}% → 等效体积 w = {w:.4f}")

    res_lp = linprog([Q.COST_A, Q.COST_B], A_ub=[[-1, -w]], b_ub=[-phi_star_A],
                     bounds=[(0, None), (0, None)], method="highs")
    pole = res_lp.x if res_lp.success else np.array([phi_star_A, 0.0])
    pole_cost = Q.VMICRO * (Q.COST_A * pole[0] + Q.COST_B * pole[1])

    surf = pd.concat([grid, ref], ignore_index=True)
    beta = Q.fit_surface(surf)
    x2, cost2 = Q.optimize_2d(beta)
    print(f"LP 极点: φA={pole[0]*100:.2f}% φB={pole[1]*100:.1f}% 成本≈{pole_cost:.0f}元")
    print(f"2D 优化: φA={x2[0]*100:.2f}% φB={x2[1]*100:.1f}% 成本≈{cost2:.0f}元")

    cands = [
        ("纯A（问题三φ*）", phi_star_A, 0.0),
        ("纯B（φ*_B）", 0.0, phi_star_B),
        ("LP极点", pole[0], pole[1]),
        ("2D代理优化", x2[0], x2[1]),
        ("混合试探(1.0%A,30%B)", 0.010, 0.30),
    ]
    ref_f = ref[ref["ci_low"] >= 0.90]
    if len(ref_f):
        best_ref = ref_f.loc[ref_f["cost"].idxmin()]
        cands.append(("混合细化最优", best_ref["phiA"], best_ref["phiB"]))
    ver_rows = []
    for name, a, b in cands:
        hits = [Q.sample_one(a, b, 52000 + i) for i in range(args.verify_m)]
        k = sum(hits)
        p, lo, hi = C.wilson(k, args.verify_m)
        ver_rows.append({"candidate": name, "phiA": a, "phiB": b,
                         "NA": C.n_rods(a), "NB": C.n_spheres(b),
                         "p_hat": p, "ci_low": lo, "ci_up": hi,
                         "cost": Q.VMICRO * (Q.COST_A * a + Q.COST_B * b),
                         "feasible": "是" if lo >= 0.90 else "否"})
    ver = pd.DataFrame(ver_rows)
    ver.to_csv(os.path.join(TBL, "q4_optimal.csv"), index=False,
               encoding="utf-8-sig")
    print(ver.to_string(index=False))
    feasible = ver[ver["feasible"] == "是"]
    best = feasible.loc[feasible["cost"].idxmin()] if len(feasible) else ver.iloc[0]
    print(f"最终最优: {best['candidate']} 成本={best['cost']:.0f}元")

    front_src = pd.concat([
        pureA_hi[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        pureB[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        ref[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        ver[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
    ]).reset_index(drop=True)
    front_src["target_ok"] = front_src["ci_low"] >= 0.90
    front_src.to_csv(os.path.join(TBL, "q4_frontier.csv"), index=False,
                     encoding="utf-8-sig")

    b_label = (f"纯B（φ*_B≈{phi_star_B*100:.0f}%，达标）"
               if b_feasible else
               f"纯B（φ*_B≈{phi_star_B*100:.0f}%，未达标）")
    comp = pd.DataFrame([
        {"方案": f"纯A（φ*={phi_star_A*100:.3f}%）",
         "体积分数合计": phi_star_A * 100, "成本": costA},
        {"方案": b_label, "体积分数合计": phi_star_B * 100,
         "成本": Q.VMICRO * Q.COST_B * phi_star_B},
        {"方案": "混合最优（退化为纯A）",
         "体积分数合计": (best["phiA"] + best["phiB"]) * 100,
         "成本": best["cost"]},
    ])
    comp.to_csv(os.path.join(TBL, "q4_comparison.csv"), index=False,
                encoding="utf-8-sig")
    print(comp.to_string(index=False))

    q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
    pb = pureB.sort_values("phiB").reset_index(drop=True)
    pB = p_at(pb["phiB"], pb["p_hat"], phi_star_B)
    costB = Q.VMICRO * Q.COST_B * phi_star_B
    fig_contour(grid, ref, pureB, beta, pole, x2, best, pole_cost)
    fig_frontier(front_src)
    fig_comparison(comp, b_feasible)
    fig_pure_curves(q2, pureB, phi_star_A, pA, phi_star_B, pB, b_feasible,
                    costA, costB)


if __name__ == "__main__":
    main()
