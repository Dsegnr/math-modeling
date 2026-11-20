"""Q3 单环布局的最终选型（同种子、长样本，比较半径与点数）"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import grid, ring, cert


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    X, Y = grid()
    rng = np.random.default_rng(4242)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print("%d 局/配置" % nrun)
    print(" %-22s %6s %8s %8s %8s" % ("布局", "点数", "盲区/m", "总时间/s", "s/源"))
    res = []
    for R in (975, 985, 990, 995, 1000):
        for n in (13, 14, 15, 16):
            pts = ring(R, n)
            l1, l2, worst, blind = cert(pts, X, Y)
            if not (l1 and l2):
                continue
            W = Q.nn_tour([tuple(map(float, p)) for p in pts])
            masks = Q.build_masks(W)
            rows = [Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases]
            tt = np.mean([r["t"] for r in rows])
            per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
            ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
            res.append((tt, R, n, blind, per, ok))
    for tt, R, n, blind, per, ok in sorted(res):
        print(" 单环 %4d x %2d %s %6d %8.1f %8.0f %8.0f" %
              (R, n, "OK" if ok > 99.99 else "%.1f%%" % ok, n, blind, tt, per))


if __name__ == "__main__":
    main()
