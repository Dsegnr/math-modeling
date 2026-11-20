"""
第七、八章（问题三、四）配图
输出：fig_q3_layout（19 点布局与盲区、7 点最小执行集）
      fig_q3_time（Q3/Q4 虚拟时间分解，来自实测日志）
      fig_q4_anglegap（19 点 vs 55 点最坏角隙场与漏检区）
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
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300

ARENA, RMIN, STEP = 1800.0, 1000.0, 20.0
C_A, C_B, C_C, C_D, C_E = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59", "#f79646"


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, "%s.%s" % (name, ext)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig] %s" % name, flush=True)


def layout19():
    p = [(0.0, 0.0)]
    p += [(1000 * math.cos(math.radians(60 * k)), 1000 * math.sin(math.radians(60 * k))) for k in range(6)]
    p += [(1700 * math.cos(math.radians(30 * k)), 1700 * math.sin(math.radians(30 * k))) for k in range(12)]
    return p


def layout55():
    p = layout19()
    p += [(2100 * math.cos(math.radians(20 * k)), 2100 * math.sin(math.radians(20 * k))) for k in range(18)]
    p += [(2400 * math.cos(math.radians(20 * k + 10)), 2400 * math.sin(math.radians(20 * k + 10))) for k in range(18)]
    u = []
    for q in p:
        if not any(math.hypot(q[0] - r[0], q[1] - r[1]) < 1.0 for r in u):
            u.append(q)
    return u


SEL7 = [(0, 0), (1000, 0), (850, 1472), (-850, 1472), (-1700, 0), (-850, -1472), (850, -1472)]


def grid(step=STEP):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X, Y, m


def fig_q3_layout():
    X, Y, m = grid()
    RR, NR = 990.0, 15
    W = np.array([(RR * math.cos(2 * math.pi * k / NR), RR * math.sin(2 * math.pi * k / NR))
                  for k in range(NR)])
    d = np.sqrt((X[:, :, None] - W[None, None, :, 0]) ** 2 + (Y[:, :, None] - W[None, None, :, 1]) ** 2)
    dmin = np.where(m, d.min(axis=2), np.nan)
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.8))
    ax = axes[0]
    cf = ax.contourf(X, Y, dmin, levels=np.arange(0, 1001, 100), cmap="YlOrRd_r", alpha=0.85)
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="k", lw=1.4))
    ax.add_patch(Circle((0, 0), RR, fill=False, ec=C_A, lw=1.2, ls="--"))
    ax.plot(W[:, 0], W[:, 1], "o", color=C_A, ms=6.5, mec="white", mew=0.9, zorder=5,
            label="单环建证集（%d 点，$R$=%.0f m）" % (NR, RR))
    ax.plot([0], [0], "ks", ms=8, zorder=6, label="起飞点（原点）")
    ax.set_aspect("equal")
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("(a) 单环 15 点建证集的盲区场（全域最大 990 m）")
    fig.colorbar(cf, ax=ax, label="盲区 / m", fraction=0.038, pad=0.03)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax = axes[1]
    labs = ["19 点\n中心+1000环6\n+1700环12", "17 点\n交会友好\n建证集", "单环 990 m×15\n（本文采用）"]
    L = [15140, 13710, 6753]
    bb = ax.bar(labs, L, color=[C_C, C_A, C_E], width=0.55)
    for r, v in zip(bb, L):
        ax.text(r.get_x() + r.get_width() / 2, v + 220, "%d m" % v, ha="center", fontsize=9.5)
    ax.set_ylabel("巡回里程 / m")
    ax.set_title("(b) 巡回里程对比：受环半径的结构性支配")
    ax.grid(alpha=0.25, axis="y")
    save(fig, "fig_q3_layout")


def _breakdown(path):
    d = json.load(open(path, encoding="utf-8"))
    log = [e for e in d["log"] if isinstance(e.get("resp"), dict) and e["resp"].get("accepted")]
    pos = None
    ch = 1
    t_move = t_meas = t_sw = t_clr = 0.0
    nm = nc = ns = 0
    for e in log:
        p = e["payload"]
        if "position" in p:
            q = (p["position"]["x"], p["position"]["y"])
            if pos is not None:
                t_move += math.hypot(q[0] - pos[0], q[1] - pos[1]) / 5.0
            pos = q
        if e["path"] == "/measure":
            nm += 1
            t_meas += 5.0
            if p.get("channel") != ch:
                t_sw += 1.0
                ns += 1
            ch = p.get("channel", ch)
        elif e["path"] == "/clear":
            nc += 1
            t_clr += 5.0 if e["resp"].get("clear_result") == "success" else 3.0
    return dict(vt=d.get("virtual_time_s", 0), move=t_move, meas=t_meas, sw=t_sw, clr=t_clr,
                nm=nm, nc=nc, ns=ns)


def fig_q3_time():
    rows = []
    for tag, fn in (("问题三（单环 990 m×15）", "run6_p3.json"), ("问题四（证书前缀 31 点）", "run6_p4.json")):
        p = os.path.join(SCRATCH, fn)
        if os.path.exists(p):
            rows.append((tag, _breakdown(p)))
    if not rows:
        print("  [skip] 无实测日志", flush=True)
        return rows
    cats = ["移动", "检测", "频道切换", "清除（光学+激光）"]
    keys = ["move", "meas", "sw", "clr"]
    colors = [C_A, C_C, C_D, C_B]
    totals = [sum(r[1][k] for k in keys) for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.6))
    ax = axes[0]
    bottom = np.zeros(len(rows))
    for k, c, lab in zip(keys, colors, cats):
        vals = np.array([r[1][k] for r in rows])
        ax.bar([r[0] for r in rows], vals, bottom=bottom, color=c, label=lab, width=0.5)
        for i, v in enumerate(vals):
            if v > 300:
                ax.text(i, bottom[i] + v / 2, "%.0f s (%.0f%%)" % (v, 100.0 * v / totals[i]),
                        ha="center", va="center", fontsize=9, color="white")
        bottom += vals
    for i, r in enumerate(rows):
        ax.text(i, bottom[i] + 160, "合计 %.0f s\n实测虚拟时间 %.0f s" % (bottom[i], r[1]["vt"]),
                ha="center", fontsize=9)
    ax.set_ylabel("虚拟时间 / s")
    ax.set_ylim(0, bottom.max() * 1.25)
    ax.set_title("(a) 虚拟时间构成分解")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    ax = axes[1]
    ax.axis("off")
    for i, r in enumerate(rows):
        b = r[1]
        txt = ("%s\n  检测 %d 次 · 切频 %d 次 · 清除 %d 次\n  移动路程 %.0f m（占 %.0f%% 时间）"
               % (r[0], b["nm"], b["ns"], b["nc"], b["move"] * 5, 100.0 * b["move"] / totals[i]))
        ax.text(0.04, 0.90 - i * 0.36, txt, transform=ax.transAxes, fontsize=10, va="top",
                bbox=dict(fc="white", ec="0.75"))
    ax.set_title("(b) 指令次数与移动规模")
    ax.set_title("(b) 指令次数与移动规模")
    fig.suptitle("图 7-3  问题三、四的虚拟时间构成（基于官方模拟器实测日志）", y=1.03, fontsize=12.5)
    save(fig, "fig_q3_time")
    return rows


def anglegap_field(W, X, Y, m):
    W = np.array(W)
    G = np.full(X.shape, 0.0)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            if not m[i, j]:
                continue
            dx = W[:, 0] - X[i, j]
            dy = W[:, 1] - Y[i, j]
            d = np.hypot(dx, dy)
            idx = np.where(d <= RMIN)[0]
            if len(idx) < 1:
                G[i, j] = 360.0
                continue
            a = np.sort(np.arctan2(dy[idx], dx[idx]))
            gaps = np.append(np.diff(a), 2 * math.pi - (a[-1] - a[0]))
            G[i, j] = math.degrees(gaps.max())
    return G


def fig_q4_anglegap():
    X, Y, m = grid()
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.6))
    for ax, W, nm in ((axes[0], layout19(), "19 点布局"), (axes[1], layout55(), "55 点布局")):
        G = anglegap_field(W, X, Y, m)
        G = np.where(m, G, np.nan)
        cf = ax.contourf(X, Y, G, levels=np.arange(0, 361, 20), cmap="RdYlGn_r")
        ax.contour(X, Y, G, levels=[180.0], colors="k", linewidths=2.0)
        bad = np.where(m & (G > 180.0), 1.0, np.nan)
        ax.contourf(X, Y, bad, levels=[0.5, 1.5], colors="none", hatches=["////"],
                    edgecolor="k", linewidth=0.0)
        Wa = np.array(W)
        ax.plot(Wa[:, 0], Wa[:, 1], "o", color="k", ms=3.5)
        ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="k", lw=1.4))
        ax.set_aspect("equal")
        ax.set_xlabel("$x$ / m")
        ax.set_title("%s：全域最坏角隙 %.1f°" % (nm, np.nanmax(G)))
        fig.colorbar(cf, ax=ax, label="最坏角隙 $\\Delta_{\\max}$ / 度", fraction=0.046)
    axes[0].set_ylabel("$y$ / m")
    fig.suptitle("图 8-2  问题四：19 点与 55 点布局的最坏角隙场（黑线为 180° 判据边界，斜纹区为漏检区）",
                 y=1.02, fontsize=12.0)
    save(fig, "fig_q4_anglegap")


if __name__ == "__main__":
    fig_q3_layout()
    fig_q3_time()
    fig_q4_anglegap()
    print("[done]", flush=True)
