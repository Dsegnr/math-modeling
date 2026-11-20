"""
Q3 压力测试配图（对应 Q4 的 fig_stress 规格）
  fig_q3_stress           走通轨迹 + 4 点稀疏建证集 + 单观测补测事件
  fig_q3_stress_progress  步图：累计清除随虚拟时间的推进，并标出 6 次补测
"""
import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

BASE = os.path.dirname(os.path.abspath(__file__))
FIGD = os.path.join(BASE, "figures")
ARCH = os.path.join(BASE, "_scratch", "archive")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300
ARENA = 1800.0
C1, C2, C3, C4 = "#1f4e79", "#c0504d", "#4f81bd", "#9bbb59"
LOG = "stress_p3_run2_ring4_PASS_run6_p3.json"
RING4 = [(990.0, 0.0), (0.0, 990.0), (-990.0, 0.0), (0.0, -990.0)]
FIX_CH = {2: (694, 1522), 10: (-1632, 199), 13: (804, 1472),
          17: (186, -1331), 19: (1064, -168), 20: (-179, 1334)}


def save(fig, name):
    for e in ("png", "pdf"):
        fig.savefig(os.path.join(FIGD, "%s.%s" % (name, e)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig]", name, flush=True)


def trace(d):
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


def main():
    d = json.load(open(os.path.join(ARCH, LOG), encoding="utf-8"))
    pts = trace(d)
    cl = [p for p in pts if p[3] == "success"]
    fig, ax = plt.subplots(figsize=(7.6, 7.0))
    ax.add_patch(Circle((0, 0), ARENA, fill=False, ec="0.45", lw=1.3, ls="--"))
    ax.add_patch(Circle((0, 0), 1000, fill=False, ec="0.8", lw=1.0, ls=":"))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=C3, lw=1.0, alpha=0.85,
            zorder=2, label="行走轨迹")
    ax.plot([q[0] for q in RING4], [q[1] for q in RING4], "o", ms=11, color=C1, zorder=6,
            label="建证集仅 4 点（90° 间距，人为削弱）")
    ax.plot([p[0] for p in cl], [p[1] for p in cl], "*", ms=14, color=C2, zorder=5,
            label="清除成功（%d 个）" % len(cl))
    for ch, (bx, by) in sorted(FIX_CH.items()):
        ax.plot([bx], [by], "D", ms=10, mfc="none", mec="k", mew=1.7, zorder=8)
        ax.annotate("ch%d" % ch, (bx, by), textcoords="offset points", xytext=(9, 7),
                    fontsize=9.0, bbox=dict(fc="white", ec="0.7"))
    ax.plot([0], [0], "ks", ms=8, zorder=7, label="起点（原点）")
    ax.annotate("建证集削到 4 点，大量源只能被 1 个点看到\n"
                "补测分支触发 6 次，全部定位并清除（11/11 全清）",
                xy=(0.03, 0.03), xycoords="axes fraction", fontsize=9.0,
                bbox=dict(fc="white", ec="0.7"))
    ax.set_aspect("equal")
    ax.set_xlim(-2450, 2450)
    ax.set_ylim(-2450, 2450)
    ax.set_xlabel("$x$ / m")
    ax.set_ylabel("$y$ / m")
    ax.set_title("问题三压力测试：稀疏建证集逼出「单观测」情形")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=8.4, framealpha=0.95)
    ax.grid(alpha=0.2)
    fig.subplots_adjust(bottom=0.18)
    save(fig, "fig_q3_stress")

    fig, ax = plt.subplots(figsize=(11.0, 4.9))
    ts, cs, c = [], [], 0
    for p in pts:
        if p[3] == "success":
            c += 1
            ts.append(p[5])
            cs.append(c)
    t1 = max(p[5] for p in pts)
    ax.step([0.0] + ts + [t1], [0] + cs + [cs[-1]], where="post", color=C1, lw=2.2,
            label="累计清除源数")
    fix_t = {}
    for ch, _ in FIX_CH.items():
        for p in cl:
            if p[4] == ch:
                fix_t[ch] = p[5]
    for ch, t in sorted(fix_t.items(), key=lambda kv: kv[1]):
        ax.plot([t], [cs[ts.index(t)]], "D", ms=8, mfc="none", mec=C2, mew=1.8, zorder=6)
        ax.annotate("补测 ch%d" % ch, (t, cs[ts.index(t)]), textcoords="offset points",
                    xytext=(6, -14), fontsize=8.6, color=C2)
    ax.axvline(1830.0, color="0.5", ls="--", lw=1.1)
    ax.annotate("建证集（4 点）走完\n$t=1830$ s", xy=(1830.0, 1.0), fontsize=9,
                xytext=(1980, 3.0), arrowprops=dict(arrowstyle="->", color="0.5"))
    ax.set_xlabel("虚拟时间 / s")
    ax.set_ylabel("累计清除源数 / 个")
    ax.set_title("问题三压力测试步图：建证集走完后由「补测 + 收尾」完成剩余清除")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_ylim(0, 12.5)
    ax.grid(alpha=0.25)
    save(fig, "fig_q3_stress_progress")
    print("[done]")


if __name__ == "__main__":
    main()
