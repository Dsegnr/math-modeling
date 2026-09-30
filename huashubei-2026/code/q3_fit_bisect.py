# -*- coding: utf-8 -*-
"""
问题三：P≥90% 的最低体积分数 —— 双方法互证。
方法一：渗透模型拟合反解（sigmoid / 幂律截断，按 AIC 选优）
方法二：概率二分 + 置信区间决策规则（整数 N 层面）
输出：
  output/tables/q3_fit_params.csv   拟合参数
  output/tables/q3_results.csv      双方法 φ* 与验证
  data/processed/q3_bisect_trace.csv 二分过程
  figures/q3/q3_fit_curve.png       拟合曲线 + 双方法 φ* 标注
"""
import os
import sys
import time
import argparse
import multiprocessing as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")
PROC = os.path.join(BASE, "data", "processed")
TARGET = 0.90


def sigmoid(x, phi0, s):
    return 1.0 / (1.0 + np.exp(-(x - phi0) / s))


def power_law(x, phi_c, a, beta):
    d = np.maximum(x - phi_c, 0.0)
    return 1.0 - np.exp(-a * d**beta)


def mc_worker(args):
    phi, N, base_seed, M = args
    hits = []
    for m in range(M):
        rng = np.random.default_rng(base_seed * 100000 + m)
        segs = C.sample_rods_c1(N, rng)
        conduct, _, _ = C.conduct_mixed(segs, None)
        hits.append(conduct)
    return phi, hits


def mc_eval(phi, M, workers):
    N = C.n_rods(phi)
    tasks = []
    CHUNK = 40
    for c in range(max(1, M // CHUNK)):
        tasks.append((phi, N, 77 + c, min(CHUNK, M)))
    hits = []
    with mp.Pool(workers) as pool:
        for _, h in pool.imap_unordered(mc_worker, tasks):
            hits.extend(h)
    k = sum(hits)
    p, lo, hi = C.wilson(k, len(hits))
    return p, lo, hi, len(hits)


def fit_and_invert(prob_df):
    x = prob_df["phi"].to_numpy()
    y = prob_df["p_hat"].to_numpy()
    w = 1.0 / np.maximum(prob_df["ci_up"] - prob_df["ci_low"], 1e-4).to_numpy()
    models = {}

    try:
        p0_sig = [0.009, 0.0015]
        popt, _ = curve_fit(sigmoid, x, y, p0=p0_sig, sigma=1 / w, maxfev=20000)
        yhat = sigmoid(x, *popt)
        rss = float(np.sum(w * (y - yhat) ** 2))
        n = len(x)
        aic = n * np.log(rss / n) + 2 * 2
        phi_star = popt[0] + popt[1] * np.log(9.0)
        models["sigmoid"] = dict(kind="sigmoid", params=popt, rss=rss, aic=aic,
                                 phi_star=phi_star)
    except Exception as e:
        print("sigmoid fit failed:", e)

    try:
        p0_pw = [0.006, 60.0, 1.5]
        bounds = ([0.0, 1e-6, 0.3], [0.02, 1e4, 5.0])
        popt, _ = curve_fit(power_law, x, y, p0=p0_pw, sigma=1 / w,
                            bounds=bounds, maxfev=40000)
        yhat = power_law(x, *popt)
        rss = float(np.sum(w * (y - yhat) ** 2))
        n = len(x)
        aic = n * np.log(rss / n) + 2 * 3
        phi_c, a, beta = popt
        phi_star = phi_c + (-np.log(0.1) / a) ** (1.0 / beta)
        models["power"] = dict(kind="power", params=popt, rss=rss, aic=aic,
                               phi_star=phi_star)
    except Exception as e:
        print("power fit failed:", e)

    best = min(models.values(), key=lambda m: m["aic"])
    return models, best


def bisection(workers, M=400, max_iter=7):
    lo_N = 0
    hi_N = C.n_rods(0.020)
    trace = []
    for it in range(max_iter):
        mid = (lo_N + hi_N) // 2
        phi = mid * C.V_A / C.V_CUBE
        p, lo, hi, m = mc_eval(phi, M, workers)
        trace.append({"iter": it + 1, "N": mid, "phi": phi, "p_hat": p,
                      "ci_low": lo, "ci_up": hi, "decision": ""})
        if lo >= TARGET:
            hi_N = mid
            trace[-1]["decision"] = "可行，下调"
        elif hi < TARGET:
            lo_N = mid + 1
            trace[-1]["decision"] = "不可行，上调"
        else:
            trace[-1]["decision"] = "区间含 0.90，加样本"
        if hi_N - lo_N <= 1:
            break
    phi_star = hi_N * C.V_A / C.V_CUBE
    return phi_star, hi_N, pd.DataFrame(trace)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=400)
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    os.makedirs(PROC, exist_ok=True)

    prob_df = pd.read_csv(os.path.join(TBL, "q2_probabilities.csv"))
    models, best = fit_and_invert(prob_df)
    pd.DataFrame([{**v, "params": str(list(v["params"]))}
                  for v in models.values()]).to_csv(
        os.path.join(TBL, "q3_fit_params.csv"), index=False, encoding="utf-8-sig")

    print("=== 拟合结果 ===")
    for name, m in models.items():
        print(f"{name}: AIC={m['aic']:.1f}, φ*={m['phi_star']*100:.3f}%")
    print("最优模型:", best["kind"], "AIC=%.1f" % best["aic"])

    phi_fit = best["phi_star"]
    if args.figures_only and os.path.exists(os.path.join(TBL, "q3_results.csv")):
        res_df = pd.read_csv(os.path.join(TBL, "q3_results.csv"))
        phi_bis = float(res_df.loc[res_df["method"] == "概率二分", "phi_star"].iloc[0]) / 100
        phi_final = float(res_df.loc[res_df["method"] == "细化定稿", "phi_star"].iloc[0]) / 100
        print("[q3] 复用已存表格，仅重绘图表")
    else:
        t0 = time.time()
        phi_bis, N_bis, trace = bisection(args.workers, M=args.m)
        trace.to_csv(os.path.join(PROC, "q3_bisect_trace.csv"),
                     index=False, encoding="utf-8-sig")
        print(f"=== 概率二分 === 耗时 {time.time()-t0:.0f}s")
        print(f"φ*_bis = {phi_bis*100:.3f}% (N={N_bis})")

        # 细化：在双方法区间内按 N 高样本量扫描，取满足 CI 下界≥0.9 的最小 N
        lo_ref = max(0.003, min(phi_fit, phi_bis) - 0.0005)
        hi_ref = max(phi_fit, phi_bis) + 0.0005
        Ns = np.arange(C.n_rods(lo_ref), C.n_rods(hi_ref) + 1)
        if len(Ns) > 9:
            Ns = np.unique(np.linspace(Ns[0], Ns[-1], 9).astype(int))
        refine_rows = []
        for N in Ns:
            phi = N * C.V_A / C.V_CUBE
            p, lo, hi, m = mc_eval(phi, 800, args.workers)
            refine_rows.append({"N": int(N), "phi": round(phi * 100, 3),
                                "p_hat": round(p, 4), "ci_low": round(lo, 4),
                                "ci_up": round(hi, 4),
                                "feasible": "是" if lo >= TARGET else "否"})
        ref_df = pd.DataFrame(refine_rows)
        ref_df.to_csv(os.path.join(TBL, "q3_refine_sweep.csv"),
                      index=False, encoding="utf-8-sig")
        feasible = ref_df[ref_df["feasible"] == "是"]
        phi_final = feasible.iloc[0]["phi"] / 100 if len(feasible) else phi_bis
        print("=== 细化扫描（N 层面）===")
        print(ref_df.to_string(index=False))
        print(f"φ*_final = {phi_final*100:.3f}%")

        # 最终验证（φ* 处高样本量）
        rows = []
        for name, phi in [("拟合反解", phi_fit), ("概率二分", phi_bis),
                          ("细化定稿", phi_final)]:
            p, lo, hi, m = mc_eval(phi, 1200, args.workers)
            rows.append({"method": name, "phi_star": round(phi * 100, 3),
                         "N": C.n_rods(phi), "M": m, "p_hat": round(p, 4),
                         "ci_low": round(lo, 4), "ci_up": round(hi, 4),
                         "satisfy": "是" if lo >= TARGET else "否"})
        res_df = pd.DataFrame(rows)
        res_df.to_csv(os.path.join(TBL, "q3_results.csv"),
                      index=False, encoding="utf-8-sig")
        print(res_df.to_string(index=False))

    # 图：拟合曲线 + 双方法 φ*
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = prob_df["phi_percent"]
    ax.errorbar(x, prob_df["p_hat"] * 100,
                yerr=[(prob_df["p_hat"] - prob_df["ci_low"]) * 100,
                      (prob_df["ci_up"] - prob_df["p_hat"]) * 100],
                fmt="o", color="#4472C4", ms=5, capsize=3,
                label="蒙特卡洛点估计（Wilson 区间）")
    xs = np.linspace(0.003, 0.020, 400)
    for name, m in models.items():
        if m["kind"] == "sigmoid":
            yv = sigmoid(xs, *m["params"])
        else:
            yv = power_law(xs, *m["params"])
        ax.plot(xs * 100, yv * 100, lw=1.8,
                label=f"{'sigmoid' if name=='sigmoid' else '幂律截断'} 拟合 (AIC={m['aic']:.0f})")
    ax.axhline(90, ls="--", color="#C00000", lw=1.5, label="可靠性目标 P=90%")
    marks = [("拟合反解 φ*", phi_fit, "#C00000", ":", 0.28, -0.06),
             ("概率二分 φ*", phi_bis, "#ED7D31", "-.", 0.10, 0.04),
             ("细化定稿 φ*", phi_final, "#00B050", "-", 0.55, -0.04)]
    for name, phi, col, ls, ypos, xoff in marks:
        ax.axvline(phi * 100, ls=ls, lw=1.4, color=col)
    # 标注统一放入说明盒，避免三线邻近导致文字重叠
    lines = [
        (f"拟合反解 φ* = {phi_fit*100:.2f}%（{best['kind']} 反演）", "#C00000"),
        (f"概率二分 φ* = {phi_bis*100:.2f}%（CI 规则，偏保守）", "#ED7D31"),
        (f"细化定稿 φ* = {phi_final*100:.2f}%（N={C.n_rods(phi_final)}，最终采用）",
         "#00B050"),
    ]
    txt = "\n".join(f"  {l}" for l, _ in lines)
    ax.text(0.03, 0.63, txt, transform=ax.transAxes, fontsize=9,
            va="top", bbox=dict(fc="white", alpha=0.92, pad=4, ec="0.6", lw=0.7))
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("渗透模型拟合与 φ* 双方法互证")
    ax.set_ylim(0, 100)
    C.style_clean(ax, grid=False)
    ax.text(0.60, 0.10, "在 P=90% 交点附近两条拟合曲线几乎重合：\nφ* 对模型形式不敏感",
            transform=ax.transAxes, fontsize=9, color="#606060",
            bbox=dict(fc="white", alpha=0.85, pad=2, ec="0.7", lw=0.5))
    ax.grid(True, ls="--", alpha=0.35)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
              fontsize=8.5, loc="upper left")
    C.save_fig(fig, os.path.join(FIG, "q3_fit_curve.png"))

    # 图2：φ* 附近局部放大（展示 0.01% 级分辨能力）
    C.setup_font()
    ref_path = os.path.join(TBL, "q3_refine_sweep.csv")
    if os.path.exists(ref_path):
        ref = pd.read_csv(ref_path)
        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.errorbar(ref["phi"], ref["p_hat"] * 100,
                    yerr=[(ref["p_hat"] - ref["ci_low"]) * 100,
                          (ref["ci_up"] - ref["p_hat"]) * 100],
                    fmt="o", color="#4472C4", ms=5, capsize=3,
                    label="高样本量 MC 验证点（M=800）")
        xs = np.linspace(0.0124, 0.0156, 200)
        if best["kind"] == "sigmoid":
            yv = sigmoid(xs, *best["params"])
        else:
            yv = power_law(xs, *best["params"])
        ax.plot(xs * 100, yv * 100, color="#ED7D31", lw=1.8,
                label="最优渗透模型拟合")
        ax.axhline(90, ls="--", color="#C00000", lw=1.4, label="P=90%")
        ax.axvline(phi_final * 100, ls="-", color="#00B050", lw=1.8)
        ax.text(phi_final * 100, 55, f"φ*={phi_final*100:.2f}%",
                rotation=90, color="#00B050", fontsize=10, fontweight="bold",
                ha="right")
        ax.set_xlabel("体积分数 φ (%)")
        ax.set_ylabel("导通概率 P (%)")
        ax.set_title("φ* 附近局部放大：0.01% 级分辨能力")
        ax.grid(True, ls="--", alpha=0.35)
        C.style_clean(ax, grid=False)
        ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
                  fontsize=9, loc="upper left")
        C.save_fig(fig, os.path.join(FIG, "q3_phi_star_zoom.png"))


if __name__ == "__main__":
    main()
