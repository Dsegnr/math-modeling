# -*- coding: utf-8 -*-
"""
问题二正式高精度驱动（新增脚本，不改动 q2_mc_probability.py）：
  - 相变区加密：0.5%~1.5%，其中 0.8%~1.2% 每 0.1% 一点，另加 1.3%/1.4% 支撑问题三拟合
  - 每点 M 可配（默认 3000）
  - 覆盖写入 output/tables/q2_probabilities.csv 与 data/processed/q2_mc_raw.csv
  - 重绘 q2 全部 4 张成品图（收敛图标注改为动态，消除原脚本硬编码）
  - 逐 φ 落盘 + 断点续跑：进程若被超时终止，已完成的 φ 不重跑
运行：python code/q2_high.py --m 3000 --workers 8
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import q2_mc_probability as q2
import common as C

# 相变区加密：0.8%~1.2% 每 0.1% 一点，另含 1.3%/1.4% 支撑问题三
PHIS_HIGH = [0.005, 0.006, 0.007, 0.008, 0.009, 0.010,
             0.011, 0.012, 0.013, 0.014, 0.015]


def fig_curve_high(prob_df):
    """p-φ 曲线（与 q2.fig_curve 同风格，N 标注交替上下、字号缩小防重叠）。"""
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = prob_df["phi_percent"]
    ax.errorbar(x, prob_df["p_hat"], yerr=[
        prob_df["p_hat"] - prob_df["ci_low"],
        prob_df["ci_up"] - prob_df["p_hat"]],
        fmt="o-", color="#C00000", capsize=4, lw=1.8, ms=5.5,
        label="蒙特卡洛估计 ±95% Wilson 区间")
    ax.axhline(0.90, ls="--", color="#4472C4", lw=1.5,
               label="可靠性目标 P=0.90")
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P")
    ax.set_title("介质 A 导通概率随体积分数的变化（C1 口径，高精度）")
    ax.grid(True, ls="--", alpha=0.35)
    ax.set_ylim(0, 1.08)
    ax.set_xticks(prob_df["phi_percent"].tolist())
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9)
    for k, (_, r) in enumerate(prob_df.iterrows()):
        off = 11 if k % 2 == 0 else -17
        va = "bottom" if off > 0 else "top"
        ax.annotate(f"N={int(r['N'])}", (r["phi_percent"], r["p_hat"]),
                    textcoords="offset points", xytext=(0, off), va=va,
                    fontsize=7, ha="center", color="#404040",
                    bbox=dict(fc="white", alpha=0.8, pad=1, ec="none"))
    ax.text(0.02, 0.03, "口径 C1：介质完全位于微构体内部",
            fontsize=9, color="#606060", transform=ax.transAxes)
    C.save_fig(fig, os.path.join(q2.FIG, "q2_p_phi_curve.png"))


def fig_convergence_dynamic(results, phi=0.010):
    """收敛曲线（标注随结果动态更新，修复原脚本硬编码 0.715/[0.669,0.757]）。"""
    C.setup_font()
    hits = np.array(results[phi], dtype=int)
    M = len(hits)
    cum = np.cumsum(hits) / np.arange(1, M + 1)
    ms = np.arange(1, M + 1)
    z = 1.96
    den = 1 + z * z / ms
    center = (cum + z * z / (2 * ms)) / den
    half = z * np.sqrt(cum * (1 - cum) / ms + z * z / (4 * ms * ms)) / den
    lo = np.clip(center - half, 0.0, 1.0)
    hi = np.clip(center + half, 0.0, 1.0)
    p_f, lo_f, hi_f = C.wilson(int(hits.sum()), M)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ms, cum, color="#C00000", lw=1.6, label=r"运行估计 $\hat{p}$")
    ax.fill_between(ms, lo, hi, color="#C00000", alpha=0.18,
                    label="95% Wilson 区间")
    ax.axhline(cum[-1], ls=":", color="#404040", lw=1,
               label=rf"最终估计 $\hat{{p}}$≈{cum[-1]:.3f}")
    ax.set_xlabel("蒙特卡洛样本量 M")
    ax.set_ylabel(r"导通概率估计 $\hat{p}$")
    ax.set_title(f"蒙特卡洛收敛性诊断（φ=1.00%，N={C.n_rods(phi)}，M={M}）",
                 fontsize=12)
    ax.grid(True, ls="--", alpha=0.35)
    ax.set_ylim(0, 1.05)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.text(0.98, 0.04,
            rf"最终 $\hat{{p}}$={p_f:.3f}，95% CI [{lo_f:.3f}, {hi_f:.3f}]",
            transform=ax.transAxes, ha="right", fontsize=9, color="#404040",
            bbox=dict(fc="white", alpha=0.85, pad=2, ec="0.7", lw=0.5))
    C.save_fig(fig, os.path.join(q2.FIG, "q2_convergence_1.00%.png"))


def load_existing(raw_path):
    """读取已有原始记录：返回 {phi: hits}，仅保留完整组（>=M）与残留组分离。"""
    if not os.path.exists(raw_path):
        return {}, {}
    raw = pd.read_csv(raw_path)
    complete, partial = {}, {}
    for phi, grp in raw.groupby("phi"):
        if len(grp) >= 0:  # 先按 phi 收集，是否完整由调用方按目标 M 判断
            complete[float(phi)] = grp["conduct"].astype(int).tolist()
    return complete, {}


def build_table(results):
    rows = []
    for phi in sorted(results):
        if not results[phi]:
            continue
        k = sum(results[phi])
        M = len(results[phi])
        p, lo, hi = C.wilson(k, M)
        rows.append({"phi": phi, "phi_percent": round(phi * 100, 2),
                     "N": C.n_rods(phi), "M": M, "conduct": k,
                     "p_hat": round(p, 4), "ci_low": round(lo, 4),
                     "ci_up": round(hi, 4)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=3000, help="每个 φ 的样本量")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()

    os.makedirs(q2.TBL, exist_ok=True)
    os.makedirs(q2.FIG, exist_ok=True)
    os.makedirs(q2.PROC, exist_ok=True)

    raw_path = os.path.join(q2.PROC, "q2_mc_raw.csv")
    if args.figures_only and os.path.exists(raw_path):
        raw = pd.read_csv(raw_path)
        results = {phi: raw.loc[raw["phi"] == phi, "conduct"].astype(int).tolist()
                   for phi in sorted(raw["phi"].unique())}
        prob_df = pd.read_csv(os.path.join(q2.TBL, "q2_probabilities.csv"))
        print("[q2_high] 复用已存 MC 结果，仅重绘图表")
    else:
        done, _ = load_existing(raw_path)
        pending = [phi for phi in PHIS_HIGH
                   if len(done.get(phi, [])) < args.m]
        print(f"[q2_high] 已完成 {len(PHIS_HIGH) - len(pending)}/{len(PHIS_HIGH)} 个 φ，"
              f"待跑 {len(pending)} 个", flush=True)
        t_all = time.time()
        for i, phi in enumerate(pending, 1):
            t0 = time.time()
            # 清掉该 φ 的残留行，避免重跑后重复计入
            if os.path.exists(raw_path):
                old = pd.read_csv(raw_path)
                old = old[old["phi"] != phi]
                if len(old):
                    old.to_csv(raw_path, index=False, encoding="utf-8-sig")
                else:
                    os.remove(raw_path)
            sub = q2.run_mc([phi], args.m, args.workers)
            done[phi] = sub[phi]
            # 追加写原始记录（保留已有完整组）
            rows = [{"phi": phi, "conduct": h} for h in sub[phi]]
            pd.DataFrame(rows).to_csv(raw_path, mode="a", header=not os.path.exists(raw_path),
                                      index=False, encoding="utf-8-sig")
            # 每次更新概率表，超时中断也不丢已完成点
            build_table(done).to_csv(os.path.join(q2.TBL, "q2_probabilities.csv"),
                                     index=False, encoding="utf-8-sig")
            print(f"[q2_high] φ={phi*100:.2f}% 完成 "
                  f"({i}/{len(pending)}，耗时 {time.time()-t0:.0f}s，"
                  f"累计 {time.time()-t_all:.0f}s)", flush=True)
        # 统一补全所有点（含历史完整点）后生成正式表
        for phi in PHIS_HIGH:
            if len(done.get(phi, [])) < args.m:
                done[phi] = done.get(phi, [])
        results = done
        prob_df = build_table(done)
        prob_df.to_csv(os.path.join(q2.TBL, "q2_probabilities.csv"),
                       index=False, encoding="utf-8-sig")
    print(prob_df.to_string(index=False))

    fig_curve_high(prob_df)
    fig_convergence_dynamic(results, phi=0.010)
    q2.fig_typical(results, phi=0.007)
    q2.fig_cluster_sizes()


if __name__ == "__main__":
    main()
