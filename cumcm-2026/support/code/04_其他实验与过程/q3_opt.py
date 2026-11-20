"""
Q3 航点集「联合最优化」：以离线复现器的平均总虚拟时间为目标，直接优化 15 个航点坐标。

这是相对"手工设计环"的算法升级：目标函数就是最终评价指标本身，
约束为覆盖证书（盲区 <= 1000 m 且全域 >=2 可测），采用确定性爬山 + 随机重启。
用法：python q3_opt.py [评估局数] [迭代次数]
"""
import os
import sys
import math
import json
import numpy as np

import q3_offline_eval as Q
from q3_tune import ring
from q3_sweep import cert
from q3_tune import grid


def objective(pts, cases, masks_cache={}):
    X, Y = masks_cache["XY"]
    l1, l2, worst, blind = cert(pts, X, Y)
    if not (l1 and l2):
        return None
    W = Q.nn_tour([tuple(map(float, p)) for p in pts])
    key = tuple((round(p[0], 1), round(p[1], 1)) for p in W)
    if key not in masks_cache:
        masks_cache[key] = Q.build_masks(W)
    masks = masks_cache[key]
    rows = [Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases]
    bad = sum(1 for r in rows if r["cleared"] != r["n_src"])
    return sum(r["t"] for r in rows) / len(rows) + bad * 5000.0


def main():
    ncase = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    nit = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    X, Y = grid(40.0)
    rng = np.random.default_rng(31337)
    cases = [Q.gen_case(np.random.default_rng(1000 + i)) for i in range(ncase)]
    cache = {"XY": (X, Y)}
    cur = [list(p) for p in ring(990, 15)]
    best = objective([tuple(p) for p in cur], cases, cache)
    print("起点（单环 990x15）目标值 = %.0f s（%d 局）" % (best, ncase))
    sigma = 60.0
    acc = 0
    for it in range(nit):
        k = int(rng.integers(0, len(cur)))
        old = list(cur[k])
        cur[k][0] += rng.normal(0, sigma)
        cur[k][1] += rng.normal(0, sigma)
        v = objective([tuple(p) for p in cur], cases, cache)
        if v is not None and v < best - 1e-9:
            best = v
            acc += 1
        else:
            cur[k] = old
        if (it + 1) % 40 == 0:
            sigma = max(15.0, sigma * 0.85)
            print("  迭代 %3d：最优 %.0f s（接受 %d 次，sigma=%.0f）" % (it + 1, best, acc, sigma))
    W = Q.nn_tour([tuple(p) for p in cur])
    print("\n最终航点集（%d 点），目标 %.0f s" % (len(W), best))
    for p in W:
        print("   (%8.1f, %8.1f)  r=%.0f" % (p[0], p[1], math.hypot(*p)))
    json.dump({"n": len(W), "obj": best, "waypoints": [[round(p[0], 1), round(p[1], 1)] for p in W]},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch", "q3_opt_ring.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch", "q3_opt_ring.json")
    print("[out] %s" % out)


if __name__ == "__main__":
    main()