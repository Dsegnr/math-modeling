"""
演练过程图（按当前冻结策略重绘）
  fig_q3_path      问题三：行走轨迹 + 单环建证集 + 清除位置（取最新 16 源一局）
  fig_q3_progress  问题三：多局清除进度 + 无效尾段（新旧策略对照）
  fig_q4_path      问题四：行走轨迹 + 31 点证书前缀 + 补给点 + 清除位置
  fig_q4_progress  问题四：多局清除进度 + 无效尾段
  fig_stress       压力测试：削弱外环布局 + 单观测补测事件的几何位置
  fig_single_fix   单观测主动补测的几何示意（已验证的退化案例）
"""
import os
import json
import math
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
ARENA = 1800.0
C1, C2, C3, C4 = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59"


def save(fig, name):
    for e in ("png", "pdf"):
        fig.savefig(os.path.join(FIGD, "%s.%s" % (name, e)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig]", name, flush=True)


def log_of(name):
    return json.load(open(os.path.join(ARCH, name), encoding="utf-8"))


def trace(d):
    """返回 [(x, y, kind, result, ch, vt)]，kind ∈ {measure, clear}"""
    out = []
    for e in d["log"]:
        if not isinstance(e.get("resp"), dict) or not e["resp"].get("accepted"):
            continue
        p = e.get("payload", {})
        if "position" not in p:
            continue
        q = p["position"]
        out.append((q["x"], q["y"], e["path"].lstrip("/"), e["resp"].get("clear_result"),
                    p.get("channel"), e["resp"].get("virtual_time_s", 0.0)))
    return out


def waypoints():
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    W = [tuple(map(float, p)) for p in d["waypoints"]]
    return W, int(d["n_cert"])


def ring(r, n, off=0.0):
    return [(r * math.cos(math.radians(360.0 * k / n + off)),
             r * math.sin(math.radians(360.0 * k / n + off))) for k in range(n)]


def draw_path(name, logfile, title, wps, ncert, note, cert_label="证书段", figsize=(7.6, 7.0)):
    d = log_of(logfile)
    pts = trace(d)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cl = [p for p in pts if p[3] == "success"]
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.3, ls="--"))
    ax.plot(xs, ys, "-", color=C3, lw=0.9, alpha=0.85, zorder=2, label="行走轨迹")
    if ncert:
        ax.plot([q[0] for q in wps[:ncert]], [q[1] for q in wps[:ncert]], "o", ms=6.2,
                color=C1, zorder=4, label="%s（%d 点）" % (cert_label, ncert))
    if len(wps) > ncert:
        ax.plot([q[0] for q in wps[ncert:]], [q[1] for q in wps[ncert:]], "o", ms=4.0,
                mfc="white", mec="0.6", zorder=3, label="L2/L3 补给点（%d 点）" % (len(wps) - ncert))
    ax.plot([p[0] for p in cl], [p[1] for p in cl], "*", ms=14, color=C2, zorder=6,
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


def progress(name, runs, title):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    ax, cmap = axes[0], plt.get_cmap("viridis")
    tails = []
    for i, (fn, lab) in enumerate(runs):
        pts = trace(log_of(fn))
        ts, cs, c = [], [], 0
        for p in pts:
            if p[3] == "success":
                c += 1
                ts.append(p[5])
                cs.append(c)
        t1 = max(p[5] for p in pts)
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
    for r, v in zip(b, [t[1] for t in tails]):
        ax.text(r.get_x() + r.get_width() / 2, v + max(tails, key=lambda z: z[1])[1] * 0.02,
                "%.0f" % v, ha="center", fontsize=9)
    ax.set_ylabel("末次清除后的剩余时间 / s")
    ax.set_title("(b) 无效尾段（越小越好）")
    ax.tick_params(axis="x", labelsize=8.0, rotation=20)
    for lb in ax.get_xticklabels():
        lb.set_ha("right")
    ax.grid(alpha=0.25, axis="y")
    fig.suptitle(title, y=1.02, fontsize=12.5)
    save(fig, name)


def fig_stress():
    d = log_of("stress_p4_run3_v17c_PASS_run6_p4.json")
    pts = trace(d)
    W = [tuple(map(float, p)) for p in
         json.load(open(os.path.join(BASE, "_scratch", "waypoints_p4_stress.json"),
                        encoding="utf-8"))["waypoints"]]
    fig, ax = plt.subplots(figsize=(7.6, 7.0))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.3, ls="--"))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=C3, lw=0.9, alpha=0.85,
            zorder=2, label="行走轨迹")
    ax.plot([q[0] for q in W[:15]], [q[1] for q in W[:15]], "o", ms=6, color=C1, zorder=4,
            label="内环 990 m×15 点")
    ax.plot([q[0] for q in W[15:]], [q[1] for q in W[15:]], "s", ms=7.5, color=C4, zorder=4,
            label="外环仅 6 点（每 60°，人为削弱）")
    cl = [p for p in pts if p[3] == "success"]
    ax.plot([p[0] for p in cl], [p[1] for p in cl], "*", ms=14, color=C2, zorder=6,
            label="清除成功（%d 个）" % len(cl))
    # 标出两个补测事件（其清除点即补测后定位点）
    for (bx, by, tag, txt) in ((-975, 644, "补测①", "ch5"), (302, -1063, "补测②", "ch18")):
        ax.plot([bx], [by], "D", ms=9, mfc="none", mec="k", mew=1.6, zorder=8)
        ax.annotate("%s %s" % (tag, txt), (bx, by), textcoords="offset points", xytext=(8, 8),
                    fontsize=9.0, bbox=dict(fc="white", ec="0.7"))
    ax.annotate("外环被削弱到 6 点，边界朝外的源只能被 1 个点看到\n"
                "补测分支两次触发并均成功定位清除（12/12 全清）",
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=9.0,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("问题四压力测试：削弱外环逼出「单观测」情形")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=8.4, framealpha=0.95)
    ax.grid(alpha=0.2)
    fig.subplots_adjust(bottom=0.18)
    save(fig, "fig_stress")


def fig_single_fix():
    src, th = (0.0, -1800.0), 270.0
    p0, a0 = (329.9, -1871.1), 347.8              # 唯一可见点及其"源→测点"方位
    CAND = ((0.0, 700.0), (0.0, -700.0), (300.0, 700.0), (300.0, -700.0),
            (500.0, 700.0), (500.0, -700.0), (800.0, 500.0), (800.0, -500.0))
    t = math.radians((a0 + 180.0) % 360.0)         # 沿"测点→源"方位前移
    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.2, ls="--"))
    ax.plot([src[0]], [src[1]], "*", ms=16, color=C2, zorder=6, label="源（域边界，朝向 270°）")
    ax.annotate("", xy=(src[0], src[1] - 700), xytext=(src[0], src[1]),
                arrowprops=dict(arrowstyle="-|>", color=C2, lw=2.0))
    ax.text(src[0] + 60, src[1] - 640, "定向方向", color=C2, fontsize=9)
    ax.plot([p0[0]], [p0[1]], "o", ms=9, color=C1, zorder=6, label="证书段唯一可见点")
    ax.plot([src[0], p0[0]], [src[1], p0[1]], "--", color=C1, lw=1.4)
    good = []
    for fw, sd in CAND:
        pm = (p0[0] + fw * math.cos(t) - sd * math.sin(t),
              p0[1] + fw * math.sin(t) + sd * math.cos(t))
        d = math.hypot(pm[0] - src[0], pm[1] - src[1])
        a = math.degrees(math.atan2(pm[0] - src[0], pm[1] - src[1]))
        diff = abs((a - th + 180.0) % 360.0 - 180.0)
        ok = d <= 1000.0 and diff <= 90.0
        if ok:
            good.append((pm, fw, sd))
        ax.plot([pm[0]], [pm[1]], "o", ms=7, mfc=(C4 if ok else "none"),
                mec=(C4 if ok else "0.6"), mew=1.4, zorder=5)
    for pm, fw, sd in good[:1]:
        ax.plot([p0[0], pm[0]], [p0[1], pm[1]], "-", color=C4, lw=1.6, zorder=4)
    ax.annotate("8 个候选补测点（绿色=可检出且交会角良态）\n"
                "首次尝试 (0,700) 即成功：交会角 64.3°、定位后一次清除",
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=9.2,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2200, 2200)
    ax.set_ylim(-3000, 1200)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("单观测主动补测的几何：用横向偏置换取良态交会角")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(alpha=0.2)
    save(fig, "fig_single_fix")


if __name__ == "__main__":
    W, ncert = waypoints()
    draw_path("fig_q3_path", "practice_0911_run21_v17c_confirm_run6_p3.json",
              "问题三演练过程：16 源全部清除（行走轨迹与清除位置）",
              W[:0] + ring(990, 15), 15,
              "16 源全部清除\n虚拟时间 4762.1 s\n平均 297.6 s/源", cert_label="建证集")
    progress("fig_q3_progress",
             [("practice_0911_run1_X8GD_run6_p3.json", "旧19点\n12源"),
              ("practice_0911_run7_CH3A_run6_p3.json", "旧混合\n10源"),
              ("practice_0911_run12_ring15_run6_p3.json", "新单环\n10源"),
              ("practice_0911_run18_v12_run6_p3.json", "新单环\n16源"),
              ("practice_0911_run21_v17c_confirm_run6_p3.json", "新单环\n16源(最新)")],
             "问题三演练：清除进度与无效尾段（新旧策略对照）")
    draw_path("fig_q4_path", "practice_0911_q4run11_WABX_run6_p4.json",
              "问题四演练过程：15 源全部清除（证书前缀 + 补给点）",
              W, ncert,
              "15 源全部清除\n虚拟时间 6254.2 s\n平均 416.9 s/源")
    progress("fig_q4_progress",
             [("practice_0911_q4run1_DWUU_run6_p4.json", "旧55点\n10源"),
              ("practice_0911_q4run4_cert31_run6_p4.json", "旧立即清\n12源"),
              ("practice_0911_q4run8_v12_run6_p4.json", "新顺路\n13源"),
              ("practice_0911_q4run11_WABX_run6_p4.json", "新顺路\n15源"),
              ("practice_0911_q4run15_v17c_confirm_run6_p4.json", "新最新\n13源")],
             "问题四演练：清除进度与无效尾段（新旧策略对照）")
    fig_stress()
    fig_single_fix()
    print("[done]")
