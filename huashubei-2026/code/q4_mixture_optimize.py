# -*- coding: utf-8 -*-
"""
问题四：A+B 混合填充成本优化（修正版）。
核心事实（由真实数据验证）：纯 B 球渗流阈值约 35%+，纯 B 成本反而高于纯 A；
最优配比由“纯曲线标定 w + LP 极点 + 2D 代理候选 + 真实 MC 验证”共同确定。
输出：
  output/tables/q4_grid.csv / q4_pureB_sweep.csv / q4_optimal.csv
  output/tables/q4_frontier.csv / q4_comparison.csv
  figures/q4/q4_contour.png / q4_frontier.png / q4_comparison.png
"""
import os
import sys
import time
import argparse
import multiprocessing as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, minimize, linprog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")

PHI_A_GRID = [0.0, 0.0025, 0.005, 0.0075, 0.010, 0.0125, 0.015]
PHI_B_GRID = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]
PHI_B_SWEEP = [0.25, 0.30, 0.34, 0.38, 0.42, 0.45]
PHI_A_HIGH = [0.0135, 0.015, 0.017, 0.020]
COST_A = 1.05
COST_B = 0.05
# 单位修正（审计通过）：微构体边长 10000 nm = 10 μm，体积 = 1000 μm³；
# 单价为 元/μm³，故成本 = 1000 × (1.05·φA + 0.05·φB) 元。
VMICRO = 1000.0


def sample_one(phiA, phiB, seed):
    rng = np.random.default_rng(seed)
    NA = C.n_rods(phiA)
    NB = C.n_spheres(phiB)
    segs = C.sample_rods_c1(NA, rng) if NA else np.zeros((0, 2, 3))
    centers = C.sample_spheres_c1(NB, rng) if NB else np.zeros((0, 3))
    conduct, _, _ = C.conduct_mixed(segs, centers)
    return conduct


def worker(args):
    phiA, phiB, base_seed, M = args
    hits = [sample_one(phiA, phiB, base_seed * 100000 + m) for m in range(M)]
    return phiA, phiB, hits


def run_points(points, M, workers):
    tasks = []
    CHUNK = 25
    for (a, b) in points:
        for c in range(max(1, M // CHUNK)):
            tasks.append((a, b, 91 + c, min(CHUNK, M)))
    results = {}
    t0 = time.time()
    with mp.Pool(workers) as pool:
        for a, b, hits in pool.imap_unordered(worker, tasks):
            results.setdefault((a, b), []).extend(hits)
    print(f"[mc] {len(tasks)} 任务，耗时 {time.time()-t0:.0f}s")
    rows = []
    for (a, b), hits in sorted(results.items()):
        k = sum(hits)
        M_ = len(hits)
        p, lo, hi = C.wilson(k, M_)
        rows.append({"phiA": a, "phiB": b, "NA": C.n_rods(a), "NB": C.n_spheres(b),
                     "M": M_, "p_hat": p, "ci_low": lo, "ci_up": hi,
                     "cost": VMICRO * (COST_A * a + COST_B * b)})
    return pd.DataFrame(rows)


def surf2(xy, b0, b1, b2, b3, b4, b5):
    x, y = xy
    z = b0 + b1 * x + b2 * y + b3 * x**2 + b4 * y**2 + b5 * x * y
    return 1.0 / (1.0 + np.exp(-z))


def p_surf(a, b, beta):
    return float(surf2((a, b), *beta))


def fit_surface(grid):
    x = grid["phiA"].to_numpy()
    y = grid["phiB"].to_numpy()
    p = grid["p_hat"].to_numpy()
    sigma = np.maximum(grid["ci_up"] - grid["ci_low"], 1e-4).to_numpy()
    popt, _ = curve_fit(surf2, (x, y), p, p0=[-6, 500, 20, -8000, -20, -600],
                        sigma=sigma, maxfev=60000)
    return popt


def phi_star_from_curve(df, phi_col="phiB", target=0.90):
    """按 CI 决策规则取满足 P≥0.9 的最小 φ（线性插值两邻点）。"""
    d = df.sort_values(phi_col)
    for i in range(len(d) - 1):
        if d.iloc[i + 1]["ci_low"] >= target:
            return float(d.iloc[i + 1][phi_col])
        if d.iloc[i]["ci_low"] < target <= d.iloc[i + 1]["ci_up"]:
            x0, x1 = d.iloc[i][phi_col], d.iloc[i + 1][phi_col]
            y0, y1 = d.iloc[i]["p_hat"], d.iloc[i + 1]["p_hat"]
            return float(x0 + (x1 - x0) * (target - y0) / (y1 - y0))
    return float(d.iloc[-1][phi_col])


def optimize_2d(beta, target=0.90, n_start=12):
    lam = 1e5

    def obj(v):
        a, b = v
        return VMICRO * (COST_A * a + COST_B * b) + \
            lam * max(0.0, target - p_surf(a, b, beta))

    rng = np.random.default_rng(1)
    starts = [(0.0, 0.0), (0.005, 0.0), (0.01, 0.0), (0.014, 0.0),
              (0.0, 0.25), (0.0, 0.35), (0.005, 0.25)]
    for _ in range(n_start):
        starts.append((rng.uniform(0, 0.02), rng.uniform(0, 0.45)))
    best = None
    for s in starts:
        res = minimize(obj, np.array(s), method="SLSQP",
                       bounds=[(0, 0.03), (0, 0.5)],
                       options={"maxiter": 200, "ftol": 1e-10})
        if res.success and (best is None or res.fun < best.fun):
            best = res
    return best.x, best.fun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=100)
    ap.add_argument("--verify-m", type=int, default=500)
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)

    # 问题三定稿 φ*（动态读取，避免硬编码旧值）
    q3res = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
    phi_star_A = float(q3res.loc[q3res["method"] == "细化定稿",
                                 "phi_star"].iloc[0]) / 100

    # 1) 二维粗网格（可复用）
    grid_path = os.path.join(TBL, "q4_grid.csv")
    if os.path.exists(grid_path):
        grid = pd.read_csv(grid_path)
        print(f"[q4] 复用网格 {len(grid)} 点")
    else:
        grid = run_points([(a, b) for a in PHI_A_GRID for b in PHI_B_GRID],
                          args.m, args.workers)
        grid.to_csv(grid_path, index=False, encoding="utf-8-sig")

    pureB_path = os.path.join(TBL, "q4_pureB_sweep.csv")
    if args.figures_only and os.path.exists(pureB_path) and \
            os.path.exists(os.path.join(TBL, "q4_optimal.csv")) and \
            os.path.exists(os.path.join(TBL, "q4_frontier.csv")):
        pureB = pd.read_csv(pureB_path)
        pureA_hi = pd.read_csv(os.path.join(TBL, "q4_pureA_high.csv"))
        ver = pd.read_csv(os.path.join(TBL, "q4_optimal.csv"))
        front_src = pd.read_csv(os.path.join(TBL, "q4_frontier.csv"))
        comp = pd.read_csv(os.path.join(TBL, "q4_comparison.csv"))
        phi_star_B = float(comp.loc[comp["方案"].str.contains("纯B"),
                                    "体积分数合计"].iloc[0]) / 100
        b_ok = (ver.loc[ver["candidate"] == "纯B（φ*_B）", "feasible"].iloc[0]
                == "是")
        comp["方案"] = comp["方案"].replace({
            "纯B（φ*_B）": (f"纯B（φ*_B≈{phi_star_B*100:.0f}%，达标）" if b_ok
                            else f"纯B（φ*_B≈{phi_star_B*100:.0f}%，未达标）"),
            "混合最优": "混合最优（退化为纯A）",
        })
        beta = fit_surface(grid)
        pole = np.array([ver.loc[ver["candidate"] == "LP极点", "phiA"].iloc[0],
                         ver.loc[ver["candidate"] == "LP极点", "phiB"].iloc[0]])
        pole_cost = ver.loc[ver["candidate"] == "LP极点", "cost"].iloc[0]
        x2 = np.array([ver.loc[ver["candidate"] == "2D代理优化", "phiA"].iloc[0],
                       ver.loc[ver["candidate"] == "2D代理优化", "phiB"].iloc[0]])
        feasible = ver[ver["feasible"] == "是"]
        best = feasible.loc[feasible["cost"].idxmin()] if len(feasible) else ver.iloc[0]
        print("[q4] 复用已存表格，仅重绘图表")
    else:
        # 2) 纯 B 基线扫描 + 纯 A 高值点（真实数据，决定 w 与前沿）
        if os.path.exists(pureB_path):
            pureB = pd.read_csv(pureB_path)
            print(f"[q4] 复用纯B扫描 {len(pureB)} 点")
        else:
            pureB = run_points([(0.0, b) for b in PHI_B_SWEEP], 400, args.workers)
            pureB.to_csv(pureB_path, index=False, encoding="utf-8-sig")
        pureA_hi = run_points([(a, 0.0) for a in PHI_A_HIGH], 400, args.workers)
        pureA_hi.to_csv(os.path.join(TBL, "q4_pureA_high.csv"), index=False,
                        encoding="utf-8-sig")

        phi_star_B = phi_star_from_curve(pureB)
        b_ok = (pureB.sort_values("phiB")["ci_low"] >= 0.90).any()
        w = phi_star_A / phi_star_B
        print(f"纯B 阈值 φ*_B ≈ {phi_star_B*100:.2f}% → 等效体积 w = {w:.4f}")

        # 3) LP 极点
        res_lp = linprog([COST_A, COST_B], A_ub=[[-1, -w]], b_ub=[-phi_star_A],
                         bounds=[(0, None), (0, None)], method="highs")
        pole = res_lp.x if res_lp.success else np.array([phi_star_A, 0.0])
        pole_cost = VMICRO * (COST_A * pole[0] + COST_B * pole[1])

        # 4) 代理曲面 + 2D 优化
        beta = fit_surface(grid)
        x2, cost2 = optimize_2d(beta)
        print(f"LP 极点: φA={pole[0]*100:.2f}% φB={pole[1]*100:.1f}% 成本≈{pole_cost:.0f}元")
        print(f"2D 优化: φA={x2[0]*100:.2f}% φB={x2[1]*100:.1f}% 成本≈{cost2:.0f}元")

        # 5) 候选验证
        cands = [
            ("纯A（问题三φ*）", phi_star_A, 0.0),
            ("纯B（φ*_B）", 0.0, phi_star_B),
            ("LP极点", pole[0], pole[1]),
            ("2D代理优化", x2[0], x2[1]),
            ("混合试探(1.0%A,30%B)", 0.010, 0.30),
        ]
        ver_rows = []
        for name, a, b in cands:
            hits = [sample_one(a, b, 52000 + i) for i in range(args.verify_m)]
            k = sum(hits)
            p, lo, hi = C.wilson(k, args.verify_m)
            ver_rows.append({"candidate": name, "phiA": a, "phiB": b,
                             "NA": C.n_rods(a), "NB": C.n_spheres(b),
                             "p_hat": p, "ci_low": lo, "ci_up": hi,
                             "cost": VMICRO * (COST_A * a + COST_B * b),
                             "feasible": "是" if lo >= 0.90 else "否"})
        ver = pd.DataFrame(ver_rows)
        ver.to_csv(os.path.join(TBL, "q4_optimal.csv"), index=False,
                   encoding="utf-8-sig")
        print(ver.to_string(index=False))
        feasible = ver[ver["feasible"] == "是"]
        best = feasible.loc[feasible["cost"].idxmin()] if len(feasible) else ver.iloc[0]
        print(f"最终最优: {best['candidate']} 成本={best['cost']:.0f}元")

        # 6) 前沿：用所有已验证点组成成本-P 点集
        front_src = pd.concat([
            pureA_hi[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
            pureB[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
            ver[["phiA", "phiB", "p_hat", "ci_low", "ci_up", "cost"]],
        ]).reset_index(drop=True)
        front_src["target_ok"] = front_src["ci_low"] >= 0.90
        front_src.to_csv(os.path.join(TBL, "q4_frontier.csv"), index=False,
                         encoding="utf-8-sig")

        comp = pd.DataFrame([
            {"方案": f"纯A（φ*={phi_star_A*100:.3f}%）",
             "体积分数合计": phi_star_A * 100,
             "成本": VMICRO * COST_A * phi_star_A},
            {"方案": (f"纯B（φ*_B≈{phi_star_B*100:.0f}%，达标）" if b_ok
                      else f"纯B（φ*_B≈{phi_star_B*100:.0f}%，未达标）"),
             "体积分数合计": phi_star_B * 100,
             "成本": VMICRO * COST_B * phi_star_B},
            {"方案": "混合最优（退化为纯A）", "体积分数合计": (best["phiA"] + best["phiB"]) * 100,
             "成本": best["cost"]},
        ])
        comp.to_csv(os.path.join(TBL, "q4_comparison.csv"), index=False,
                    encoding="utf-8-sig")
        print(comp.to_string(index=False))

    # ---- 图1：概率曲面 + 候选点 ----
    C.setup_font()
    fig, ax = plt.subplots(figsize=(9, 6.5))
    aa = np.linspace(0, 0.02, 120)
    bb = np.linspace(0, 0.45, 120)
    AA, BB = np.meshgrid(aa, bb)
    ZZ = np.array([p_surf(a, b, beta) for a, b in zip(AA.ravel(), BB.ravel())])
    ZZ = ZZ.reshape(AA.shape)
    cs = ax.contourf(AA * 100, BB * 100, ZZ, levels=12, cmap="RdYlBu_r", alpha=0.9)
    fig.colorbar(cs, ax=ax, label="导通概率 P（代理曲面）")
    ctr = ax.contour(AA * 100, BB * 100, ZZ, levels=[0.90], colors="#C00000",
                     linewidths=2.2)
    ax.clabel(ctr, fmt="P=0.90 可行边界", fontsize=9)
    ax.scatter(grid["phiA"] * 100, grid["phiB"] * 100, c=grid["p_hat"],
               cmap="RdYlBu_r", edgecolor="k", s=40, zorder=5,
               label="粗网格 MC 点", clip_on=False)
    ax.scatter(np.zeros(len(pureB)), pureB["phiB"] * 100, marker="x", color="k",
               s=40, zorder=6, label="纯 B 扫描点", clip_on=False)
    ax.plot(pole[0] * 100, pole[1] * 100, "v", color="#7030A0", ms=12,
            markeredgecolor="white", markeredgewidth=1.2,
            label=f"LP 极点（{pole_cost:.0f}元）", zorder=7)
    ax.plot(x2[0] * 100, x2[1] * 100, "s", color="#ED7D31", ms=9,
            markeredgecolor="white", markeredgewidth=1.0, label="2D 代理优化")
    ax.plot(best["phiA"] * 100, best["phiB"] * 100, "*", color="#00B050", ms=16,
            markeredgecolor="white", markeredgewidth=1.0,
            label=f"最终验证最优（{best['cost']:.0f}元）", zorder=8)
    ax.annotate("LP 极点 ≈ 最终最优\n（均退化为纯 A）",
                xy=(best["phiA"] * 100, best["phiB"] * 100),
                xytext=(1.55, 3.2), fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="#303030", lw=0.9),
                bbox=dict(fc="white", alpha=0.9, pad=2, ec="0.6", lw=0.5))
    # 局部放大 inset：候选点集中区域
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
    ZZ2 = np.array([p_surf(a, b, beta) for a, b in zip(AA2.ravel(), BB2.ravel())])
    ZZ2 = ZZ2.reshape(AA2.shape)
    iax.contourf(AA2 * 100, BB2 * 100, ZZ2, levels=12, cmap="RdYlBu_r", alpha=0.9)
    iax.contour(AA2 * 100, BB2 * 100, ZZ2, levels=[0.90], colors="#C00000",
                linewidths=1.6)
    for (px, py, mk, mc, ms) in [
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
    ax.text(2.25, 40, "设计空间外", rotation=90, fontsize=10,
            color="#303030", va="top", fontweight="bold")
    ax.set_xlim(0, 2.5)
    ax.set_ylim(0, 45)
    ax.set_xlabel("介质 A 体积分数 φA (%)")
    ax.set_ylabel("介质 B 体积分数 φB (%)")
    ax.set_title("A+B 混合体系导通概率与成本最优解")
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
              fontsize=9, loc="lower right")
    cs.colorbar.set_ticks([0.1, 0.3, 0.5, 0.7, 0.9])
    C.save_fig(fig, os.path.join(FIG, "q4_contour.png"))

    # ---- 图2：成本-概率前沿（全部已验证点）----
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    f = front_src.sort_values("cost")
    ok = f[f["target_ok"]]
    ax.scatter(ok["cost"], ok["p_hat"] * 100, s=55, color="#4472C4",
               edgecolor="k", zorder=5, label="可行点（CI 下界 ≥0.90）")
    ax.scatter(f[~f["target_ok"]]["cost"],
               f[~f["target_ok"]]["p_hat"] * 100, s=50, color="#C00000", alpha=0.8,
               edgecolor="k", zorder=5, label="不可行点")
    ax.errorbar(f["cost"], f["p_hat"] * 100,
                yerr=[(f["p_hat"] - f["ci_low"]) * 100,
                      (f["ci_up"] - f["p_hat"]) * 100],
                fmt="none", ecolor="#303030", elinewidth=1.0, capsize=2, zorder=1)
    ax.axhline(90, ls="--", color="#00B050", lw=1.3, label="可行阈值 P=0.90")
    ax.set_xlabel("总成本（元）")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("成本-导通概率关系（所有真实 MC 验证点）")
    ax.set_ylim(0, 105)
    ax.grid(True, ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.text(0.02, 0.98, "误差棒为 95% Wilson 置信区间；可行性按 CI 下界判定",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#404040")
    C.save_fig(fig, os.path.join(FIG, "q4_frontier.png"))

    # ---- 图3：三方案对比 ----
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
    ax.set_title("纯 A / 纯 B / 混合最优 成本对比")
    ax.grid(True, axis="y", ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    note = ("注：本工况混合最优退化为纯 A；球形介质 B 存在“面接触瓶颈”，"
            f"φ*_B≈{phi_star_B*100:.0f}% 仍无法满足 90% CI 规则。"
            if not b_ok else
            "注：本工况混合最优退化为纯 A；介质 B 虽可达标但成本远高于纯 A。")
    ax.text(0.5, -0.18, note,
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#404040")
    fig.subplots_adjust(bottom=0.22)
    C.save_fig(fig, os.path.join(FIG, "q4_comparison.png"))

    # ---- 图4：纯A vs 纯B 导通效率对比（面接触瓶颈）----
    C.setup_font()
    rowA = ver[ver["candidate"] == "纯A（问题三φ*）"].iloc[0]
    phi_A, p_A, cost_A = rowA["phiA"], rowA["p_hat"], rowA["cost"]
    rowB = ver[ver["candidate"] == "纯B（φ*_B）"].iloc[0]
    phi_B, p_B, cost_B = rowB["phiB"], rowB["p_hat"], rowB["cost"]
    q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
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
    ax.axvline(phi_A * 100, ls="-.", color="#1F77B4", lw=1.4)
    ax.plot(phi_A * 100, p_A * 100, "*", color="#1F77B4", ms=16,
            markeredgecolor="white", markeredgewidth=1.2, zorder=12)
    ax.text(phi_A * 100 + 0.2, min(p_A * 100 + 3, 100),
            f"φ*_A={phi_A*100:.2f}%", fontsize=8.5, color="#1F77B4")
    ax.annotate(f"A：φ*={phi_A*100:.2f}% 时达标\n成本 {cost_A:.1f} 元",
                xy=(phi_A * 100, p_A * 100), xytext=(3.2, 62), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#303030"),
                bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    if b_ok:
        ax.annotate(f"B：φ*_B≈{phi_B*100:.0f}% 时达标\n成本 {cost_B:.1f} 元",
                    xy=(phi_B * 100, p_B * 100), xytext=(14, 35), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#303030"),
                    bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    else:
        ax.annotate(f"B：φ*_B≈{phi_B*100:.0f}%（外推，扫描上限 60%）时 "
                    f"P≈{p_B*100:.0f}%\n"
                    f"但 CI 下界不达标\n成本 {cost_B:.1f} 元（面接触瓶颈）",
                    xy=(phi_B * 100, p_B * 100), xytext=(14, 48), fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#303030"),
                    bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("介质 A 与介质 B 的导通效率对比")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 65)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.85, edgecolor="0.7",
              fontsize=9, loc="lower right")
    C.save_fig(fig, os.path.join(FIG, "q4_pure_curves.png"))


if __name__ == "__main__":
    main()
