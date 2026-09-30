# -*- coding: utf-8 -*-
"""
问题三正式高精度驱动（新增脚本，不改动 q3_fit_bisect.py）：
  - 读取问题二最终概率表（q2_high.py 产物）
  - 渗透模型拟合反解（AIC 选优）
  - 概率二分 M=bisect_m（默认 3000）
  - φ* 邻域 N 层面细化扫描 M=refine_m（默认 3000），取 CI 下界≥0.9 的最小 N
  - 最终验证：拟合/二分各 M=verify_m；细化定稿 3 个随机种子 × verify_m 合并 Wilson
  - 覆盖写入 q3_fit_params / q3_bisect_trace / q3_refine_sweep / q3_results
  - 新增 q3_seed_verify.csv（逐种子明细）
  - 重绘 q3 两张成品图（标注动态，消除原脚本硬编码 φ*）
运行：python code/q3_high_verify.py --workers 8
"""
import os
import sys
import time
import argparse
import multiprocessing as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import q3_fit_bisect as q3
import common as C

TARGET = 0.90
SEEDS_FINAL = [77, 2026, 31415]


def mc_eval_seed(phi, M, workers, base_seed=77):
    """与 q3.mc_eval 等价，但允许指定随机种子基。"""
    N = C.n_rods(phi)
    tasks = []
    CHUNK = 40
    for c in range(max(1, M // CHUNK)):
        tasks.append((phi, N, base_seed + c, min(CHUNK, M)))
    hits = []
    with mp.Pool(workers) as pool:
        for _, h in pool.imap_unordered(q3.mc_worker, tasks):
            hits.extend(h)
    k = sum(hits)
    p, lo, hi = C.wilson(k, len(hits))
    return p, lo, hi, len(hits), hits


def fig_fit_curve(prob_df, models, best, phi_fit, phi_bis, phi_final):
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
            yv = q3.sigmoid(xs, *m["params"])
        else:
            yv = q3.power_law(xs, *m["params"])
        ax.plot(xs * 100, yv * 100, lw=1.8,
                label=f"{'sigmoid' if name == 'sigmoid' else '幂律截断'} 拟合 (AIC={m['aic']:.0f})")
    ax.axhline(90, ls="--", color="#C00000", lw=1.5, label="可靠性目标 P=90%")
    marks = [("拟合反解 φ*", phi_fit, "#C00000", ":"),
             ("概率二分 φ*", phi_bis, "#ED7D31", "-."),
             ("细化定稿 φ*", phi_final, "#00B050", "-")]
    for name, phi, col, ls in marks:
        ax.axvline(phi * 100, ls=ls, lw=1.4, color=col)
    lines = [
        (f"拟合反解 φ* = {phi_fit*100:.2f}%（{best['kind']}，AIC={best['aic']:.0f}）", "#C00000"),
        (f"概率二分 φ* = {phi_bis*100:.2f}%（CI 规则，偏保守）", "#ED7D31"),
        (f"细化定稿 φ* = {phi_final*100:.2f}%（N={C.n_rods(phi_final)}，3 种子终验）", "#00B050"),
    ]
    txt = "\n".join(f"  {l}" for l, _ in lines)
    ax.text(0.03, 0.63, txt, transform=ax.transAxes, fontsize=9,
            va="top", bbox=dict(fc="white", alpha=0.92, pad=4, ec="0.6", lw=0.7))
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("渗透模型拟合与 φ* 双方法互证（高精度）")
    ax.set_ylim(0, 100)
    C.style_clean(ax, grid=False)
    ax.text(0.60, 0.10, "在 P=90% 交点附近两条拟合曲线几乎重合：\nφ* 对模型形式不敏感",
            transform=ax.transAxes, fontsize=9, color="#606060",
            bbox=dict(fc="white", alpha=0.85, pad=2, ec="0.7", lw=0.5))
    ax.grid(True, ls="--", alpha=0.35)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
              fontsize=8.5, loc="upper left")
    C.save_fig(fig, os.path.join(q3.FIG, "q3_fit_curve.png"))


def fig_zoom(ref_df, best, phi_final, phi_bis, phi_fit):
    C.setup_font()
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.errorbar(ref_df["phi"], ref_df["p_hat"] * 100,
                yerr=[(ref_df["p_hat"] - ref_df["ci_low"]) * 100,
                      (ref_df["ci_up"] - ref_df["p_hat"]) * 100],
                fmt="o", color="#4472C4", ms=5, capsize=3,
                label=f"高样本量 MC 验证点（M={int(ref_df['M'].iloc[0])}）")
    lo_x = min(ref_df["phi"].min(), phi_final * 100) - 0.12
    hi_x = max(ref_df["phi"].max(), phi_bis * 100) + 0.12
    xs = np.linspace(lo_x, hi_x, 200) / 100
    if best["kind"] == "sigmoid":
        yv = q3.sigmoid(xs, *best["params"])
    else:
        yv = q3.power_law(xs, *best["params"])
    ax.plot(xs * 100, yv * 100, color="#ED7D31", lw=1.8,
            label="最优渗透模型拟合")
    ax.axhline(90, ls="--", color="#C00000", lw=1.4, label="P=90%")
    ax.axvline(phi_final * 100, ls="-", color="#00B050", lw=1.8)
    ax.text(phi_final * 100, 55, f"φ*={phi_final*100:.2f}%",
            rotation=90, color="#00B050", fontsize=10, fontweight="bold",
            ha="right")
    ax.set_xlabel("体积分数 φ (%)")
    ax.set_ylabel("导通概率 P (%)")
    ax.set_title("φ* 附近局部放大：0.01% 级分辨能力（高精度）")
    ax.grid(True, ls="--", alpha=0.35)
    C.style_clean(ax, grid=False)
    ax.legend(frameon=True, framealpha=0.92, edgecolor="0.7",
              fontsize=9, loc="upper left")
    C.save_fig(fig, os.path.join(q3.FIG, "q3_phi_star_zoom.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bisect-m", type=int, default=3000, help="概率二分每点评测样本量")
    ap.add_argument("--refine-m", type=int, default=3000, help="细化扫描每点评测样本量")
    ap.add_argument("--verify-m", type=int, default=3000, help="终验每种子样本量")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true",
                    help="复用已完成阶段（二分/细化/种子），断点续跑")
    ap.add_argument("--figures-only", action="store_true",
                    help="复用已存表格只重绘图表")
    args = ap.parse_args()
    os.makedirs(q3.TBL, exist_ok=True)
    os.makedirs(q3.FIG, exist_ok=True)

    prob_df = pd.read_csv(os.path.join(q3.TBL, "q2_probabilities.csv"))
    models, best = q3.fit_and_invert(prob_df)
    pd.DataFrame([{**v, "params": str(list(v["params"]))}
                  for v in models.values()]).to_csv(
        os.path.join(q3.TBL, "q3_fit_params.csv"), index=False,
        encoding="utf-8-sig")
    print("=== 拟合结果 ===")
    for name, m in models.items():
        print(f"{name}: AIC={m['aic']:.1f}, φ*={m['phi_star']*100:.3f}%")
    print("最优模型:", best["kind"], "AIC=%.1f" % best["aic"])
    phi_fit = best["phi_star"]

    if args.figures_only and os.path.exists(os.path.join(q3.TBL, "q3_results.csv")):
        res_df = pd.read_csv(os.path.join(q3.TBL, "q3_results.csv"))
        phi_bis = float(res_df.loc[res_df["method"] == "概率二分", "phi_star"].iloc[0]) / 100
        phi_final = float(res_df.loc[res_df["method"] == "细化定稿", "phi_star"].iloc[0]) / 100
        ref_df = pd.read_csv(os.path.join(q3.TBL, "q3_refine_sweep.csv"))
        print("[q3_high] 复用已存表格，仅重绘图表")
    else:
        state_path = os.path.join(q3.TBL, "q3_high_state.csv")
        state = {}
        if args.resume and os.path.exists(state_path):
            st = pd.read_csv(state_path)
            state = dict(zip(st["key"], st["value"]))
            print("[q3_high] 读取续跑状态:", state, flush=True)

        if args.resume and "phi_bis" in state and \
                int(float(state.get("M_bis", 0))) >= args.bisect_m:
            phi_bis = float(state["phi_bis"])
            N_bis = int(state["N_bis"])
            trace = pd.read_csv(os.path.join(q3.PROC, "q3_bisect_trace.csv"))
            print(f"[q3_high] 复用二分结果 φ*_bis={phi_bis*100:.3f}% (N={N_bis})",
                  flush=True)
        else:
            t0 = time.time()
            phi_bis, N_bis, trace = q3.bisection(args.workers,
                                                 M=args.bisect_m, max_iter=7)
            trace.to_csv(os.path.join(q3.PROC, "q3_bisect_trace.csv"),
                         index=False, encoding="utf-8-sig")
            pd.DataFrame([
                {"key": "phi_bis", "value": phi_bis},
                {"key": "N_bis", "value": N_bis},
                {"key": "M_bis", "value": args.bisect_m},
                {"key": "phi_fit", "value": phi_fit},
                {"key": "M_fit", "value": args.verify_m},
            ]).to_csv(state_path, index=False, encoding="utf-8-sig")
            print(f"=== 概率二分 === 耗时 {time.time()-t0:.0f}s")
            print(f"φ*_bis = {phi_bis*100:.3f}% (N={N_bis})")

        lo_ref = max(0.003, min(phi_fit, phi_bis) - 0.0005)
        hi_ref = max(phi_fit, phi_bis) + 0.0005
        Ns = np.arange(C.n_rods(lo_ref), C.n_rods(hi_ref) + 1)
        if len(Ns) > 9:
            Ns = np.unique(np.linspace(Ns[0], Ns[-1], 9).astype(int))
        ref_path = os.path.join(q3.TBL, "q3_refine_sweep.csv")
        ref_dict = {}
        if args.resume and os.path.exists(ref_path):
            old = pd.read_csv(ref_path)
            for _, r in old.iterrows():
                if int(r["N"]) in Ns and int(r["M"]) >= args.refine_m:
                    ref_dict[int(r["N"])] = dict(r)
        t_ref = time.time()
        for N in Ns:
            if N in ref_dict:
                print(f"  细化 N={int(N)} 复用已有", flush=True)
                continue
            phi = N * C.V_A / C.V_CUBE
            p, lo, hi, m, _ = mc_eval_seed(phi, args.refine_m, args.workers, 77)
            ref_dict[int(N)] = {"N": int(N), "phi": round(phi * 100, 3),
                                "p_hat": round(p, 4), "ci_low": round(lo, 4),
                                "ci_up": round(hi, 4), "M": m,
                                "feasible": "是" if lo >= TARGET else "否"}
            pd.DataFrame(list(ref_dict.values())).sort_values("N").to_csv(
                ref_path, index=False, encoding="utf-8-sig")
            print(f"  细化 N={int(N)} φ={phi*100:.3f}% p_hat={p:.4f} "
                  f"CI=[{lo:.4f},{hi:.4f}] 耗时 {time.time()-t_ref:.0f}s", flush=True)
        ref_df = pd.DataFrame(list(ref_dict.values())).sort_values("N") \
            .reset_index(drop=True)
        feasible = ref_df[ref_df["feasible"] == "是"]
        phi_final = feasible.iloc[0]["phi"] / 100 if len(feasible) else phi_bis
        print("=== 细化扫描（N 层面，M=%d）===" % args.refine_m)
        print(ref_df.to_string(index=False))
        print(f"φ*_final = {phi_final*100:.3f}%")

        rows = []
        p, lo, hi, m, _ = mc_eval_seed(phi_fit, args.verify_m, args.workers, 77)
        rows.append({"method": "拟合反解", "phi_star": round(phi_fit * 100, 3),
                     "N": C.n_rods(phi_fit), "M": m, "p_hat": round(p, 4),
                     "ci_low": round(lo, 4), "ci_up": round(hi, 4),
                     "satisfy": "是" if lo >= TARGET else "否"})
        p, lo, hi, m, _ = mc_eval_seed(phi_bis, args.verify_m, args.workers, 77)
        rows.append({"method": "概率二分", "phi_star": round(phi_bis * 100, 3),
                     "N": C.n_rods(phi_bis), "M": m, "p_hat": round(p, 4),
                     "ci_low": round(lo, 4), "ci_up": round(hi, 4),
                     "satisfy": "是" if lo >= TARGET else "否"})
        seed_path = os.path.join(q3.TBL, "q3_seed_verify.csv")
        seed_rows = []
        if args.resume and os.path.exists(seed_path):
            old = pd.read_csv(seed_path)
            for _, r in old.iterrows():
                if int(r["seed"]) in SEEDS_FINAL and \
                        int(r["M"]) >= args.verify_m:
                    seed_rows.append(dict(r))
        done_seeds = {int(r["seed"]) for r in seed_rows}
        for seed in SEEDS_FINAL:
            if seed in done_seeds:
                print(f"  种子 {seed} 复用已有", flush=True)
                continue
            p, lo, hi, m, hits = mc_eval_seed(phi_final, args.verify_m,
                                              args.workers, seed)
            seed_rows.append({"method": "细化定稿", "seed": seed,
                              "phi": round(phi_final * 100, 3),
                              "N": C.n_rods(phi_final), "M": m,
                              "conduct": int(sum(hits)),
                              "p_hat": round(p, 4), "ci_low": round(lo, 4),
                              "ci_up": round(hi, 4)})
            pd.DataFrame(seed_rows).to_csv(seed_path, index=False,
                                           encoding="utf-8-sig")
            print(f"  种子 {seed} 完成 p_hat={p:.4f}", flush=True)
        k = int(sum(r["conduct"] for r in seed_rows))
        M_all = int(sum(r["M"] for r in seed_rows))
        p, lo, hi = C.wilson(k, M_all)
        rows.append({"method": "细化定稿", "phi_star": round(phi_final * 100, 3),
                     "N": C.n_rods(phi_final), "M": M_all, "p_hat": round(p, 4),
                     "ci_low": round(lo, 4), "ci_up": round(hi, 4),
                     "satisfy": "是" if lo >= TARGET else "否"})
        res_df = pd.DataFrame(rows)
        res_df.to_csv(os.path.join(q3.TBL, "q3_results.csv"),
                      index=False, encoding="utf-8-sig")
        print(res_df.to_string(index=False))

    fig_fit_curve(prob_df, models, best, phi_fit, phi_bis, phi_final)
    fig_zoom(ref_df, best, phi_final, phi_bis, phi_fit)


if __name__ == "__main__":
    main()
