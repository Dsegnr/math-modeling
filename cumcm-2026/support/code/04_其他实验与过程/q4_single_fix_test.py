"""
离线验证「单观测主动补测」分支的几何：
  取已知的退化案例（源在 (0,-1800) 朝正南，证书段只有 1 个点可见），
  代入 run6_robust 的 4 个候选偏移，检查：
    (1) 补测点能否收到该源（距离 <= r_i 且落在 +-90度 覆盖角内）；
    (2) 两条示向度的交会角是否 >=30度（良态）。
用法：python q4_single_fix_test.py
"""
import os
import math
import json

BASE = os.path.dirname(os.path.abspath(__file__))
CAND = ((0.0, 700.0), (0.0, -700.0), (300.0, 700.0), (300.0, -700.0),
        (500.0, 700.0), (500.0, -700.0), (800.0, 500.0), (800.0, -500.0))


def bearing(p, q):
    return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 360.0


def in_beam(p, src, theta, rmin, rmax):
    d = math.hypot(src[0] - p[0], src[1] - p[1])
    if d > rmax:
        return False, d, None
    a = bearing(src, p)          # 从"源"指向"航点"的方向，用于判定是否落在源的覆盖角内
    diff = abs((a - theta + 180.0) % 360.0 - 180.0)
    return (diff <= 90.0 and d <= rmax), d, a


def main():
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    W = [tuple(map(float, p)) for p in d["waypoints"]][:int(d["n_cert"])]
    cases = [((0.0, -1800.0), 270.0), ((0.0, -1800.0), 250.0), ((1800.0, 0.0), 0.0),
             ((1273.0, 1273.0), 45.0)]
    for src, th in cases:
        vis = []
        for i, p in enumerate(W, 1):
            ok, dist, a = in_beam(p, src, th, 0.0, 1000.0)
            if ok:
                vis.append((i, p, dist, a))
        print("源 (%6.0f,%6.0f) 朝向 %3.0f度 | 证书段可见点 %d 个：%s"
              % (src[0], src[1], th, len(vis), [v[0] for v in vis]))
        if len(vis) != 1:
            print("     （非退化案例，跳过补测验证）")
            continue
        i0, p0, d0, a0 = vis[0]
        print("     唯一可见点：idx=%d (%7.1f,%7.1f) 距离=%.1f 方位=%.1f度" % (i0, p0[0], p0[1], d0, a0))
        for fw, sd in CAND:
            t = math.radians(bearing(p0, src))   # 与 run6_robust 一致：沿"测点->源"方位前移
            pm = (p0[0] + fw * math.cos(t) - sd * math.sin(t),
                  p0[1] + fw * math.sin(t) + sd * math.cos(t))
            for rmin, rmax in ((1000.0, 1000.0), (1000.0, 1500.0)):
                ok, dist, a1 = in_beam(pm, src, th, rmin, rmax)
                if not ok:
                    continue
                # 源处两条方向的夹角（交会角）
                v0 = (p0[0] - src[0], p0[1] - src[1])
                v1 = (pm[0] - src[0], pm[1] - src[1])
                c = (v0[0] * v1[0] + v0[1] * v1[1]) / (math.hypot(*v0) * math.hypot(*v1))
                ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
                if ang > 90:
                    ang = 180 - ang
                print("     候选 fw=%.0f sd=%.0f -> 补测点 (%7.1f,%7.1f) r=%.0f m 可检出 交会角=%.1f度 %s"
                      % (fw, sd, pm[0], pm[1], rmax, ang, "良态" if ang >= 30 else "偏小"))
        print()


if __name__ == "__main__":
    main()