"""
分析类图与表（按当前冻结方案重做）
  fig_q4_cert_structure  证书结构与覆盖能力曲线（替代过时的 19/55 点角隙对照图）
  fig_case_space         演练案例空间覆盖（源数 x 全向/定向构成）
  fig_version_timeline   优化历程（各版本平均定位清除时间）
  tab_practice_summary   全部演练局的时间构成（自动从归档日志生成）
  tab_case_space / tab_version_compare
"""
import os
import re
import csv
import json
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

import q4_time_decomp as TD

BASE = os.path.dirname(os.path.abspath(__file__))
FIGD = os.path.join(BASE, "figures")
ARCH = os.path.join(BASE, "_scratch", "archive")
TABD = os.path.join(BASE, "output", "tables")
SIMD = r"<行为日志目录：请替换为本地路径>"
os.makedirs(FIGD, exist_ok=True)
os.makedirs(TABD, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300
ARENA = 1800.0
C1, C2, C3, C4, C5 = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59", "#f79646"


def save(fig, name):
    for e in ("png", "pdf"):
        fig.savefig(os.path.join(FIGD, "%s.%s" % (name, e)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig]", name, flush=True)


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def fig_cert_structure():
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    W = [tuple(map(float, p)) for p in d["waypoints"]]
    ncert = int(d["n_cert"])
    X, Y = grid(20.0)
    TH = np.arange(0.0, 360.0, 10.0)
    cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
    best = np.zeros((len(X), len(TH)), dtype=np.float32)
    angs = []
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6))
    ax = axes[0]
    ax.plot([q[0] for q in W[:ncert]], [q[1] for q in W[:ncert]], "o-", ms=5.5, lw=1.2,
            color=C1, label="证书段（%d 点，巡回 %.1f km）" % (ncert, d.get("cert_len_m", 0) / 1000.0))
    ax.plot([q[0] for q in W[ncert:]], [q[1] for q in W[ncert:]], "o", ms=3.4, mfc="white",
            mec="0.6", label="L2/L3 补给点（%d 点）" % (len(W) - ncert))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.2, ls="--"))
    ax.add_patch(Circle((0, 0), 1000, fill=False, ec=C4, lw=1.0, ls=":"))
    ax.add_patch(Circle((0, 0), 1900, fill=False, ec=C2, lw=1.0, ls=":"))
    ax.annotate("内环约 1000 m：中半径源朝外波束 / 圆心可测",
                xy=(0.03, 0.20), xycoords="axes fraction", fontsize=8.4, color=C4,
                bbox=dict(fc="white", ec=C4, alpha=0.9, lw=0.8))
    ax.annotate("外环约 1900 m > 1800：边界朝外源只能从外侧捕获",
                xy=(0.03, 0.13), xycoords="axes fraction", fontsize=8.4, color=C2,
                bbox=dict(fc="white", ec=C2, alpha=0.9, lw=0.8))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("(a) 问题四证书结构：双环为必需")
    ax.legend(loc="upper left", fontsize=8.4, framealpha=0.95)
    ax.grid(alpha=0.2)
    for k in range(1, len(W) + 1):
        w = W[k - 1]
        dx, dy = w[0] - X, w[1] - Y
        dd = np.sqrt(dx * dx + dy * dy)
        vis = dd <= 1000.0
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        ok = vis[:, None] & (diff <= 90.0)
        cnt += ok.astype(np.int16)
        if k <= 40:
            a0 = np.degrees(np.arctan2(dy, dx))
            for a1, o1 in angs:
                both = ok & o1
                if not np.any(both):
                    continue
                df = np.abs(((a1 - a0) + 180.0) % 360.0 - 180.0)
                angij = np.where(df > 90.0, 180.0 - df, df)[:, None]
                best = np.where(both & (angij > best), angij.astype(np.float32), best)
            angs.append((a0, ok))
    ks, l1, l2, l3 = [], [], [], []
    for k in (13, 31, 50, len(W)):
        ks.append(k)
    cur = np.zeros((len(X), len(TH)), dtype=np.int16)
    curbest = np.zeros((len(X), len(TH)), dtype=np.float32)
    pool = []
    res = {}
    for k in range(1, len(W) + 1):
        w = W[k - 1]
        dx, dy = w[0] - X, w[1] - Y
        dd = np.sqrt(dx * dx + dy * dy)
        vis = dd <= 1000.0
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        ok = vis[:, None] & (diff <= 90.0)
        cur += ok.astype(np.int16)
        a0 = np.degrees(np.arctan2(dy, dx))
        for a1, o1 in pool:
            both = ok & o1
            if not np.any(both):
                continue
            df = np.abs(((a1 - a0) + 180.0) % 360.0 - 180.0)
            angij = np.where(df > 90.0, 180.0 - df, df)[:, None]
            curbest = np.where(both & (angij > curbest), angij.astype(np.float32), curbest)
        pool.append((a0, ok))
        if k in ks:
            res[k] = (100.0 * np.count_nonzero(cur >= 1) / cur.size,
                      100.0 * np.count_nonzero(cur >= 2) / cur.size,
                      100.0 * np.count_nonzero((cur >= 2) & (curbest >= 30.0)) / cur.size)
    ax = axes[1]
    ax.plot(ks, [res[k][0] for k in ks], "-o", color=C1, ms=5, label="L1 必被检出")
    ax.plot(ks, [res[k][1] for k in ks], "--s", color=C2, ms=5, label="L2 可见点 ≥2")
    ax.plot(ks, [res[k][2] for k in ks], ":^", color=C4, ms=5, label="L3 交会角 ≥30°")
    ax.axvline(ncert, color="0.4", ls="--", lw=1.0)
    ax.annotate("证书段 %d 点" % ncert, xy=(ncert, res[ncert][0]), xytext=(ncert + 3, 90),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="0.4"))
    ax.set_xlabel("累计航点数（证书段优先）")
    ax.set_ylabel("全域 (位置×朝向) 覆盖率 / %")
    ax.set_ylim(45, 102)
    ax.set_title("(b) 覆盖能力随航点数（20 m×10° 网格）")
    ax.legend(loc="lower right", fontsize=8.6, framealpha=0.95)
    ax.grid(alpha=0.25)
    fig.suptitle("问题四证书：结构与「必检出—可定位」两级覆盖", y=1.02, fontsize=12.5)
    save(fig, "fig_q4_cert_structure")
    with open(os.path.join(TABD, "tab_l2l3_audit.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["航点集合", "累计航点数", "L1 必检出 / %", "L2 可见点≥2 / %", "L3 交会角≥30° / %"])
        tag = {13: "内环 13 点", 31: "证书段（内环 13 + 外环 18）", 50: "证书段 + 前 19 个补给点",
               len(W): "证书段 + 全部 50 个补给点"}
        for k in ks:
            w.writerow([tag.get(k, "前 %d 点" % k), k, round(res[k][0], 2),
                        round(res[k][1], 2), round(res[k][2], 2)])
    print("  [tab] tab_l2l3_audit.csv", flush=True)


def fig_case_space():
    q3, q4 = [], []
    for prob, box in ((3, q3), (4, q4)):
        for f in glob.glob(os.path.join(SIMD, "practice-p%d-*.result.json" % prob)):
            try:
                j = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            box.append((j["jammer_count"], j.get("directional_jammer_count", 0), j["case_code"]))
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    ax = axes[0]
    ns = [n for n, _, _ in q3]
    ax.hist(ns, bins=np.arange(9.5, 17.5, 1), color=C1, rwidth=0.7)
    for k in sorted(set(ns)):
        ax.text(k, ns.count(k) + 0.15, str(ns.count(k)), ha="center", fontsize=9)
    ax.set_xticks(range(10, 17))
    ax.set_xlabel("案例干扰源个数")
    ax.set_ylabel("局数")
    ax.set_title("(a) 问题三：%d 局演练，源数覆盖 10~16" % len(q3))
    ax.grid(alpha=0.25, axis="y")
    ax = axes[1]
    for n, nd, code in sorted(q4):
        ax.plot([n], [nd / n * 100.0], "o", ms=8, color=C2, alpha=0.75)
    ax.axhline(50, color="0.5", ls=":", lw=1.1)
    ax.annotate("全定向（0/11）与几乎全全向（14/1）两类极端均已实测且 100%% 清除",
                xy=(0.03, 0.05), xycoords="axes fraction", fontsize=8.6,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_xticks(range(10, 17))
    ax.set_xlabel("案例干扰源个数")
    ax.set_ylabel("定向源占比 / %")
    ax.set_ylim(-5, 105)
    ax.set_title("(b) 问题四：%d 局演练，构成覆盖全部区间" % len(q4))
    ax.grid(alpha=0.25)
    fig.suptitle("演练案例空间覆盖（数据来自模拟器报告的真值）", y=1.02, fontsize=12.5)
    save(fig, "fig_case_space")
    with open(os.path.join(TABD, "tab_case_space.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["问题", "源数", "全向", "定向", "案例编码"])
        for n, nd, code in sorted(q3):
            w.writerow([3, n, n - nd, nd, code])
        for n, nd, code in sorted(q4):
            w.writerow([4, n, n - nd, nd, code])
    print("  [tab] tab_case_space.csv", flush=True)


def fig_version():
    ver = [("v1 19/55 点\n+ 启发式终止", 651, 830),
           ("v2 建证集\n+ 证书终止", 640, 700),
           ("v5 顺路清除", 408, 620),
           ("v7 单环 990×15", 343, 560),
           ("v12 三条才开清", 263, 500),
           ("v17 单观测补测", 296, 490)]
    fig, ax = plt.subplots(figsize=(10.6, 4.9))
    x = np.arange(len(ver))
    ax.plot(x, [v[1] for v in ver], "-o", lw=2.0, ms=8, color=C1, label="问题三 平均 / (s/源)")
    ax.plot(x, [v[2] for v in ver], "--s", lw=2.0, ms=7, color=C2, label="问题四 平均 / (s/源)")
    for i, v in enumerate(ver):
        ax.text(i, v[1] - 38, "%.0f" % v[1], ha="center", fontsize=9, color=C1)
        ax.text(i, v[2] + 18, "%.0f" % v[2], ha="center", fontsize=9, color=C2)
    ax.set_xticks(x)
    ax.set_xticklabels([v[0] for v in ver], fontsize=8.6)
    ax.set_ylabel("平均定位清除时间 / (s/源)")
    ax.set_title("优化历程：平均定位清除时间（演练实测口径）")
    ax.legend(fontsize=9.5)
    ax.grid(alpha=0.25, axis="y")
    ax.set_ylim(0, 900)
    save(fig, "fig_version_timeline")
    keys = ["初始（19/55 点 + 启发式终止）", "建证集 + 证书式终止", "最优绕道点顺路清除",
            "单环 990 m×15 建证集", "累计 ≥3 条示向度才开清 + 对角试探点", "单观测主动补测 + 健壮性修复"]
    with open(os.path.join(TABD, "tab_version_compare.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["版本", "问题三平均 / (s/源)", "问题四平均 / (s/源)", "关键改动"])
        for (lab, a, b), kk in zip(ver, keys):
            w.writerow([kk, a, b, lab.replace("\n", " ")])
    print("  [tab] tab_version_compare.csv", flush=True)


def tab_practice():
    files = [f for f in sorted(os.listdir(ARCH))
             if re.match(r"^(practice|stress|baseline)_", f) and f.endswith(".json")]
    rows = []
    for f in files:
        try:
            rows.append(TD.decompose(os.path.join(ARCH, f)))
        except Exception:
            continue
    with open(os.path.join(TABD, "tab_practice_summary.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["日志", "源数", "虚拟时间/s", "平均/(s/源)", "移动/s", "检测/s", "切频/s", "清除/s",
                    "measure次数", "clear成功", "clear失败"])
        for r in rows:
            ns = max(r["n_src"], 1)
            w.writerow([r["file"], r["n_src"], round(r["vt"], 1), round(r["vt"] / ns, 1),
                        round(r["mv"], 1), round(r["me"], 1), round(r["sw"], 1), round(r["cl"], 1),
                        r["n_meas"], r["n_ok"], r["n_miss"]])
    print("  [tab] tab_practice_summary.csv（%d 局）" % len(rows), flush=True)


if __name__ == "__main__":
    fig_cert_structure()
    fig_case_space()
    fig_version()
    tab_practice()
    print("[done]")