# -*- coding: utf-8 -*-
"""
问题二：C1 口径蒙特卡洛导通概率（正式版）。
输出：
  output/tables/q2_probabilities.csv        四档+曲线点概率表
  data/processed/q2_mc_raw.csv              逐样本原始结果（可复现）
  figures/q2/q2_p_phi_curve.png             p-φ 渗流曲线（Wilson 误差棒）
  figures/q2/q2_convergence_1.00%.png       样本量-概率收敛曲线
  figures/q2/q2_typical_configs.png         典型导通/不导通构型三维图
"""
import os
import sys
import time
import argparse
import multiprocessing as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")
PROC = os.path.join(BASE, "data", "processed")

PHIS_REQUIRED = [0.005, 0.006, 0.007, 0.010]
PHIS_CURVE = [0.008, 0.009, 0.012, 0.015]


def worker(args):
    phi, N, base_seed, M = args
    hits = []
    for m in range(M):
        rng = np.random.default_rng(base_seed * 100000 + m)
        segs = C.sample_rods_c1(N, rng)
        conduct, _, _ = C.conduct_mixed(segs, None)
        hits.append(conduct)
    return phi, hits


def run_mc(phis, M, workers):
    tasks = []
    CHUNK = 40
    for phi in phis:
        N = C.n_rods(phi)
        for c in range(max(1, M // CHUNK)):
            tasks.append((phi, N, 42 + c, min(CHUNK, M)))
    results = {phi: [] for phi in phis}
    t0 = time.time()
    with mp.Pool(workers) as pool:
        for phi, hits in pool.imap_unordered(worker, tasks):
            results[phi].extend(hits)
    print(f"[mc] {len(tasks)} 个任务完成，耗时 {time.time()-t0:.0f}s")
    return results


def save_raw(results, path):
    rows = []
    for phi, hits in results.items():
        for h in hits:
            rows.append({"phi": phi, "conduct": h})
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def fig_curve(prob_df):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = prob_df["phi_percent"]
    ax.errorbar(x, prob_df["p_hat"], yerr=[
        prob_df["p_hat"] - prob_df["ci_low"],
        prob_df["ci_up"] - prob_df["p_hat"]],
        fmt="o-", color="#C00000", capsize=4, lw=1.8, ms=6,
        label="蒙特卡洛估计 ±95% Wilson 区间")
    ax.axhline(0.90, ls="--", color="#4472C4", lw=1.5,
               label="可靠性目标 P=0.90")
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P")
    ax.set_title("介质 A 导通概率随体积分数的变化（C1 口径）")
    ax.grid(True, ls="--", alpha=0.35)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(prob_df["phi_percent"].tolist())
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9)
    for _, r in prob_df.iterrows():
        ax.annotate(f"N={int(r['N'])}", (r["phi_percent"], r["p_hat"]),
                    textcoords="offset points", xytext=(0, 13),
                    fontsize=8, ha="center", color="#404040",
                    bbox=dict(fc="white", alpha=0.75, pad=1, ec="none"))
    ax.text(0.02, 0.03, "口径 C1：介质完全位于微构体内部",
            fontsize=9, color="#606060", transform=ax.transAxes)
    C.save_fig(fig, os.path.join(FIG, "q2_p_phi_curve.png"))


def fig_convergence(results, phi=0.010):
    C.setup_font()
    hits = np.array(results[phi], dtype=int)
    M = len(hits)
    cum = np.cumsum(hits) / np.arange(1, M + 1)
    ms = np.arange(1, M + 1)
    z = 1.96
    # Wilson 得分区间（逐样本量）
    den = 1 + z * z / ms
    center = (cum + z * z / (2 * ms)) / den
    half = z * np.sqrt(cum * (1 - cum) / ms + z * z / (4 * ms * ms)) / den
    lo = np.clip(center - half, 0.0, 1.0)
    hi = np.clip(center + half, 0.0, 1.0)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ms, cum, color="#C00000", lw=1.6, label=r"运行估计 $\hat{p}$")
    ax.fill_between(ms, lo, hi, color="#C00000", alpha=0.18,
                    label="95% Wilson 区间")
    ax.axhline(cum[-1], ls=":", color="#404040", lw=1,
               label=rf"最终估计 $\hat{{p}}$≈{cum[-1]:.3f}")
    ax.set_xlabel("蒙特卡洛样本量 M")
    ax.set_ylabel(r"导通概率估计 $\hat{p}$")
    ax.set_title(f"蒙特卡洛收敛性诊断（φ=1.00%，N={C.n_rods(phi)}）",
                 fontsize=12)
    ax.grid(True, ls="--", alpha=0.35)
    ax.set_ylim(0, 1.05)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    p_f, lo_f, hi_f = C.wilson(int(hits.sum()), M)
    ax.text(0.98, 0.04,
            rf"最终 $\hat{{p}}$={p_f:.3f}，95% CI [{lo_f:.3f}, {hi_f:.3f}]",
            transform=ax.transAxes, ha="right", fontsize=9, color="#404040",
            bbox=dict(fc="white", alpha=0.85, pad=2, ec="0.7", lw=0.5))
    C.save_fig(fig, os.path.join(FIG, "q2_convergence_1.00%.png"))


def fig_typical(results, phi=0.007):
    """取一个导通样本与一个不导通样本，画 2D 接触网络对比图。"""
    C.setup_font()
    rng = np.random.default_rng(2026)
    N = C.n_rods(phi)
    examples = []
    while len(examples) < 2:
        segs = C.sample_rods_c1(N, rng)
        conduct, _, _ = C.conduct_mixed(segs, None)
        status = "导通" if conduct else "不导通"
        if (status == "导通" and not any(s == "导通" for s, _ in examples)) or \
           (status == "不导通" and not any(s == "不导通" for s, _ in examples)):
            examples.append((status, segs))
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    fig.subplots_adjust(left=0.09, right=0.99, top=0.86, bottom=0.20)
    for k, (ax, (status, segs)) in enumerate(zip(axes, examples), 1):
        n = len(segs)
        mids = 0.5 * (segs[:, 0] + segs[:, 1])
        edges, tL, tR = C.contact_edges(segs)
        path = C.find_spanning_path(segs) if status == "导通" else None
        clabels = C.cluster_labels(segs)
        counts = np.bincount(clabels, minlength=clabels.max() + 1)
        max_id = int(np.argmax(counts))
        if status == "导通":
            hi_set = set(path) if path is not None else {max_id}
            hi_color = "#00B050"
        else:
            hi_set = {max_id}
            hi_color = "#ED7D31"
        deg = np.zeros(n, dtype=int)
        if len(edges):
            deg[edges[:, 0]] += 1
            deg[edges[:, 1]] += 1
        C.style_clean(ax, grid=False)
        # 接触边
        for a, b in edges:
            inpath = path is not None and a in path and b in path
            inhi = status != "导通" and a in hi_set and b in hi_set
            if inpath:
                ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                        color="white", lw=3.8, zorder=3)
                ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                        color="#00B050", lw=2.2, zorder=4)
            elif inhi:
                ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                        color="#ED7D31", lw=1.6, alpha=0.85, zorder=3)
            else:
                ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                        color=(0.42, 0.42, 0.42, 0.28), lw=0.6, zorder=2)
        for i in np.nonzero(tL)[0]:
            ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                    color="#D62728", lw=0.5, alpha=0.30, zorder=1)
        for i in np.nonzero(tR)[0]:
            ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                    color="#1F77B4", lw=0.5, alpha=0.30, zorder=1)
        if path is not None:
            for i in path:
                if tL[i]:
                    ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="white", lw=3.8, zorder=3)
                    ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="#00B050", lw=2.2, zorder=4)
                if tR[i]:
                    ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="white", lw=3.8, zorder=3)
                    ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="#00B050", lw=2.2, zorder=4)
        # 节点
        for i in range(n):
            if i in hi_set:
                s = 22 + 3 * min(deg[i], 8)
                alpha = 0.95
            else:
                s = 12
                alpha = 0.55
            col = hi_color if i in hi_set else (0.62, 0.62, 0.62)
            ax.scatter(mids[i, 0], mids[i, 1], s=s, c=[col], alpha=alpha,
                       edgecolors="white", linewidths=0.6, zorder=5)
        if path is not None:
            pl = list(path)
            ax.scatter(mids[pl, 0], mids[pl, 1], s=38, facecolors="none",
                       edgecolors="#111111", linewidths=1.4, zorder=6)
        ax.scatter([-C.HALF, C.HALF], [0.0, 0.0], marker="s", s=120,
                   c=["#D62728", "#1F77B4"], edgecolor="white", lw=1.4, zorder=7)
        ax.set_xlim(-C.HALF - 120, C.HALF + 120)
        ylo = min(mids[:, 1].min(), 0.0) - 120
        yhi = max(mids[:, 1].max(), 0.0) + 120
        ax.set_ylim(ylo, yhi)
        ax.set_yticks(np.linspace(ylo, yhi, 3).round(0))
        ax.set_aspect(0.62)
        ax.set_xlabel("X (nm)")
        ax.set_ylabel("Y (nm)")
        ax.text(-0.06, 1.03, "(a)" if k == 1 else "(b)",
                transform=ax.transAxes, fontsize=12, fontweight="bold")
        ax.set_title(f"φ={phi*100:.2f}%，N={N}：{status}", fontsize=12)
        if status != "导通":
            ax.text(0.02, 0.97, f"最大连通簇仅 {len(hi_set)} 段，未跨接"
                                "（亚渗流阈值特征）",
                    transform=ax.transAxes, va="top", fontsize=8.5,
                    color="#B45309",
                    bbox=dict(fc="white", alpha=0.9, ec="none", pad=2))
        handles = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=hi_color, ms=9,
                   label="导通路径（左→右）" if status == "导通"
                   else "最大连通簇（未跨接）"),
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=(0.62, 0.62, 0.62), ms=7, label="其余段"),
            Line2D([0], [0], color=(0.42, 0.42, 0.42, 0.5), lw=1,
                   label="接触边（≤61.8 nm）"),
            Line2D([0], [0], color="#D62728", lw=1.2, label="左面接触边"),
            Line2D([0], [0], color="#1F77B4", lw=1.2, label="右面接触边"),
        ]
        ax.legend(handles=handles, loc="upper center",
                  bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=7.5,
                  frameon=True, framealpha=0.95, edgecolor="0.7")
    fig.suptitle("典型蒙特卡洛构型：接触网络对比（节点大小 ∝ 接触数）",
                 fontsize=13)
    C.save_fig(fig, os.path.join(FIG, "q2_typical_configs.png"))


def fig_cluster_sizes():
    """渗流簇大小分布：φ=0.7% 与 1.0% 各取一个典型构型。"""
    C.setup_font()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, phi in zip(axes, [0.007, 0.010]):
        rng = np.random.default_rng(2026)
        N = C.n_rods(phi)
        segs = C.sample_rods_c1(N, rng)
        _, _, sizes = C.conduct_mixed(segs, None, need_clusters=True)
        sizes = np.sort(np.array(sizes))[::-1]
        top = sizes[:12]
        bars = ax.bar(np.arange(1, len(top) + 1), top,
                      color="#4472C4", edgecolor="black", lw=0.5)
        for b, v in zip(bars, top):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.05, f"{v}",
                    ha="center", fontsize=8)
        ax.set_yscale("log")
        ax.set_xlabel("连通簇排序（按段数降序）")
        ax.set_ylabel("簇内段数（对数轴）")
        ax.set_title(f"φ={phi*100:.2f}%（N={N}）")
        ax.grid(True, axis="y", ls="--", alpha=0.3)
        C.style_clean(ax, grid=False)
        ax.text(0.97, 0.93, f"最大簇占比 {sizes[0]/len(segs)*100:.0f}%",
                transform=ax.transAxes, ha="right", fontsize=9,
                bbox=dict(fc="white", alpha=0.85, ec="0.7", pad=1.5))
    fig.suptitle("渗流簇大小分布：随体积分数增大，最大簇迅速吞并小簇",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    C.save_fig(fig, os.path.join(FIG, "q2_cluster_sizes.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=400, help="每个 φ 的样本量")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存结果只重绘图表")
    args = ap.parse_args()
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(PROC, exist_ok=True)

    raw_path = os.path.join(PROC, "q2_mc_raw.csv")
    if args.figures_only and os.path.exists(raw_path):
        raw = pd.read_csv(raw_path)
        results = {phi: raw.loc[raw["phi"] == phi, "conduct"].astype(int).tolist()
                   for phi in sorted(raw["phi"].unique())}
        prob_df = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
        print("[q2] 复用已存 MC 结果，仅重绘图表")
    else:
        phis = sorted(set(PHIS_REQUIRED + PHIS_CURVE))
        results = run_mc(phis, args.m, args.workers)
        save_raw(results, raw_path)
        rows = []
        for phi in phis:
            k = sum(results[phi])
            M = len(results[phi])
            p, lo, hi = C.wilson(k, M)
            rows.append({"phi": phi, "phi_percent": round(phi * 100, 2),
                         "N": C.n_rods(phi), "M": M, "conduct": k,
                         "p_hat": round(p, 4), "ci_low": round(lo, 4),
                         "ci_up": round(hi, 4)})
        prob_df = pd.DataFrame(rows)
        prob_df.to_csv(os.path.join(TBL, "q2_probabilities.csv"),
                       index=False, encoding="utf-8-sig")
    print(prob_df.to_string(index=False))

    fig_curve(prob_df)
    fig_convergence(results, phi=0.010)
    fig_typical(results, phi=0.007)
    fig_cluster_sizes()


if __name__ == "__main__":
    main()
