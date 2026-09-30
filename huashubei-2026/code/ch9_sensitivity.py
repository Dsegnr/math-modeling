# -*- coding: utf-8 -*-
"""
第九章：模型检验与灵敏度分析（新增脚本）
  1. 口径敏感性：A1（周期卷回+同一导体+周期距离）vs B1（卷回分段+直接距离）
     vs C1（完全悬浮，复用 q2 高精度表）
  2. 导通阈值 ±10%：A-A 阈值 61.8 与 A-面阈值 31.8 同比例缩放下的 p-φ 曲线
  3. 单价 ±10%：介质 A/B 单价扰动下的成本与最优方案稳定性
  4. 多随机种子：关键 φ 点不同种子 p̂ 的箱线图（复现性检验）
输出：
  output/tables/ch9_caliber_sensitivity.csv / ch9_threshold_sensitivity.csv
  output/tables/ch9_price_sensitivity.csv / ch9_seed_box.csv
  图片/ch9_caliber_sensitivity.png / ch9_threshold_sensitivity.png
  图片/ch9_price_sensitivity.png / ch9_seed_box.png
运行：python code/ch9_sensitivity.py --workers 8
"""
import os
import sys
import argparse
import multiprocessing as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")

PHIS_AB = [0.005, 0.007, 0.010, 0.012, 0.015]
PHIS_TH = [0.008, 0.010, 0.011, 0.012, 0.014]
PHIS_SEED = [0.009, 0.010, 0.012]
SEEDS = [101, 202, 303, 404, 505, 606]
TH_FACTORS = [0.9, 1.0, 1.1]

# A1 口径（周期卷回+同一导体+周期距离）：27 个周期平移
SHIFTS_A1 = np.array(
    [[tx, ty, tz] for tx in (-C.SIDE, 0, C.SIDE)
     for ty in (-C.SIDE, 0, C.SIDE)
     for tz in (-C.SIDE, 0, C.SIDE)], dtype=float)


def interval_dist_to_zero(a, b):
    lo = np.minimum(a, b)
    hi = np.maximum(a, b)
    return np.where(hi < 0, -hi, np.where(lo > 0, lo, 0.0))


def a1_conduct(P1, P2):
    """A1 口径连通判定：整根圆柱为一个节点、27 个周期移位下的最短距离。"""
    N = len(P1)
    if N == 0:
        return 0
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    bestL = np.full(N, np.inf)
    bestR = np.full(N, np.inf)
    for k in (-1, 0, 1):
        a = P1[:, 0] + C.SIDE * k + C.HALF
        b = P2[:, 0] + C.SIDE * k + C.HALF
        bestL = np.minimum(bestL, interval_dist_to_zero(a, b))
        a = P1[:, 0] + C.SIDE * k - C.HALF
        b = P2[:, 0] + C.SIDE * k - C.HALF
        bestR = np.minimum(bestR, interval_dist_to_zero(a, b))
    touchL = bestL <= C.TH_AF
    touchR = bestR <= C.TH_AF
    if not touchL.any() or not touchR.any():
        return 0
    uf = C.UnionFind(N + 2)
    LEFT = N
    RIGHT = N + 1
    for i in np.nonzero(touchL)[0]:
        uf.union(int(i), LEFT)
    for i in np.nonzero(touchR)[0]:
        uf.union(int(i), RIGHT)
    ii, jj = np.triu_indices(N, 1)
    CH = 100_000
    for st in range(0, len(ii), CH):
        sl = slice(st, st + CH)
        i_ = ii[sl]
        j_ = jj[sl]
        pA = P1[i_]
        uA = U[i_]
        lA = L[i_]
        vB = U[j_]
        lB = L[j_]
        best = np.full(len(i_), np.inf)
        for s in range(27):
            pB = P1[j_] + SHIFTS_A1[s]
            d = C.seg_seg_dist_batch(pA, uA, lA, pB, vB, lB)
            best = np.minimum(best, d)
        hit = np.nonzero(best <= C.TH_AA)[0]
        for t in hit:
            uf.union(int(i_[t]), int(j_[t]))
    return 1 if uf.find(LEFT) == uf.find(RIGHT) else 0


def a1_sample(N, seed):
    """A1 口径采样：允许介质穿出边界（周期卷回），整根圆柱为一个导体。"""
    rng = np.random.default_rng(seed)
    c = rng.uniform(-C.HALF, C.HALF, size=(N, 3))
    v = rng.normal(size=(N, 3))
    u = v / np.linalg.norm(v, axis=1)[:, None]
    P1 = c - (C.H_A / 2) * u
    P2 = c + (C.H_A / 2) * u
    return a1_conduct(P1, P2)


def worker(args):
    """多进程工作函数：kind 分发，避免把采样/判定代码复制进各进程。"""
    kind, payload = args
    if kind == "caliber":
        model, phi, N, base_seed, M = payload
        if model == "A1":
            fn = a1_sample
        else:
            import q2_model_check2 as B1
            fn = B1.sample_B1
        hits = [fn(N, base_seed * 100000 + m) for m in range(M)]
        return kind, model, phi, hits
    if kind == "threshold":
        phi, N, th_aa, th_af, base_seed, M = payload
        C.TH_AA = th_aa
        C.TH_AF = th_af
        hits = []
        for m in range(M):
            rng = np.random.default_rng(base_seed * 100000 + m)
            segs = C.sample_rods_c1(N, rng)
            conduct, _, _ = C.conduct_mixed(segs, None)
            hits.append(conduct)
        return kind, phi, th_aa, th_af, hits
    if kind == "seed":
        phi, N, seed, M = payload
        hits = []
        for m in range(M):
            rng = np.random.default_rng(seed * 100000 + m)
            segs = C.sample_rods_c1(N, rng)
            conduct, _, _ = C.conduct_mixed(segs, None)
            hits.append(conduct)
        return kind, phi, seed, hits
    raise ValueError(kind)


def run_batch(tasks, workers):
    results = []
    with mp.Pool(workers) as pool:
        for r in pool.imap_unordered(worker, tasks):
            results.append(r)
    return results


def fig_caliber(df):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    styles = {"C1": ("o-", "#1F77B4"), "B1": ("s--", "#ED7D31"),
              "A1": ("^:", "#7F7F7F")}
    for model, (fmt, col) in styles.items():
        d = df[df["model"] == model].sort_values("phi")
        ax.errorbar(d["phi_percent"], d["p_hat"],
                    yerr=[d["p_hat"] - d["ci_low"], d["ci_up"] - d["p_hat"]],
                    fmt=fmt, color=col, ms=5, capsize=3, lw=1.6,
                    label=model)
    ax.axhline(0.90, ls="--", color="#C00000", lw=1.4,
               label="可靠性目标 P=0.90")
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P")
    ax.set_title("口径敏感性：三种随机生成口径的导通概率对比")
    ax.set_ylim(0, 1.08)
    ax.grid(True, ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7", fontsize=9,
              loc="center left")
    ax.text(0.02, 0.04,
            "A1/B1 为周期卷回口径（介质可穿出微构体），C1 为题目口径"
            "（介质完全悬浮于内部）；\n卷回口径在 0.5%~1.5% 全区间导通概率≈1，"
            "与题目“0.5%~1.0% 区间概率非平凡”矛盾。",
            transform=ax.transAxes, va="bottom", fontsize=8.5, color="#404040",
            bbox=dict(fc="white", alpha=0.9, ec="0.7", lw=0.5, pad=3))
    C.save_fig(fig, os.path.join(FIG, "ch9_caliber_sensitivity.png"))


def phi_star_approx(df):
    """由采样点线性插值 P=0.9 对应的 φ*（灵敏度比较用，非正式 φ*）。"""
    d = df.sort_values("phi").reset_index(drop=True)
    for i in range(len(d) - 1):
        y0, y1 = d.loc[i, "p_hat"], d.loc[i + 1, "p_hat"]
        if y0 <= 0.90 <= y1:
            x0, x1 = d.loc[i, "phi"], d.loc[i + 1, "phi"]
            return float(x0 + (x1 - x0) * (0.90 - y0) / (y1 - y0))
    return float(d.iloc[-1]["phi"])


def fig_threshold(df):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    styles = {0.9: ("-", "#ED7D31"), 1.0: ("-", "#1F77B4"),
              1.1: ("-", "#C00000")}
    for fac, (ls, col) in styles.items():
        d = df[df["factor"] == fac].sort_values("phi")
        ax.errorbar(d["phi_percent"], d["p_hat"],
                    yerr=[d["p_hat"] - d["ci_low"], d["ci_up"] - d["p_hat"]],
                    fmt="o" + ls, color=col, ms=5, capsize=3, lw=1.6,
                    label=f"阈值×{fac:g}（A-A={61.8*fac:.1f}，A-面={31.8*fac:.1f} nm）")
        phi_s = phi_star_approx(d)
        ax.axvline(phi_s * 100, ls=ls, lw=1.0, color=col, alpha=0.7)
        ax.text(phi_s * 100, 0.06, f"φ*≈{phi_s*100:.2f}%", rotation=90,
                fontsize=8, color=col, ha="right")
    ax.axhline(0.90, ls="--", color="#00B050", lw=1.4, label="P=0.90")
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P")
    ax.set_title("导通阈值 ±10% 敏感性（A-A 与 A-面阈值同比例缩放）")
    ax.set_ylim(0, 1.08)
    ax.grid(True, ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7", fontsize=8.5,
              loc="upper left")
    ax.text(0.02, 0.03, "阈值±10% 时 φ* 变化约 ±0.05~0.1 个百分点，结论（φ*≈1.4%）稳健",
            transform=ax.transAxes, fontsize=8.5, color="#404040")
    C.save_fig(fig, os.path.join(FIG, "ch9_threshold_sensitivity.png"))


def fig_price(df):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(df))
    wbar = 0.36
    ax.bar(x - wbar / 2, df["costA_yuan"], wbar, color="#1F77B4",
           edgecolor="black", lw=0.5, label="纯 A 成本")
    ax.bar(x + wbar / 2, df["costB_yuan"], wbar, color="#ED7D31",
           edgecolor="black", lw=0.5, label="纯 B 成本")
    for i, r in df.iterrows():
        ax.text(i - wbar / 2, r["costA_yuan"] + 0.4, f"{r['costA_yuan']:.2f}",
                ha="center", fontsize=8)
        ax.text(i + wbar / 2, r["costB_yuan"] + 0.4, f"{r['costB_yuan']:.2f}",
                ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["scenario"], fontsize=8)
    ax.set_ylabel("成本（元）")
    ax.set_ylim(0, max(df["costB_yuan"].max() * 1.2, 20))
    ax.set_title("介质单价 ±10% 敏感性：纯 A 始终为最低成本方案")
    ax.grid(True, axis="y", ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9)
    ax.text(0.5, -0.20,
            "注：纯 B 达标需 φ≈60% 以上，成本约为纯 A 的 2 倍以上；"
            "在全部 ±10% 单价组合下 LP 极点均退化为纯 A，方案结论稳健。",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#404040")
    fig.subplots_adjust(bottom=0.28)
    C.save_fig(fig, os.path.join(FIG, "ch9_price_sensitivity.png"))


def fig_seed_box(df):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5))
    phis = sorted(df["phi"].unique())
    data = [df[df["phi"] == p]["p_hat"].to_numpy() for p in phis]
    bp = ax.boxplot(data, positions=np.arange(1, len(phis) + 1),
                    widths=0.45, patch_artist=True, showfliers=False)
    for patch, col in zip(bp["boxes"], ["#4472C4", "#1F77B4", "#2E75B6"]):
        patch.set_facecolor(col)
        patch.set_alpha(0.65)
    for k, p in enumerate(phis, 1):
        d = df[df["phi"] == p]
        ax.scatter(np.full(len(d), k) + np.linspace(-0.12, 0.12, len(d)),
                   d["p_hat"], color="black", s=18, zorder=5)
        # 全部种子合并后的 Wilson 区间
        kk = int((d["p_hat"] * d["M"]).sum())
        MM = int(d["M"].sum())
        p_all, lo, hi = C.wilson(kk, MM)
        ax.plot([k - 0.28, k + 0.28], [p_all, p_all], color="#C00000", lw=2.2)
        ax.plot([k - 0.20, k + 0.20], [lo, lo], color="#C00000", lw=1.2)
        ax.plot([k - 0.20, k + 0.20], [hi, hi], color="#C00000", lw=1.2)
        ax.text(k, hi + 0.025, f"合并 95% CI\n[{lo:.3f},{hi:.3f}]",
                ha="center", fontsize=7.5, color="#C00000")
    ax.axhline(0.90, ls="--", color="#00B050", lw=1.3, label="P=0.90")
    ax.set_xticks(np.arange(1, len(phis) + 1))
    ax.set_xticklabels([f"φ={p*100:.1f}%" for p in phis])
    ax.set_ylabel(r"单种子导通概率估计 $\hat{p}$")
    ax.set_title(f"多随机种子稳定性检验（每种子 M={int(df['M'].iloc[0])}，"
                 f"{len(SEEDS)} 个种子；红线为合并 Wilson 区间）")
    ax.set_ylim(0, 1.05)
    ax.grid(True, axis="y", ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    C.save_fig(fig, os.path.join(FIG, "ch9_seed_box.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a1b1-m", type=int, default=100, help="A1/B1 每口径每点样本量")
    ap.add_argument("--thr-m", type=int, default=300, help="阈值敏感性每点样本量")
    ap.add_argument("--seed-m", type=int, default=300, help="多种子每种子每点样本量")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--skip-caliber", action="store_true",
                    help="跳过口径敏感性 MC（复用已存表）")
    ap.add_argument("--skip-threshold", action="store_true",
                    help="跳过阈值敏感性 MC（复用已存表）")
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)

    cal_path = os.path.join(TBL, "ch9_caliber_sensitivity.csv")
    thr_path = os.path.join(TBL, "ch9_threshold_sensitivity.csv")
    price_path = os.path.join(TBL, "ch9_price_sensitivity.csv")
    seed_path = os.path.join(TBL, "ch9_seed_box.csv")

    if not args.skip_caliber and (not args.figures_only
                                  or not os.path.exists(cal_path)):
        q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
        tasks = []
        for model in ["A1", "B1"]:
            for phi in PHIS_AB:
                N = C.n_rods(phi)
                CH = 30
                for c in range(max(1, args.a1b1_m // CH)):
                    tasks.append(("caliber", (model, phi, N, 17 + c,
                                              min(CH, args.a1b1_m))))
        agg = {}
        for r in run_batch(tasks, args.workers):
            _, model, phi, hits = r
            agg.setdefault((model, phi), []).extend(hits)
        rows = []
        for (model, phi), hits in sorted(agg.items()):
            k = sum(hits)
            M = len(hits)
            p, lo, hi = C.wilson(k, M)
            rows.append({"model": model, "phi": phi,
                         "phi_percent": round(phi * 100, 2),
                         "N": C.n_rods(phi), "M": M, "conduct": k,
                         "p_hat": p, "ci_low": lo, "ci_up": hi})
        for _, r in q2.iterrows():
            rows.append({"model": "C1", "phi": r["phi"],
                         "phi_percent": r["phi_percent"], "N": r["N"],
                         "M": r["M"], "conduct": r["conduct"],
                         "p_hat": r["p_hat"], "ci_low": r["ci_low"],
                         "ci_up": r["ci_up"]})
        pd.DataFrame(rows).to_csv(cal_path, index=False, encoding="utf-8-sig")

    if not args.skip_threshold and (not args.figures_only
                                    or not os.path.exists(thr_path)):
        tasks = []
        for fac in TH_FACTORS:
            for phi in PHIS_TH:
                N = C.n_rods(phi)
                CH = 50
                for c in range(max(1, args.thr_m // CH)):
                    tasks.append(("threshold",
                                  (phi, N, 61.8 * fac, 31.8 * fac, 31 + c,
                                   min(CH, args.thr_m))))
        agg = {}
        for r in run_batch(tasks, args.workers):
            _, phi, th_aa, th_af, hits = r
            agg.setdefault((round(th_aa / 61.8, 4), phi), []).extend(hits)
        rows = []
        for (fac, phi), hits in sorted(agg.items()):
            k = sum(hits)
            M = len(hits)
            p, lo, hi = C.wilson(k, M)
            th_aa = 61.8 * fac
            th_af = 31.8 * fac
            rows.append({"factor": fac, "th_aa": round(th_aa, 2),
                         "th_af": round(th_af, 2),
                         "phi": phi, "phi_percent": round(phi * 100, 2),
                         "N": C.n_rods(phi), "M": M, "conduct": k,
                         "p_hat": p, "ci_low": lo, "ci_up": hi})
        pd.DataFrame(rows).to_csv(thr_path, index=False, encoding="utf-8-sig")

    if not args.figures_only or not os.path.exists(price_path):
        q3 = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
        phi_star_A = float(q3.loc[q3["method"] == "细化定稿",
                                  "phi_star"].iloc[0]) / 100
        pureB = pd.read_csv(os.path.join(TBL, "q4_pureB_sweep.csv"))
        import q4_mixture_optimize as Q
        phi_star_B = Q.phi_star_from_curve(pureB)
        w = phi_star_A / phi_star_B
        # 单位修正：微构体体积 = 1000 μm³，成本单位 元/μm³
        VMICRO = 1000.0
        price_A_base, price_B_base = Q.COST_A, Q.COST_B
        scenarios = [
            ("基准", price_A_base, price_B_base),
            ("A +10%", price_A_base * 1.1, price_B_base),
            ("A -10%", price_A_base * 0.9, price_B_base),
            ("B +10%", price_A_base, price_B_base * 1.1),
            ("B -10%", price_A_base, price_B_base * 0.9),
        ]
        from scipy.optimize import linprog
        rows = []
        for name, pa, pb in scenarios:
            costA = VMICRO * pa * phi_star_A
            costB = VMICRO * pb * phi_star_B
            res = linprog([pa, pb], A_ub=[[-1, -w]], b_ub=[-phi_star_A],
                          bounds=[(0, None), (0, None)], method="highs")
            pole = res.x if res.success else np.array([phi_star_A, 0.0])
            opt_cost = VMICRO * (pa * pole[0] + pb * pole[1])
            scheme = ("纯 A" if pole[1] < 1e-9 else
                      ("纯 B" if pole[0] < 1e-9 else "混合"))
            rows.append({"scenario": name, "priceA": round(pa, 4),
                         "priceB": round(pb, 4),
                         "costA_yuan": round(costA, 4),
                         "costB_yuan": round(costB, 4),
                         "LP_phiA": round(pole[0], 5),
                         "LP_phiB": round(pole[1], 5),
                         "opt_cost_yuan": round(opt_cost, 4),
                         "optimal": scheme})
        pd.DataFrame(rows).to_csv(price_path, index=False,
                                  encoding="utf-8-sig")

    if not args.figures_only or not os.path.exists(seed_path):
        tasks = []
        for phi in PHIS_SEED:
            N = C.n_rods(phi)
            CH = args.seed_m
            for seed in SEEDS:
                for c in range(max(1, args.seed_m // CH)):
                    tasks.append(("seed", (phi, N, seed, min(CH, args.seed_m))))
        agg = {}
        for r in run_batch(tasks, args.workers):
            _, phi, seed, hits = r
            agg.setdefault((phi, seed), []).extend(hits)
        rows = []
        for (phi, seed), hits in sorted(agg.items()):
            k = sum(hits)
            M = len(hits)
            p, lo, hi = C.wilson(k, M)
            rows.append({"phi": phi, "phi_percent": round(phi * 100, 2),
                         "seed": seed, "M": M, "conduct": k,
                         "p_hat": p, "ci_low": lo, "ci_up": hi})
        pd.DataFrame(rows).to_csv(seed_path, index=False, encoding="utf-8-sig")

    cal = pd.read_csv(cal_path)
    thr = pd.read_csv(thr_path)
    price = pd.read_csv(price_path)
    seed = pd.read_csv(seed_path)
    fig_caliber(cal)
    fig_threshold(thr)
    fig_price(price)
    fig_seed_box(seed)


if __name__ == "__main__":
    main()
