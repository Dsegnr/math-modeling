# -*- coding: utf-8 -*-
"""
数据驱动补图（主会话，数据已落定）：
  1. q2_evolution.png   相变演化：φ=0.5/0.8/1.0/1.2/1.5% 接触网络多面板
  2. q3_methods_compare.png  双方法互证：三方法 φ* 与终验 P̂ 对比
  3. q3_diagnostics.png      拟合诊断：sigmoid/幂律拟合曲线与残差（AIC 对比）
运行：python code/data_figures.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import common as C
import q3_fit_bisect as q3

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")


def fig_q2_evolution():
    C.setup_font()
    from matplotlib.lines import Line2D
    q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
    phis = [0.005, 0.008, 0.010, 0.012, 0.015]
    fig, axes = plt.subplots(1, 5, figsize=(17, 3.6))
    fig.suptitle("渗流相变演化：孤立簇 → 跨接路径 → 全导通（接触网络，XY 俯视）",
                 fontsize=13)
    for k, (ax, phi) in enumerate(zip(axes, phis)):
        rng = np.random.default_rng(2026 + k)
        N = C.n_rods(phi)
        segs = C.sample_rods_c1(N, rng)
        mids = 0.5 * (segs[:, 0] + segs[:, 1])
        edges, tL, tR = C.contact_edges(segs)
        path = C.find_spanning_path(segs)
        clabels = C.cluster_labels(segs)
        counts = np.bincount(clabels, minlength=clabels.max() + 1)
        max_id = int(np.argmax(counts))
        C.style_clean(ax, grid=False)
        if len(edges):
            for a, b in edges:
                inpath = path is not None and a in path and b in path
                if inpath:
                    ax.plot([mids[a, 0], mids[b, 0]],
                            [mids[a, 1], mids[b, 1]],
                            color="#00B050", lw=1.6, zorder=4)
                else:
                    ax.plot([mids[a, 0], mids[b, 0]],
                            [mids[a, 1], mids[b, 1]],
                            color=(0.42, 0.42, 0.42, 0.22), lw=0.5, zorder=2)
        if path is not None:
            for i in path:
                if tL[i]:
                    ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="#00B050", lw=1.0, alpha=0.8, zorder=4)
                if tR[i]:
                    ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                            color="#00B050", lw=1.0, alpha=0.8, zorder=4)
        for i in range(N):
            if clabels[i] == max_id:
                ax.scatter(mids[i, 0], mids[i, 1], s=8, c="#ED7D31",
                           alpha=0.9, edgecolors="white", linewidths=0.3,
                           zorder=5)
            elif path is not None and i in path:
                ax.scatter(mids[i, 0], mids[i, 1], s=9, c="#00B050",
                           alpha=0.95, edgecolors="white", linewidths=0.3,
                           zorder=5)
            else:
                ax.scatter(mids[i, 0], mids[i, 1], s=5, color=(0.55, 0.58, 0.65),
                           alpha=0.55, zorder=3)
        ax.scatter([-C.HALF, C.HALF], [0, 0], marker="s", s=55,
                   c=["#D62728", "#1F77B4"], edgecolor="white", lw=1.0,
                   zorder=6)
        ax.set_xlim(-C.HALF - 120, C.HALF + 120)
        ylo = max(mids[:, 1].min(), -C.HALF) - 120
        yhi = min(mids[:, 1].max(), C.HALF) + 120
        ax.set_ylim(ylo, yhi)
        ax.set_aspect("equal")
        ax.set_xticks([-5000, 0, 5000])
        ax.set_yticks([])
        ax.set_xlabel("X (nm)", fontsize=8)
        r = q2[q2["phi"] == phi].iloc[0]
        status = "导通" if path is not None else "不导通"
        ax.set_title(f"φ={phi*100:.1f}%（N={N}）\nP_hat={r['p_hat']:.3f} · {status}",
                     fontsize=10)
    handles = [
        Line2D([0], [0], color="#00B050", lw=2, label="跨接路径（左→右）"),
        Line2D([0], [0], color=(0.42, 0.42, 0.42, 0.5), lw=1, label="接触边"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ED7D31",
               ms=6, label="最大连通簇"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=(0.55, 0.58, 0.65), ms=5, label="其余段"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#D62728",
               ms=6, label="左带电面（红）"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#1F77B4",
               ms=6, label="右带电面（蓝）"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, 0.01))
    fig.tight_layout(rect=[0, 0.10, 1, 0.92])
    C.save_fig(fig, os.path.join(FIG, "q2_evolution.png"))


def fig_q3_methods_compare():
    C.setup_font()
    q3r = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    names = q3r["method"].tolist()
    phi = q3r["phi_star"].tolist()
    p = q3r["p_hat"].tolist()
    ci_lo = q3r["ci_low"].tolist()
    ci_hi = q3r["ci_up"].tolist()
    colors = ["#C00000", "#ED7D31", "#00B050"]
    x = np.arange(len(names))
    bars = ax.bar(x, phi, width=0.5, color=colors, edgecolor="black", lw=0.6)
    for xi, b, v in zip(x, bars, phi):
        ax.text(xi, v + 0.018, f"{v:.3f}%", ha="center", fontsize=11,
                fontweight="bold")
    ax.axhline(1.359, ls="--", color="#00B050", lw=1.2, alpha=0.8)
    ax.text(0.05, 1.362, "定稿 φ*=1.359%", color="#00B050", fontsize=9,
            va="top")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("φ* (%)")
    ax.set_ylim(1.25, 1.45)
    ax.set_title("问题三 φ* 三方法互证与终验可靠性")
    ax.grid(True, axis="y", ls="--", alpha=0.3)
    C.style_clean(ax, grid=False)
    ax2 = ax.twinx()
    ax2.errorbar(x, [v * 100 for v in p],
                 yerr=[[(v - l) * 100 for v, l in zip(p, ci_lo)],
                       [(h - v) * 100 for v, h in zip(p, ci_hi)]],
                 fmt="o", color="#1F77B4", ms=7, capsize=4, zorder=5,
                 label="终验 P_hat ±95% CI")
    ax2.axhline(90, ls=":", color="#C00000", lw=1.0, alpha=0.7)
    ax2.set_ylabel("终验导通概率 P_hat (%)", color="#1F77B4")
    ax2.set_ylim(80, 100)
    ax2.tick_params(labelsize=9, colors="#1F77B4")
    ax2.text(2.42, 90.5, "P_hat 90% 阈值", ha="right", va="center",
             color="#C00000", fontsize=8,
             bbox=dict(fc="white", alpha=0.85, pad=1.5, ec="none"))
    for xi, v, l, h in zip(x, p, ci_lo, ci_hi):
        ax2.text(xi, h * 100 + 3.2, f"P_hat={v:.3f}\nCI[{l:.3f},{h:.3f}]",
                 ha="center", fontsize=7.5, color="#1F77B4")
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2,
               fontsize=8.5, frameon=False)
    ax.text(0.02, 0.97, "拟合反解偏乐观（CI 规则不达标）→ 概率二分与细化定稿互证；"
                        "细化定稿 3 种子 M=9000 最严",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#404040",
            bbox=dict(fc="white", alpha=0.9, ec="0.7", lw=0.5, pad=3))
    fig.subplots_adjust(bottom=0.20)
    C.save_fig(fig, os.path.join(FIG, "q3_methods_compare.png"))


def fig_q3_diagnostics():
    C.setup_font()
    q2 = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
    fit = pd.read_csv(os.path.join(TBL, "q3_fit_params.csv"))
    models = {}
    for _, r in fit.iterrows():
        s = r["params"].replace("np.float64(", "").replace(")", "") \
            .strip("[] ")
        params = np.array([float(v.strip()) for v in s.split(",")
                           if v.strip()])
        models[r["kind"]] = {"params": params, "aic": r["aic"],
                             "phi_star": r["phi_star"]}
    x = q2["phi"].to_numpy()
    y = q2["p_hat"].to_numpy()
    ci_w = (q2["ci_up"] - q2["ci_low"]).to_numpy()
    xs = np.linspace(0.004, 0.016, 300)
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 7), sharex=True,
                             gridspec_kw={"height_ratios": [2.2, 1]})
    ax = axes[0]
    ax.errorbar(q2["phi_percent"], y * 100,
                yerr=[(y - q2["ci_low"]) * 100, (q2["ci_up"] - y) * 100],
                fmt="o", color="#4472C4", ms=5, capsize=3,
                label="MC 点估计（M=3000，95% Wilson 区间）")
    colors = {"sigmoid": "#C00000", "power": "#ED7D31"}
    for name, m in models.items():
        if name == "sigmoid":
            yv = q3.sigmoid(xs, *m["params"])
        else:
            yv = q3.power_law(xs, *m["params"])
        ax.plot(xs * 100, yv * 100, color=colors[name], lw=1.8,
                label=f"{'sigmoid' if name=='sigmoid' else '幂律截断'} 拟合 "
                      f"(AIC={m['aic']:.1f})")
    ax.axhline(90, ls="--", color="#00B050", lw=1.2, label="P=90%")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_ylim(0, 100)
    ax.set_title("渗透模型拟合诊断：曲线形态与残差（回应“结果不硬”教训）")
    ax.grid(True, ls="--", alpha=0.3)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7", fontsize=9,
              loc="upper left")
    C.style_clean(ax, grid=False)
    ax2 = axes[1]
    for name, m in models.items():
        if name == "sigmoid":
            yv = q3.sigmoid(x, *m["params"])
        else:
            yv = q3.power_law(x, *m["params"])
        resid = (y - yv) * 100
        rmse = float(np.sqrt(np.mean(resid ** 2)))
        label = ("sigmoid" if name == "sigmoid" else "幂律截断") + \
                f" (RMSE={rmse:.1f}%)"
        ax2.errorbar(q2["phi_percent"], resid, yerr=ci_w * 100,
                     fmt="o", ms=4, capsize=2, color=colors[name], alpha=0.85,
                     label=label)
    ax2.axhline(0, color="black", lw=0.9)
    ax2.set_xlabel("体积分数 φ (%)")
    ax2.set_ylabel("残差 = MC 估计 − 拟合 (%)")
    ax2.grid(True, ls="--", alpha=0.3)
    ax2.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax2.text(0.02, 0.94, "误差棒 = 95% Wilson 区间",
             transform=ax2.transAxes, fontsize=7.5, color="#404040")
    C.style_clean(ax2, grid=False)
    fig.tight_layout()
    C.save_fig(fig, os.path.join(FIG, "q3_diagnostics.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_q2_evolution()
    fig_q3_methods_compare()
    fig_q3_diagnostics()
