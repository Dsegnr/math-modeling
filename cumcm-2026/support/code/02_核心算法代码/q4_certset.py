"""
Q4 提前终止的严格化：55 点布局的「L1 最小检测证书集」

判据（L1 一重可见，只用 r_min = 1000 m 的保底接收半径）：
    对目标圆域内任意一点 x，记 P_x(S) = { p in S : ||p - x|| <= r_min }。
    源在 x 处朝向任意，只有当某个可见测点落在源的 +-90度 覆盖扇区内才会被检出。
    因此「无论源朝向如何都至少被检出一次」等价于
        maxgap( angles of P_x(S) - x ) <= 180度   （P_x 的角度集合不存在 > 180度 的空隙）
    即 Delta_max(x) <= 180度，与 x in conv(P_x) 等价。

用途：把 run6_robust.py(p4) 的终止判据由
        「已检出源全清 + 连续 8 点无新发现」（启发式，理论上可漏检）
      换成
        「证书集 S 已全部走完 + 已检出源全清」（有证书，不漏检）

输出：_scratch/certset_p4.json、output/tables/tab_q4_certset.csv
"""
import os
import math
import json
import csv
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
TABDIR = os.path.join(BASE, "output", "tables")
SCRATCH = os.path.join(BASE, "_scratch")
os.makedirs(TABDIR, exist_ok=True)
os.makedirs(SCRATCH, exist_ok=True)

ARENA = 1800.0
RMIN = 1000.0
GAP_MAX = 180.0          # L1 判据阈值（度）


def load_layout():
    with open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8") as f:
        data = json.load(f)
    pts = [tuple(map(float, p)) for p in data["waypoints"]]
    return pts, data.get("worst_gap_deg")


def grid(step):
    g = np.arange(-ARENA, ARENA + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= ARENA ** 2
    return X[m], Y[m]


def matrices(P, X, Y):
    W = np.array(P)
    D = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
    A = np.degrees(np.arctan2(Y[:, None] - W[None, :, 1], X[:, None] - W[None, :, 0])) % 360.0
    return D, A


def feasible(D, A, S):
    """返回 (是否全域满足 L1, 全域最少可见测点数, 全域最大角隙/度)"""
    vis = D[:, S] <= RMIN
    cnt = vis.sum(axis=1)
    if np.any(cnt < 2):
        # 可见点 <2 时角度覆盖最多 180度，不满足
        return False, int(cnt.min()), 360.0
    ang = np.where(vis, A[:, S], np.nan)
    ang.sort(axis=1)
    idx = np.arange(len(cnt))
    first = ang[:, 0]
    last = ang[idx, np.maximum(cnt - 1, 0)]
    d = np.diff(ang, axis=1)
    inner = np.where(np.isnan(d), -1.0, d).max(axis=1)
    wrap = 360.0 - (last - first)
    maxgap = np.maximum(inner, wrap)
    return bool(np.all(maxgap <= GAP_MAX + 1e-9)), int(cnt.min()), float(maxgap.max())


def greedy_delete(D, A, S):
    S = list(S)
    improved, it = True, 0
    while improved and len(S) > 2:
        improved = False
        it += 1
        for j in list(S):
            cand = [s for s in S if s != j]
            if len(cand) < 2:
                continue
            ok, _, _ = feasible(D, A, cand)
            if ok:
                S = cand
                improved = True
        print("  第 %d 轮删除后剩 %d 点" % (it, len(S)), flush=True)
        if it > 8:
            break
    return S


def main():
    P, worst_gap_json = load_layout()
    print("Q4 55 点布局：L1 最小检测证书集", flush=True)
    print("  布局点数 %d，waypoints_p4.json 记录最坏角隙 %.1f度" % (len(P), worst_gap_json), flush=True)

    X, Y = grid(20.0)
    print("  全域网格：%d 点（步长 20 m）" % len(X), flush=True)
    D, A = matrices(P, X, Y)

    full = list(range(len(P)))
    ok, mc, mg = feasible(D, A, full)
    print("  全部 55 点：L1 通过=%s | 最少可见 %d 点 | 最坏角隙 %.1f度" % (ok, mc, mg), flush=True)

    S = greedy_delete(D, A, full)
    ok, mc, mg = feasible(D, A, S)
    print("\n  证书集：%d 点 | 20 m 网格 L1 通过=%s | 最少可见 %d | 最坏角隙 %.1f度"
          % (len(S), ok, mc, mg), flush=True)

    X2, Y2 = grid(10.0)
    D2, A2 = matrices(P, X2, Y2)
    ok2, mc2, mg2 = feasible(D2, A2, S)
    print("  10 m 网格复核（%d 点）：L1 通过=%s | 最少可见 %d | 最坏角隙 %.1f度"
          % (len(X2), ok2, mc2, mg2), flush=True)

    idx = sorted(S)
    last_idx = idx[-1] + 1
    print("  证书集在既有巡回顺序中的序号: %s" % [i + 1 for i in idx], flush=True)
    print("  => 新终止判据最早在该巡回第 %d 个航点之后生效（共 %d 点）" % (last_idx, len(P)), flush=True)

    pts = [P[i] for i in idx]
    print("\n  证书集坐标（按巡回顺序）:", flush=True)
    for k, q in zip([i + 1 for i in idx], pts):
        print("    巡回第 %2d 点  (%8.1f, %8.1f)   r=%.0f" % (k, q[0], q[1], math.hypot(*q)), flush=True)

    json.dump({"n": len(S), "gap_max_deg": GAP_MAX, "r_min": RMIN,
               "min_visible_20m": mc, "maxgap_20m": round(mg, 2),
               "min_visible_10m": mc2, "maxgap_10m": round(mg2, 2),
               "cert_indices": [i + 1 for i in idx],
               "cert_waypoints": [[round(q[0], 1), round(q[1], 1)] for q in pts]},
              open(os.path.join(SCRATCH, "certset_p4.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    with open(os.path.join(TABDIR, "tab_q4_certset.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["项目", "值"])
        w.writerow(["布局航点总数", len(P)])
        w.writerow(["L1 角隙阈值 /度", GAP_MAX])
        w.writerow(["保底接收半径 r_min / m", RMIN])
        w.writerow(["证书集点数", len(S)])
        w.writerow(["20 m 网格最少可见测点数", mc])
        w.writerow(["20 m 网格最大角隙 /度", round(mg, 1)])
        w.writerow(["10 m 网格最少可见测点数", mc2])
        w.writerow(["10 m 网格最大角隙 /度", round(mg2, 1)])
        w.writerow(["证书集在巡回中的最大序号", last_idx])
        w.writerow([])
        w.writerow(["巡回序号", "航点 x / m", "航点 y / m"])
        for k, q in zip([i + 1 for i in idx], pts):
            w.writerow([k, round(q[0], 1), round(q[1], 1)])
    print("\n  [tab] tab_q4_certset.csv | _scratch/certset_p4.json", flush=True)


if __name__ == "__main__":
    main()