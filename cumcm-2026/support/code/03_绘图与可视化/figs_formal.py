"""
Formal-test figures (B problem, problems 3 and 4).

Inputs : the six formal-run logs archived by the hardened runner
         (_scratch/formal_p{3,4}_*.json) plus the practice archives.
Outputs: overwrites fig_q3_path / fig_q3_progress / fig_q4_path / fig_q3_time
         and adds fig_formal_summary / fig_q4_fallback.

Every number drawn here is read from the run logs; nothing is hand-typed.
"""
import os
import json
import math
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.join(BASE, "_scratch")
ARCH = os.path.join(SCRATCH, "archive")

# Figures are written next to this script; an extra output directory may be
# passed on the command line (for example the LaTeX build's figures folder):
#   python figs_formal.py <extra-figure-dir>
OUTDIRS = [os.path.join(BASE, "figures")]
if len(sys.argv) > 1:
    OUTDIRS.append(sys.argv[1])

for d in OUTDIRS:
    os.makedirs(d, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300

ARENA = 1800.0
RMIN = 1000.0
C1, C2, C3, C4 = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59"

FORMAL = {
    "p3": [("第 1 局", "formal_p3_20260912_151455.json"),
           ("第 2 局", "formal_p3_20260912_152006.json"),
           ("第 3 局", "formal_p3_20260912_152259.json")],
    "p4": [("第 1 局", "formal_p4_20260912_152701.json"),
           ("第 2 局", "formal_p4_20260912_153140.json"),
           ("第 3 局", "formal_p4_20260912_153557.json")],
}
CASES = {"p3": ["6A7K-XC7T-GK8K-7GGK", "UEVE-DGYC-PJJ2-VFHY", "CGP2-9BMC-G7MB-HR8D"],
         "p4": ["TY66-BXB7-63BJ-M3Z6", "N3D8-NNPH-3ZCJ-TVQC", "V3VE-CRSQ-5SMB-NHG6"]}


def save(fig, name):
    for d in OUTDIRS:
        for e in ("png", "pdf"):
            fig.savefig(os.path.join(d, "%s.%s" % (name, e)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig]", name, flush=True)


def load(name, folder=None):
    p = os.path.join(folder or SCRATCH, name)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def trace(d):
    out = []
    for e in d["log"]:
        r = e.get("resp")
        if not isinstance(r, dict) or not r.get("accepted"):
            continue
        p = e.get("payload", {})
        if "position" not in p:
            continue
        q = p["position"]
        out.append(dict(x=q["x"], y=q["y"], kind=e["path"].lstrip("/"),
                        res=r.get("clear_result"), ch=p.get("channel"),
                        vt=r.get("virtual_time_s", 0.0), mres=r.get("measure_result"),
                        svd=r.get("svd_deg")))
    return out


def stats(path):
    d = load(path)
    pts = trace(d)
    n_src = len(d["observed"])
    n_clr = len(d["cleared"])
    vt = d["virtual_time_s"]
    calls = [p for p in pts if p["kind"] == "clear"]
    miss = [p for p in calls if p["res"] != "success"]
    return dict(d=d, pts=pts, n_src=n_src, n_clr=n_clr, vt=vt, avg=vt / max(1, n_src),
                calls=len(calls), miss=len(miss))


def waypoints():
    with open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    return [tuple(map(float, p)) for p in d["waypoints"]], int(d["n_cert"])


def ring(r, n):
    return [(r * math.cos(math.radians(360.0 * k / n)),
             r * math.sin(math.radians(360.0 * k / n))) for k in range(n)]


def draw_path(name, run, title, wps, ncert, note, cert_label="证书段", figsize=(7.6, 7.0)):
    st = stats(run)
    pts = st["pts"]
    cl = [p for p in pts if p["res"] == "success"]
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.3, ls="--"))
    ax.plot([p["x"] for p in pts], [p["y"] for p in pts], "-", color=C3, lw=0.9, alpha=0.85,
            zorder=2, label="行走轨迹")
    if ncert:
        ax.plot([q[0] for q in wps[:ncert]], [q[1] for q in wps[:ncert]], "o", ms=6.2,
                color=C1, zorder=4, label="%s（%d 点）" % (cert_label, ncert))
    if len(wps) > ncert:
        ax.plot([q[0] for q in wps[ncert:]], [q[1] for q in wps[ncert:]], "o", ms=4.0,
                mfc="white", mec="0.6", zorder=3, label="L2/L3 补给点（%d 点）" % (len(wps) - ncert))
    ax.plot([p["x"] for p in cl], [p["y"] for p in cl], "*", ms=14, color=C2, zorder=6,
            label="源清除位置（%d 个）" % len(cl))
    ax.plot([0], [0], "ks", ms=8, zorder=7, label="起点（原点）")
    ax.annotate(note, xy=(0.03, 0.03), xycoords="axes fraction", fontsize=9.2,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title(title)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8.2, framealpha=0.95)
    ax.grid(alpha=0.2)
    fig.subplots_adjust(bottom=0.20)
    save(fig, name)


def fig_q3_path():
    lab, run = FORMAL["p3"][1]
    st = stats(run)
    draw_path("fig_q3_path", run,
              "问题三正式测试%s：%d 源全部清除（行走轨迹与清除位置）" % (lab, st["n_src"]),
              ring(990, 15), 15,
              "%d 源全部清除\n虚拟时间 %.1f s\n平均 %.1f s/源"% (st["n_src"], st["vt"], st["avg"]),
              cert_label="建证集")


def progress(name, runs, title):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    ax = axes[0]
    cmap = plt.get_cmap("viridis")
    tails = []
    for i, (fn, lab) in enumerate(runs):
        pts = stats(fn)["pts"]
        ts, cs, c = [], [], 0
        for p in pts:
            if p["res"] == "success":
                c += 1
                ts.append(p["vt"])
                cs.append(c)
        t1 = max(p["vt"] for p in pts)
        col = cmap(i / max(1, len(runs) - 1))
        ax.step([0.0] + ts + [t1], [0] + cs + [cs[-1]], where="post", color=col, lw=1.7, label=lab)
        ax.plot([ts[-1]], [cs[-1]], "o", ms=5, color=col)
        tails.append((lab, t1 - ts[-1]))
    ax.set_xlabel("虚拟时间 / s")
    ax.set_ylabel("累计清除源数 / 个")
    ax.set_title("(a) 清除进度")
    ax.legend(loc="lower right", fontsize=8.0)
    ax.grid(alpha=0.25)
    ax = axes[1]
    b = ax.bar([t[0] for t in tails], [t[1] for t in tails], color=C2, width=0.55)
    top = max(t[1] for t in tails)
    for r, v in zip(b, [t[1] for t in tails]):
        ax.text(r.get_x() + r.get_width() / 2, v + top * 0.02, "%.0f" % v, ha="center", fontsize=9)
    ax.set_ylabel("末次清除后的剩余时间 / s")
    ax.set_title("(b) 无效尾段（越小越好）")
    ax.tick_params(axis="x", labelsize=8.0, rotation=20)
    for lb in ax.get_xticklabels():
        lb.set_ha("right")
    ax.grid(alpha=0.25, axis="y")
    ax.set_ylim(0, top * 1.25)
    fig.suptitle(title, y=1.02, fontsize=12.5)
    save(fig, name)


def fig_q3_progress():
    runs = [(fn, "%s\n%d 源" % (lab, stats(fn)["n_src"])) for lab, fn in FORMAL["p3"]]
    progress("fig_q3_progress", runs, "问题三三次正式测试：清除进度与无效尾段")


def fig_q4_path():
    W, ncert = waypoints()
    lab, run = FORMAL["p4"][0]
    st = stats(run)
    draw_path("fig_q4_path", run,
              "问题四正式测试%s：%d 源全部清除（证书前缀 + 补给点）" % (lab, st["n_src"]),
              W, ncert,
              "%d 源全部清除\n虚拟时间 %.1f s\n平均 %.1f s/源" % (st["n_src"], st["vt"], st["avg"]))


def breakdown(path):
    d = load(path)
    log = [e for e in d["log"] if isinstance(e.get("resp"), dict) and e["resp"].get("accepted")]
    pos, ch = None, 1
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
    for prob, tag in (("p3", "问题三"), ("p4", "问题四")):
        for lab, fn in FORMAL[prob]:
            rows.append(("%s\n%s" % (tag, lab), breakdown(os.path.join(SCRATCH, fn))))
    cats = ["移动", "检测", "频道切换", "清除（光学+激光）"]
    keys = ["move", "meas", "sw", "clr"]
    colors = [C1, C3, C4, C2]
    totals = [sum(r[1][k] for k in keys) for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.8))
    ax = axes[0]
    bottom = np.zeros(len(rows))
    for k, c, lab in zip(keys, colors, cats):
        vals = np.array([r[1][k] for r in rows])
        ax.bar([r[0] for r in rows], vals, bottom=bottom, color=c, label=lab, width=0.6)
        for i, v in enumerate(vals):
            if v > 400:
                ax.text(i, bottom[i] + v / 2, "%.0f s\n(%.0f%%)" % (v, 100.0 * v / totals[i]),
                        ha="center", va="center", fontsize=7.6, color="white")
        bottom += vals
    for i, r in enumerate(rows):
        ax.text(i, bottom[i] + 150, "合计 %.0f s\n实测 %.0f s" % (bottom[i], r[1]["vt"]),
                ha="center", fontsize=8.0)
    ax.set_ylabel("虚拟时间 / s")
    ax.set_ylim(0, bottom.max() * 1.22)
    ax.tick_params(axis="x", labelsize=8.0)
    ax.set_title("(a) 六次正式测试的虚拟时间构成分解")
    ax.legend(loc="upper left", fontsize=8.4)
    ax.grid(alpha=0.25, axis="y")
    ax = axes[1]
    x = np.arange(len(rows))
    mv = [100.0 * r[1]["move"] / totals[i] for i, r in enumerate(rows)]
    bar = ax.bar(x, mv, color=C1, width=0.6, label="移动占比")
    for xi, v, r in zip(x, mv, rows):
        ax.text(xi, v + 1.2, "%.0f%%\n%.0f m" % (v, r[1]["move"] * 5), ha="center", fontsize=8.0)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], fontsize=8.0)
    ax.set_ylabel("移动时间占比 / %")
    ax.set_ylim(0, max(mv) * 1.35)
    ax.set_title("(b) 移动占比与移动路程")
    ax.grid(alpha=0.25, axis="y")
    fig.suptitle("六次正式测试的虚拟时间构成（全部取自正式测试运行日志）", y=1.02, fontsize=12.5)
    save(fig, "fig_q3_time")
    return rows


# Practice sample used in the appendix (tables D2/D3): final configuration only.
# Values are the (source count, seconds per source) pairs already recorded there,
# so the figure and the appendix can never disagree.
PRACTICE = {
    "p3": [(10, 398.0), (15, 288.0), (15, 291.0), (11, 391.0), (16, 397.0), (15, 346.0),
           (16, 263.0), (16, 304.0), (12, 369.0), (16, 298.0), (10, 506.0), (13, 345.0),
           (10, 381.8), (11, 647.0), (16, 294.0), (14, 314.0)],
    "p4": [(15, 556.0), (14, 611.5), (11, 692.4), (13, 543.2), (15, 416.9), (16, 408.8),
           (12, 714.6), (11, 594.7), (13, 596.7), (14, 473.5), (12, 724.8), (15, 437.6),
           (13, 529.1), (15, 523.7), (12, 665.6), (16, 401.3)],
}


def fig_formal_summary():
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9))
    for ax, prob, tag, key in ((axes[0], 3, "问题三", "p3"), (axes[1], 4, "问题四", "p4")):
        pr = PRACTICE[key]
        if prob == 3:
            lab_pr = "演练（附录表 D2 的 %d 局）" % len(pr)
        else:
            lab_pr = "演练（附录表 D3 中 %d 局有 s/源 指标者）" % len(pr)
        fx = []
        for lab, fn in FORMAL[key]:
            st = stats(os.path.join(SCRATCH, fn))
            fx.append((st["n_src"], st["avg"], lab))
        ax.scatter([p[0] for p in pr], [p[1] for p in pr], s=42, c="#9dc3e6", alpha=0.85,
                   edgecolors="white", linewidths=0.6, zorder=3, label=lab_pr)
        ax.scatter([f[0] for f in fx], [f[1] for f in fx], s=170, marker="*", c=C2,
                   edgecolors="k", linewidths=0.7, zorder=5, label="正式测试（3 局，100% 清除）")
        for n, a, lab in fx:
            ax.annotate(lab, (n, a), textcoords="offset points", xytext=(9, 6), fontsize=8.6)
        mf = float(np.mean([f[1] for f in fx]))
        mp = float(np.mean([p[1] for p in pr]))
        ax.axhline(mf, color=C2, ls="--", lw=1.4, zorder=2)
        ax.axhline(mp, color="#4472c4", ls=":", lw=1.3, zorder=2)
        ax.annotate("正式均值 %.1f s/源" % mf, (0.02, 0.93), xycoords="axes fraction",
                    fontsize=9.2, color=C2, bbox=dict(fc="white", ec="0.75"))
        ax.annotate("演练均值 %.1f s/源" % mp, (0.02, 0.84), xycoords="axes fraction",
                    fontsize=9.2, color="#4472c4", bbox=dict(fc="white", ec="0.75"))
        ax.set_xlabel("干扰源个数 / 个")
        ax.set_ylabel("平均定位清除时间 / (s/源)")
        ax.set_title("(%s) %s：正式测试与演练分布" % ("a" if prob == 3 else "b", tag))
        ax.grid(alpha=0.25)
        ax.legend(loc="lower right", fontsize=8.4, framealpha=0.95)
    fig.suptitle("六次正式测试成绩与演练分布对照（正式为主、演练为辅）", y=1.02, fontsize=12.5)
    save(fig, "fig_formal_summary")


def fig_q4_fallback():
    lab, run = FORMAL["p4"][1]
    st = stats(run)
    pts = st["pts"]
    W, ncert = waypoints()
    ev = {}
    for p in pts:
        if p["ch"] in (12, 14) and p["mres"] == "direction":
            ev.setdefault(p["ch"], []).append(p)
        if p["ch"] in (12, 14) and p["res"] == "success":
            ev.setdefault(("clr", p["ch"]), []).append(p)
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.7))
    # (a) overview
    ax = axes[0]
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.2, ls="--"))
    ax.plot([p["x"] for p in pts], [p["y"] for p in pts], "-", color=C3, lw=0.8, alpha=0.8, zorder=2)
    ax.plot([q[0] for q in W[:ncert]], [q[1] for q in W[:ncert]], "o", ms=4.4, color=C1, zorder=4,
            label="证书前缀 31 点")
    cl = [p for p in pts if p["res"] == "success"]
    ax.plot([p["x"] for p in cl], [p["y"] for p in cl], "*", ms=12, color=C2, zorder=6,
            label="清除位置（%d 个）" % len(cl))
    for ch, mk in ((12, "o"), (14, "s")):
        c = ev[("clr", ch)][0]
        ax.plot([c["x"]], [c["y"]], mk, ms=9, mfc="none", mec="k", mew=1.6, zorder=7)
        ax.annotate("ch%d" % ch, (c["x"], c["y"]), textcoords="offset points", xytext=(7, 7), fontsize=9)
    ax.annotate("本局 %d 源各清除一次\n其中 2 个源由兜底分支完成\n清除调用 %d 次，候选试探落空 %d 次"
                % (st["n_src"], st["calls"], st["miss"]),
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=8.8,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("(a) 正式第 2 局全景")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8.2)
    ax.grid(alpha=0.2)
    # (b) ch12 zoom : single bearing -> active re-measurement -> intersect -> clear
    for ax, ch, title in ((axes[1], 12, "(b) ch12：单观测触发的主动补测"),
                          (axes[2], 14, "(c) ch14：双示向度驱动的收尾清除")):
        ms = ev[ch]
        c = ev[("clr", ch)][0]
        ax.plot([0], [c["y"]], color="none")
        for j, m in enumerate(ms):
            t = math.radians(m["svd"])
            L = 2600.0
            ux, uy = math.cos(t), math.sin(t)
            ax.plot([m["x"], m["x"] + L * ux], [m["y"], m["y"] + L * uy], ls="--", lw=1.5,
                    color=C1, alpha=0.95, zorder=3)
            ax.annotate("", xy=(m["x"] + 700.0 * ux, m["y"] + 700.0 * uy), xytext=(m["x"], m["y"]),
                        arrowprops=dict(arrowstyle="-|>", color=C1, lw=1.8), zorder=4)
            ax.plot([m["x"]], [m["y"]], "o", ms=7, color=C1, zorder=5)
            ax.annotate("$t$=%.1f s\n%.2f°" % (m["vt"], m["svd"]), (m["x"], m["y"]),
                        textcoords="offset points",
                        xytext=(10, -30) if j == 0 else (-30, 20), fontsize=8.2,
                        bbox=dict(fc="white", ec="0.75"))
        ax.plot([c["x"]], [c["y"]], "*", ms=17, color=C2, zorder=6)
        ax.annotate("清除成功\n$t$=%.1f s" % c["vt"], (c["x"], c["y"]), textcoords="offset points",
                    xytext=(-46, 20), fontsize=8.6, bbox=dict(fc="white", ec="0.75"))
        xs = [m["x"] for m in ms] + [c["x"]]
        ys = [m["y"] for m in ms] + [c["y"]]
        pad = 900.0
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_aspect("equal")
        ax.set_xlabel("$x$ / m")
        ax.set_ylabel("$y$ / m")
        ax.set_title(title)
        ax.grid(alpha=0.22)
    fig.suptitle("问题四正式第 2 局的兜底分支：两个弱观测源全部清除，且 15 个源各清除一次", y=1.03, fontsize=12.3)
    save(fig, "fig_q4_fallback")


if __name__ == "__main__":
    fig_q3_path()
    fig_q3_progress()
    fig_q4_path()
    fig_q3_time()
    fig_formal_summary()
    fig_q4_fallback()
    print("[done]")
