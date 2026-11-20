"""问题三演练过程图：行走轨迹图 + 多局清除进度曲线"""
import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE = os.path.dirname(os.path.abspath(__file__))
FIGD = os.path.join(BASE, "figures")
ARCH = os.path.join(BASE, "_scratch", "archive")
os.makedirs(FIGD, exist_ok=True)
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300
C1, C2, C3 = "#1f4e79", "#c0504d", "#4f81bd"
ARENA = 1800.0
W17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
       (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
       (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]


def save(fig, name):
    for e in ("png", "pdf"):
        fig.savefig(os.path.join(FIGD, "%s.%s" % (name, e)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig]", name, flush=True)


def trace(path):
    d = json.load(open(path, encoding="utf-8"))
    log = [e for e in d["log"] if isinstance(e.get("resp"), dict) and e["resp"].get("accepted")]
    out = []
    for e in log:
        p = e["payload"]
        if "position" in p and e["path"] in ("/measure", "/clear"):
            out.append((p["position"]["x"], p["position"]["y"], e["path"],
                        e["resp"].get("clear_result"), p.get("channel"),
                        e["resp"].get("virtual_time_s", 0.0)))
    return out


def fig_path():
    pts = trace(os.path.join(ARCH, "practice_0911_run4_UYG2_run6_p3.json"))
    fig, ax = plt.subplots(figsize=(7.4, 6.8))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.2, ls="--"))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=C3, lw=1.0, alpha=0.75,
            zorder=2, label="机器狗行走轨迹")
    for i, (px, py) in enumerate(W17, 1):
        ax.plot([px], [py], "o", ms=6, color=C1, zorder=4,
                label="17 点建证集航点" if i == 1 else None)
    cl = [(p[0], p[1], p[4]) for p in pts if p[3] == "success"]
    ax.plot([c[0] for c in cl], [c[1] for c in cl], "*", ms=13, color=C2, zorder=6,
            label="清除成功点")
    ax.plot([0], [0], "s", ms=8, color="k", zorder=6, label="起点（原点）")
    ax.annotate("清除 11 个源\n虚拟时间 7607 s", xy=(0.03, 0.03), xycoords="axes fraction",
                fontsize=9.5, bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2300, 2300)
    ax.set_ylim(-2300, 2300)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("问题三演练行走轨迹（11 个源全部清除）")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(alpha=0.2)
    save(fig, "fig_q3_path")


def fig_progress():
    runs = [("practice_0911_run1_X8GD_run6_p3.json", "旧19点·12源"),
            ("practice_0911_run4_UYG2_run6_p3.json", "17点·11源"),
            ("practice_0911_run5_KE7U_run6_p3.json", "17点·13源"),
            ("practice_0911_run7_CH3A_run6_p3.json", "混合·10源"),
            ("practice_0911_run8_RXB3_run6_p3.json", "混合·13源")]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.8))
    ax, cmap = axes[0], plt.get_cmap("viridis")
    tails = []
    for i, (fn, lab) in enumerate(runs):
        pts = trace(os.path.join(ARCH, fn))
        ts, cs, c = [], [], 0
        for p in pts:
            if p[3] == "success":
                c += 1
                ts.append(p[5])
                cs.append(c)
        t1 = max(p[5] for p in pts)
        col = cmap(i / max(1, len(runs) - 1))
        ax.step([0.0] + ts + [t1], [0] + cs + [cs[-1]], where="post", color=col, lw=1.8, label=lab)
        ax.plot([ts[-1]], [cs[-1]], "o", ms=5, color=col)
        tails.append((lab, t1 - ts[-1]))
    ax.set_xlabel("虚拟时间 / s")
    ax.set_ylabel("累计清除源数 / 个")
    ax.set_title("(a) 各局清除进度（圆点为全部清除时刻）")
    ax.legend(loc="lower right", fontsize=8.5)
    ax.grid(alpha=0.25)
    ax = axes[1]
    b = ax.bar([t[0] for t in tails], [t[1] for t in tails], color=C2, width=0.5)
    for r, v in zip(b, [t[1] for t in tails]):
        ax.text(r.get_x() + r.get_width() / 2, v + 30, "%.0f" % v, ha="center", fontsize=9)
    ax.set_ylabel("全部清除后的剩余虚拟时间 / s")
    ax.set_title("(b) 无效尾段（越小越好）")
    ax.tick_params(axis="x", labelsize=8.5)
    ax.grid(alpha=0.25, axis="y")
    fig.suptitle("问题三演练清除进度与无效尾段分析", y=1.02, fontsize=12.5)
    save(fig, "fig_q3_progress")


if __name__ == "__main__":
    fig_path()
    fig_progress()
    print("[done]")
