"""
把 Q4 证书段换成"时间代理最优"的 25 点结构（原点 + 内环 950x8 + 外环 1850x16），
原 31 点证书段之后的 50 个 L2/L3 补给点保留，并按最近邻接续排序。
"""
import os
import json
import math
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE, "waypoints_p4.json")
ARCH = os.path.join(BASE, "_scratch", "archive")


def ring(r, n, off=0.0):
    return [(r * math.cos(math.radians(360.0 * k / n + off)),
             r * math.sin(math.radians(360.0 * k / n + off))) for k in range(n)]


def nn_tour(pts, start=(0.0, 0.0)):
    rem, cur, out = list(pts), start, []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
        out.append(j)
        cur = j
        rem.remove(j)
    return out


def tour_len(pts):
    s, cur = 0.0, (0.0, 0.0)
    for p in pts:
        s += math.hypot(p[0] - cur[0], p[1] - cur[1])
        cur = p
    return s


def main():
    old = json.load(open(DST, encoding="utf-8"))
    old_tour = [tuple(map(float, p)) for p in old["waypoints"]]
    n_old_cert = int(old["n_cert"])
    supply = [p for p in old_tour[n_old_cert:]]
    cert = nn_tour([(0.0, 0.0)] + ring(950.0, 8) + ring(1850.0, 16))
    supply = nn_tour(supply, cert[-1])
    tour = cert + supply
    os.makedirs(ARCH, exist_ok=True)
    bak = os.path.join(ARCH, "waypoints_p4_v2_81pt_cert31.json")
    if os.path.exists(DST) and not os.path.exists(bak):
        shutil.copy2(DST, bak)
    out = {
        "source": "Q4 证书巡回 v3：证书段 %d 点（原点 + 内环 950 mx8 + 外环 1850 mx16），"
                  "按「总时间代理 J = 巡回/5 + 点数x未现频道扫描」最优；"
                  "20 mx2度 与 10 mx1度 (990 m, 89度) 复核均 0 未覆盖；其后为原 L2/L3 补给点。"
                  % len(cert),
        "n": len(tour),
        "n_cert": len(cert),
        "cert_len_m": round(tour_len(cert), 1),
        "approx_tour_len_m": round(tour_len(tour), 1),
        "worst_gap_deg": None,
        "waypoints": [[round(x, 1), round(y, 1)] for x, y in tour],
    }
    json.dump(out, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[write] %s：%d 点（证书段 %d 点 / %.0f m；全巡回 %.0f m）"
          % (DST, len(tour), len(cert), tour_len(cert), tour_len(tour)))
    print("证书段坐标：")
    for p in cert:
        print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))


if __name__ == "__main__":
    main()