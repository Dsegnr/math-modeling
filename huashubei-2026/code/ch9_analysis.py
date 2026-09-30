# -*- coding: utf-8 -*-
"""
第九章：模型的分析与检验（按问题补充检验项）
  问题一：阈值 ±10% 下三组导通判定是否改变（主口径/合并口径对照）
  问题二：样本量 M 与估计精度（P̂/Wilson 区间宽度随 M 收敛，复用 q2 raw）
  问题三：阈值 ±10% 对 φ* 的影响（由阈值敏感性曲线插值反解）
  问题四：等效体积 w 敏感性 + 纯 B 外推不确定性（复用 q4 表）
输出：
  output/tables/ch9_q1_threshold.csv / ch9_q2_m_accuracy.csv
  output/tables/ch9_q3_threshold_phi_star.csv / ch9_q4_w_sensitivity.csv
  output/tables/ch9_q4_phiB_uncertainty.csv
  图片/3_正文结果图/ch9_q1_threshold.png / ch9_q2_m_accuracy.png
  图片/3_正文结果图/ch9_q4_w_sensitivity.png
运行：python code/ch9_analysis.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import linprog
import common as C
import q1_connectivity as Q1

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")
GROUPS = ["组1", "组2", "组3"]
FACTORS = [0.9, 1.0, 1.1]


def wilson_row(k, M):
    p, lo, hi = C.wilson(int(k), int(M))
    return p, lo, hi


def sec1_q1():
    """问题一：阈值 ±10% 与口径对照。"""
    rows = []
    segs_all = {g: Q1.parse_group(g) for g in GROUPS}
    labels_all = {g: Q1.merge_groups(segs_all[g]) for g in GROUPS}
    base_aa, base_af = C.TH_AA, C.TH_AF
    for f in FACTORS:
        C.TH_AA = base_aa * f
        C.TH_AF = base_af * f
        for g in GROUPS:
            segs = segs_all[g]
            cond_main, _, _ = C.conduct_mixed(segs, None)
            cond_merge, _, _ = C.conduct_mixed(segs, None,
                                               merge_groups=labels_all[g])
            rows.append({"组": g, "factor": f,
                         "th_aa": round(C.TH_AA, 2),
                         "th_af": round(C.TH_AF, 2),
                         "主口径": "导通" if cond_main else "不导通",
                         "合并口径": "导通" if cond_merge else "不导通"})
    C.TH_AA, C.TH_AF = base_aa, base_af
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(TBL, "ch9_q1_threshold.csv"), index=False,
              encoding="utf-8-sig")
    # 图：3×3 双面板（主口径/合并口径）
    C.setup_font()
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    for ax, col in zip(axes, ["主口径", "合并口径"]):
        mat = np.zeros((3, 3), dtype=int)
        for i, g in enumerate(GROUPS):
            for j, f in enumerate(FACTORS):
                v = df[(df["组"] == g) & (df["factor"] == f)][col].iloc[0]
                mat[i, j] = 1 if v == "导通" else 0
        im = ax.imshow(mat, cmap="RdYlGn", vmin=-0.5, vmax=1.5,
                       aspect="auto")
        ax.set_xticks(range(3))
        ax.set_xticklabels([f"×{f:g}" for f in FACTORS])
        ax.set_yticks(range(3))
        ax.set_yticklabels(GROUPS)
        ax.set_xlabel("导通阈值缩放因子")
        ax.set_title(col + "（橙=不导通，绿=导通）")
        for i in range(3):
            for j in range(3):
                v = "导通" if mat[i, j] else "不导通"
                ax.text(j, i, v, ha="center", va="center", fontsize=10,
                        fontweight="bold",
                        color="white" if mat[i, j] else "#7A1F1F")
        C.style_clean(ax, grid=False)
    fig.suptitle("问题一：导通阈值 ±10% 与口径敏感性", fontsize=13)
    fig.text(0.5, 0.02,
             "结论：合并口径在 ±10% 阈值扰动下全部稳健；主口径仅组3 在 ×0.9 时翻转",
             ha="center", fontsize=9, color="#404040")
    fig.tight_layout(rect=[0, 0.04, 1, 0.92])
    C.save_fig(fig, os.path.join(FIG, "ch9_q1_threshold.png"))


def sec2_q2():
    """问题二：样本量-精度收敛（复用 q2_mc_raw.csv）。"""
    raw = pd.read_csv(os.path.join(BASE, "data", "processed",
                                   "q2_mc_raw.csv"))
    rows = []
    Ms = [500, 1000, 2000, 3000]
    for phi, grp in raw.groupby("phi"):
        hits = grp["conduct"].astype(int).tolist()
        for M in Ms:
            h = hits[:M]
            k = sum(h)
            p, lo, hi = wilson_row(k, len(h))
            rows.append({"phi": phi, "phi_percent": round(phi * 100, 2),
                         "M": len(h), "k": k, "p_hat": round(p, 4),
                         "ci_low": round(lo, 4), "ci_up": round(hi, 4),
                         "ci_width": round(hi - lo, 4)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(TBL, "ch9_q2_m_accuracy.csv"), index=False,
              encoding="utf-8-sig")
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    sel = [0.007, 0.009, 0.010, 0.012, 0.014]
    colors = ["#B45309", "#7030A0", "#C00000", "#1F77B4", "#1F7A3D"]
    for phi, col in zip(sel, colors):
        d = df[df["phi"] == phi].sort_values("M")
        ax.plot(d["M"], d["p_hat"], "o-", color=col, lw=1.6, ms=4,
                label=f"φ={phi*100:.1f}%")
        ax.fill_between(d["M"], d["ci_low"], d["ci_up"], color=col,
                        alpha=0.14)
    ax.axhline(0.90, ls="--", color="#404040", lw=1.2, label="P=0.90")
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_xticks(Ms)
    ax.set_xticklabels([str(m) for m in Ms])
    ax.set_xlabel("蒙特卡洛样本量 M（对数轴）")
    ax.set_ylabel(r"导通概率估计 $\hat{P}$")
    ax.set_title("问题二：样本量-精度收敛（Wilson 区间随 M 收窄）")
    ax.set_ylim(0.2, 1.02)
    ax.grid(True, ls="--", alpha=0.3)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7", fontsize=9,
              loc="center left", bbox_to_anchor=(1.01, 0.5))
    ax.text(0.02, 0.04, "M=3000 时区间半宽约 ±0.01~0.02，φ* 判据（CI 下界≥0.90）稳定",
            transform=ax.transAxes, fontsize=8.5, color="#404040")
    fig.tight_layout(rect=[0, 0, 0.92, 1])
    C.save_fig(fig, os.path.join(FIG, "ch9_q2_m_accuracy.png"))


def phi_star_linear(df):
    d = df.sort_values("phi").reset_index(drop=True)
    for i in range(len(d) - 1):
        y0, y1 = d.loc[i, "p_hat"], d.loc[i + 1, "p_hat"]
        if y0 <= 0.90 <= y1:
            x0, x1 = d.loc[i, "phi"], d.loc[i + 1, "phi"]
            return float(x0 + (x1 - x0) * (0.90 - y0) / (y1 - y0))
    return None


def sec3_q3():
    """问题三：阈值 ±10% 对 φ* 的影响（由阈值敏感性表反解）。"""
    thr = pd.read_csv(os.path.join(TBL, "ch9_threshold_sensitivity.csv"))
    base = phi_star_linear(thr[thr["factor"] == 1.0])
    rows = []
    for fac in FACTORS:
        d = thr[thr["factor"] == fac]
        phi_star = phi_star_linear(d)
        feas = d[d["ci_low"] >= 0.90]
        phi_feas = float(feas.iloc[0]["phi"]) if len(feas) else None
        rows.append({"factor": fac,
                     "phi_star_interp": (round(phi_star * 100, 3)
                                         if phi_star is not None else None),
                     "phi_star_CIrule": (round(phi_feas * 100, 3)
                                         if phi_feas is not None else "未达标"),
                     "delta_vs_base_pp": (
                         round((phi_star - base) * 100, 3)
                         if phi_star is not None and base is not None
                         else None)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(TBL, "ch9_q3_threshold_phi_star.csv"), index=False,
              encoding="utf-8-sig")


def sec4_q4():
    """问题四：等效体积 w 敏感性 + 纯 B 外推不确定性。"""
    q3 = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
    phi_star_A = float(q3.loc[q3["method"] == "细化定稿",
                              "phi_star"].iloc[0]) / 100
    pureB = pd.read_csv(os.path.join(TBL, "q4_pureB_sweep.csv"))
    pb = pureB.sort_values("phiB").reset_index(drop=True)
    feasB = pb[pb["ci_low"] >= 0.90]
    phi_star_B = float(feasB.iloc[0]["phiB"]) if len(feasB) else \
        float(pb.iloc[-1]["phiB"])
    w0 = phi_star_A / phi_star_B
    cA, cB = 1.05, 0.05
    VM = 1000.0
    rows = []
    for wf in [0.8, 0.9, 1.0, 1.1, 1.2]:
        w = w0 * wf
        res = linprog([cA, cB], A_ub=[[-1, -w]], b_ub=[-phi_star_A],
                      bounds=[(0, None), (0, None)], method="highs")
        pole = res.x if res.success else np.array([phi_star_A, 0.0])
        cost = VM * (cA * pole[0] + cB * pole[1])
        scheme = ("纯 A" if pole[1] < 1e-9 else
                  ("纯 B" if pole[0] < 1e-9 else "混合"))
        rows.append({"w_factor": wf, "w": round(w, 5),
                     "LP_phiA": round(pole[0], 5),
                     "LP_phiB": round(pole[1], 5),
                     "cost_yuan": round(cost, 4),
                     "optimal": scheme})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(TBL, "ch9_q4_w_sensitivity.csv"), index=False,
              encoding="utf-8-sig")
    # 图：w 变化下纯 A/纯 B 理论成本
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5))
    wf = np.array([0.8, 0.9, 1.0, 1.1, 1.2])
    costA = VM * cA * phi_star_A
    costB = VM * cB * phi_star_A / (w0 * wf)
    ax.plot(wf, np.full_like(wf, costA), "o-", color="#1F77B4", lw=1.8,
            label="纯 A 成本（LP 最优）")
    ax.plot(wf, costB, "s--", color="#ED7D31", lw=1.6,
            label="纯 B 理论成本")
    ax.fill_between(wf, costA - 0.1, costA + 0.1, color="#1F77B4", alpha=0.15)
    ax.set_xticks(wf)
    ax.set_xticklabels([f"×{x:g}" for x in wf])
    ax.set_xlabel("等效体积权重 w 的缩放因子")
    ax.set_ylabel("成本（元）")
    ax.set_title("问题四：等效体积 w 敏感性（LP 最优恒为纯 A）")
    ax.set_ylim(0, 44)
    ax.grid(True, ls="--", alpha=0.3)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7", fontsize=9)
    ax.text(0.02, 0.96, f"w0=φ*_A/φ*_B≈{w0:.4f}；纯A成本 {costA:.2f} 元；"
                         "w 需 >0.0476 纯B才可能竞争（±20% 内不可能）",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#404040",
            bbox=dict(fc="white", alpha=0.9, ec="0.7", lw=0.5))
    C.save_fig(fig, os.path.join(FIG, "ch9_q4_w_sensitivity.png"))
    # 纯 B 外推不确定性
    sub = pb[pb["phiB"].isin([0.50, 0.55, 0.60])][["phiB", "NB", "M",
                                                   "p_hat", "ci_low",
                                                   "ci_up"]].copy()
    sub["达标(CI下界≥0.9)"] = sub["ci_low"] >= 0.90
    sub["phiB"] = (sub["phiB"] * 100).round(2)
    sub.to_csv(os.path.join(TBL, "ch9_q4_phiB_uncertainty.csv"), index=False,
               encoding="utf-8-sig")


def main():
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    sec1_q1()
    sec2_q2()
    sec3_q3()
    sec4_q4()
    print("ch9_analysis done")


if __name__ == "__main__":
    main()
