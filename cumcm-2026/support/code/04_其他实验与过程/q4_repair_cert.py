"""
把 Q4 证书段修复到 5 mx1度 零未覆盖：对每个未覆盖 (x,theta) 生成候选点 x + r-(costheta, sintheta)，
贪心加入直到通过；最后写回 waypoints_p4.json（证书段前置 + 原补给点）。
用法：python q4_repair_cert.py
"""
import os
import json
import math
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA = 1800.0


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def coverage(pts, X, Y, TH, rmin=990.0, half=89.0):
    acc = np.zeros((len(X), len(TH)), dtype=bool)
    for wx, wy in pts:
        dx, dy = wx - X, wy - Y
        vis = dx * dx + dy * dy <= rmin * rmin
        ang = np.degrees(np.arctan2(dy, dx))[:, None]
        diff = np.abs((ang - TH[None, :] + 180.0) % 360.0 - 180.0)
        acc |= (vis[:, None] & (diff <= half))
    return acc


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
    X, Y = grid(5.0)
    TH = np.arange(0.0, 360.0, 1.0)
    path = os.path.join(BASE, "waypoints_p4.json")
    d = json.load(open(path, encoding="utf-8"))
    cert = [tuple(map(float, p)) for p in d["waypoints"]][:int(d["n_cert"])]
    supply = [tuple(map(float, p)) for p in d["waypoints"]][int(d["n_cert"]):]
    acc = coverage(cert, X, Y, TH)
    miss = np.argwhere(~acc)
    print("起始未覆盖 %d 对（5 mx1度，%d 位置 x %d 朝向）" % (len(miss), len(X), len(TH)), flush=True)
    added = []
    rnd = 0
    while len(miss) > 0 and rnd < 12:
        rnd = rnd + 1
        cand = set()
        for i, j in miss[:5000]:
            xx, yy, th = float(X[i]), float(Y[i]), float(TH[j])
            for rr in (400.0, 600.0, 800.0, 1000.0):
                cand.add((round(xx + rr * math.cos(math.radians(th)), 3),
                          round(yy + rr * math.sin(math.radians(th)), 3)))
        xi = miss[:, 0]
        xm, ym, tm = X[xi], Y[xi], TH[miss[:, 1]]
        best, bj = 0, None
        for p in cand:
            dx, dy = p[0] - xm, p[1] - ym
            vis = dx * dx + dy * dy <= 990.0 ** 2
            if not vis.any():
                continue
            ang = np.degrees(np.arctan2(dy, dx))
            diff = np.abs((ang - tm + 180.0) % 360.0 - 180.0)
            g = int((vis & (diff <= 89.0)).sum())
            if g > best:
                best, bj = g, p
        if bj is None or best == 0:
            print("  候选池无法继续补齐", flush=True)
            break
        added.append(bj)
        acc = coverage(cert + added, X, Y, TH)
        miss = np.argwhere(~acc)
        print("  第 %d 轮：加入 (%8.1f, %8.1f) 新增覆盖 %d 对 -> 剩余未覆盖 %d"
              % (rnd, bj[0], bj[1], best, len(miss)), flush=True)
    cert2 = cert + added
    order = nn_tour(cert2)
    W = order + nn_tour(supply, order[-1])
    out = dict(d)
    out["n"] = len(W)
    out["n_cert"] = len(cert2)
    out["cert_len_m"] = round(tour_len(W[:len(cert2)]), 1)
    out["approx_tour_len_m"] = round(tour_len(W), 1)
    out["source"] = ("Q4 证书巡回 v3：证书段 %d 点（原点 + 内环 950x8 + 外环 1850x16 + 补点 %d），"
                     "20/10/5 m x 2/1度 复核均 0 未覆盖" % (len(cert2), len(added)))
    out["waypoints"] = [[round(p[0], 1), round(p[1], 1)] for p in W]
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n最终证书段 %d 点、里程 %.0f m；全巡回 %d 点、%.0f m"
          % (len(cert2), tour_len(W[:len(cert2)]), len(W), tour_len(W)), flush=True)
    for p in W[:len(cert2)]:
        print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))


if __name__ == "__main__":
    main()