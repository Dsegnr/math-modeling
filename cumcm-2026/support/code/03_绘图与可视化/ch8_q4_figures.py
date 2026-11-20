"""
第八章（问题四）配图
  fig_q4_layout  ：新 81 点巡回（证书前缀 31 点 + L2/L3 补给点）与源清除位置
  fig_q4_cover   ：(a) 前缀长度-L1/L2 覆盖曲线（旧 55 点序 vs 新证书序）
                   (b) 证书集最坏情形可见数分布图（对朝向取最不利）
  fig_q4_path    ：证书式终止首局行走轨迹与清除进度
"""
import os
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(BASE, "figures")
SCRATCH = os.path.join(BASE, "_scratch")
ARCH = os.path.join(SCRATCH, "archive")
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300

ARENA, RMIN, HALF = 1800.0, 990.0, 89.0
C_A, C_B, C_C, C_D, C_E = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59", "#f79646"


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, "%s.%s" % (name, ext)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig] %s" % name, flush=True)


def load_tour():
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    return [tuple(map(float, p)) for p in d["waypoints"]], int(d["n_cert"])


def load_old():
    p = os.path.join(ARCH, "waypoints_p4_v1_55pt.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    return [tuple(map(float, q)) for q in d["waypoints"]]


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def det_counts(pts, X, Y, TH, K=None):
    cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
    for (wx, wy) in (pts[:K] if K else pts):
        dx, dy = wx - X, wy - Y
        vis = dx * dx + dy * dy <= RMIN * RMIN
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        cnt += (vis[:, None] & (diff <= HALF)).astype(np.int16)
    return cnt


def fig_layout():
    tour, ncert = load_tour()
    cand = json.load(open(os.path.join(SCRATCH, "certset_p4_cover.json"), encoding="utf-8"))
    cert = [tuple(p) for p in cand["cert"]]
    inner = [q for q in cert if math.hypot(*q) <= 1100]
    outer = [q for q in cert if math.hypot(*q) > 1100]
    log = json.load(open(os.path.join(ARCH, "practice_0911_q4run3_cert31_run6_p4.json"), encoding="utf-8"))
    cleared = {}
    for e in log["log"]:
        if e["path"] == "/clear" and e.get("resp", {}).get("clear_result") == "success":
            p = e["payload"]
            cleared[p["channel"]] = (p["position"]["x"], p["position"]["y"])

    fig, ax = plt.subplots(figsize=(7.6, 7.0))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.3, ls="--"))
    xs = [0.0] + [q[0] for q in tour[:ncert]]
    ys = [0.0] + [q[1] for q in tour[:ncert]]
    ax.plot(xs, ys, "-", color=C_A, lw=1.7, zorder=3, label="证书前缀巡检路径（前 %d 点）" % ncert)
    ax.plot([q[0] for q in tour[ncert:]], [q[1] for q in tour[ncert:]], "o", ms=4.2,
            mfc="white", mec="0.55", zorder=3, label="L2/L3 补给点（50 点）")
    ax.plot([q[0] for q in inner], [q[1] for q in inner], "o", ms=7.5, color=C_A, zorder=5,
            label="证书内环 13 点（900~1050 m）")
    ax.plot([q[0] for q in outer], [q[1] for q in outer], "s", ms=6.0, color=C_D, zorder=5,
            label="证书外环 18 点（1900 m，每 20°）")
    ax.plot([v[0] for v in cleared.values()], [v[1] for v in cleared.values()], "*", ms=15,
            color=C_B, zorder=6, label="源清除位置（14 个）")
    ax.plot([0], [0], "ks", ms=8, zorder=7, label="起点（原点）")
    for i, q in enumerate(cert, 1):
        ax.annotate(str(i), (q[0], q[1]), textcoords="offset points", xytext=(4, 4),
                    fontsize=6.5, color="0.25")
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("问题四航点集：全域保证检出证书前缀（31 点）+ L2/L3 补给点")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3, fontsize=8.2, framealpha=0.95)
    ax.grid(alpha=0.2)
    fig.subplots_adjust(bottom=0.20)
    save(fig, "fig_q4_layout")


def fig_cover():
    tour, ncert = load_tour()
    old = load_old()
    X, Y = grid(20.0)
    TH = np.arange(0.0, 360.0, 10.0)
    tot = len(X) * len(TH)
    Ks = list(range(4, 58, 2))
    l1n, l2n, l1o, l2o = [], [], [], []
    cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
    for i, w in enumerate(tour, 1):
        dx, dy = w[0] - X, w[1] - Y
        vis = dx * dx + dy * dy <= RMIN * RMIN
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        cnt += (vis[:, None] & (diff <= HALF)).astype(np.int16)
        if i in Ks:
            l1n.append(100.0 * np.count_nonzero(cnt >= 1) / tot)
            l2n.append(100.0 * np.count_nonzero(cnt >= 2) / tot)
    if old:
        cnt = np.zeros((len(X), len(TH)), dtype=np.int16)
        for i, w in enumerate(old, 1):
            dx, dy = w[0] - X, w[1] - Y
            vis = dx * dx + dy * dy <= RMIN * RMIN
            ang = np.degrees(np.arctan2(dy, dx))[:, None]
            diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
            cnt += (vis[:, None] & (diff <= HALF)).astype(np.int16)
            if i in Ks:
                l1o.append(100.0 * np.count_nonzero(cnt >= 1) / tot)
                l2o.append(100.0 * np.count_nonzero(cnt >= 2) / tot)

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9))
    ax = axes[0]
    ax.plot(Ks, l1n, "-o", ms=3.4, color=C_A, label="新证书序 · L1 保证检出")
    ax.plot(Ks, l2n, "--s", ms=3.2, color=C_B, label="新证书序 · L2 两点可定位")
    if l1o:
        ax.plot(Ks[:len(l1o)], l1o, "-^", ms=3.4, color=C_C, label="旧 55 点序 · L1")
        ax.plot(Ks[:len(l2o)], l2o, "--v", ms=3.2, color=C_E, label="旧 55 点序 · L2")
        ax.annotate("旧 55 点走完全程 L1 = %.2f%%（仍未达 100%%）" % l1o[-1],
                    xy=(Ks[len(l1o) - 1], l1o[-1]), xytext=(24.0, 96.0), fontsize=8.0, color=C_C,
                    arrowprops=dict(arrowstyle="->", color=C_C, lw=0.9))
    ax.axvline(ncert, color="0.35", ls=":", lw=1.2)
    ax.annotate("证书前缀 %d 点\nL1 = 100%%" % ncert, xy=(ncert, 100.0),
                xytext=(ncert + 1.5, 88.0), fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="0.35", lw=1.0))
    ax.set_xlabel("巡回前缀长度 / 个航点")
    ax.set_ylabel("全域 (位置×朝向) 覆盖率 / %")
    ax.set_ylim(40, 102)
    ax.set_title("(a) 前缀长度—覆盖能力曲线（网格 20 m×10°）")
    ax.legend(loc="lower right", fontsize=8.2, framealpha=0.95)
    ax.grid(alpha=0.25)

    cert = [tuple(p) for p in json.load(open(os.path.join(SCRATCH, "certset_p4_cover.json"),
                                             encoding="utf-8"))["cert"]]
    Xg, Yg = grid(20.0)
    THg = np.arange(0.0, 360.0, 10.0)
    first = np.full((len(Xg), len(THg)), 9999, dtype=np.int16)
    for i, (wx, wy) in enumerate(cert, 1):
        dx, dy = wx - Xg, wy - Yg
        vis = dx * dx + dy * dy <= RMIN * RMIN
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - THg[None, :] + 180.0) % 360.0 - 180.0)
        cov = vis[:, None] & (diff <= HALF)
        first = np.where(cov & (first == 9999), np.int16(i), first)
    worst = first.max(axis=1)
    ax = axes[1]
    sc = ax.scatter(Xg, Yg, c=worst, s=1.8, cmap="viridis",
                    vmin=int(worst.min()), vmax=int(worst.max()))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.35", lw=1.2, ls="--"))
    for q in cert:
        ax.plot([q[0]], [q[1]], "o", ms=3.2, color=C_B)
    ax.set_aspect("equal")
    ax.set_xlim(-1900, 1900)
    ax.set_ylim(-1900, 1900)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("(b) 各位置在最不利朝向下所需的最靠后证书序号")
    cb = fig.colorbar(sc, ax=ax, fraction=0.045, pad=0.03)
    cb.set_label("$\\max_{\\theta}$ 首次可检出证书序号")
    ax.annotate("全域最大值 = %d，即证书前缀长度 K*" % int(worst.max()),
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=9.0,
                bbox=dict(fc="white", ec="0.7"))
    fig.suptitle("问题四：全域保证检出证书的能力与最坏情形", y=1.02, fontsize=12.5)
    save(fig, "fig_q4_cover")


def fig_path():
    log = json.load(open(os.path.join(ARCH, "practice_0911_q4run3_cert31_run6_p4.json"), encoding="utf-8"))
    tour, ncert = load_tour()
    pts, seen = [], set()
    for e in log["log"]:
        p = e.get("payload", {})
        if e["path"] == "/measure" and "position" in p:
            k = (round(p["position"]["x"], 1), round(p["position"]["y"], 1))
            if k not in seen:
                seen.add(k)
                pts.append(k)
        if e["path"] == "/clear" and e.get("resp", {}).get("clear_result") == "success":
            pts.append((round(p["position"]["x"], 1), round(p["position"]["y"], 1)))
    cl = []
    for e in log["log"]:
        if e["path"] == "/clear" and e.get("resp", {}).get("clear_result") == "success":
            p = e["payload"]
            cl.append((p["position"]["x"], p["position"]["y"], e["resp"]["virtual_time_s"]))

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.4))
    ax = axes[0]
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.2, ls="--"))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=C_C, lw=1.0, alpha=0.8,
            zorder=2, label="机器狗行走轨迹")
    ax.plot([q[0] for q in tour[:ncert]], [q[1] for q in tour[:ncert]], "o", ms=6,
            color=C_A, zorder=4, label="证书前缀 31 点")
    ax.plot([q[0] for q in tour[ncert:]], [q[1] for q in tour[ncert:]], "o", ms=4,
            mfc="white", mec="0.6", zorder=3, label="L2/L3 补给点")
    ax.plot([c[0] for c in cl], [c[1] for c in cl], "*", ms=15, color=C_B, zorder=6,
            label="源清除位置")
    ax.annotate("14 源全部清除于 8552 s\n证书扫完于 10461 s 并终止", xy=(0.03, 0.03),
                xycoords="axes fraction", fontsize=9.0, bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("(a) 行走轨迹与清除位置（14 源全清）")
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.95)
    ax.grid(alpha=0.2)

    ax = axes[1]
    ax.step([c[2] for c in cl], list(range(1, len(cl) + 1)), where="post", color=C_A, lw=2.0,
            label="累计清除源数")
    ax.axhline(14, color="0.4", ls=":", lw=1.1)
    ax.axvline(cl[-1][2], color=C_B, ls="--", lw=1.2)
    ax.axvline(log["virtual_time_s"], color=C_D, ls="-.", lw=1.2)
    ax.set_xlim(0, log["virtual_time_s"] * 1.08)
    ax.annotate("全清 %.0f s" % cl[-1][2], xy=(cl[-1][2], 3), fontsize=8.8, color=C_B,
                rotation=90, va="bottom")
    ax.annotate("证书扫完并终止 %.0f s" % log["virtual_time_s"], xy=(log["virtual_time_s"], 6.5),
                fontsize=8.8, color=C_D, rotation=90, va="bottom")
    ax.set_xlabel("虚拟时间 / s")
    ax.set_ylabel("累计清除源数 / 个")
    ax.set_title("(b) 清除进度与证书尾段")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.25)
    fig.suptitle("问题四演练（14 源，100% 清除）过程图", y=1.02, fontsize=12.5)
    save(fig, "fig_q4_path")


if __name__ == "__main__":
    fig_layout()
    fig_cover()
    fig_path()
    print("[done]")
