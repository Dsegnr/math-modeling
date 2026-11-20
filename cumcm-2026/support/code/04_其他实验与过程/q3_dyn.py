"""
Q3「顺序自适应」策略验证：证书集固定不变，但每步重算"下一个航点 / 先去清哪个源"。
对照：固定最近邻顺序 + 最优绕道点顺路清除（现行）。
用法：python q3_dyn.py [局数]
"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import grid, ring, cert


def rep(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-32s %7.1f%% %8.0f %8.0f %8.0f %8.0f %7.0f %6.0f %7.0f" %
          (label, ok, tt.mean(), per, np.mean([r["mv"] for r in rows]),
           np.mean([r["me"] for r in rows]), np.mean([r["sw"] for r in rows]),
           np.mean([r["cl"] for r in rows]), np.mean([r["n_meas"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    X, Y = grid()
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    layouts = {"S17(17点)": S17, "R15(单环990x15)": ring(990, 15)}
    rng = np.random.default_rng(9090)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print(" %-32s %8s %8s %8s %8s %8s %7s %6s %7s" %
          ("配置（%d 局）" % nrun, "清除率", "总时间", "s/源", "移动", "检测", "切频", "清除", "measure"))
    for name, pts in layouts.items():
        W = Q.nn_tour([tuple(map(float, p)) for p in pts])
        masks = Q.build_masks(W)
        l1, l2, worst, blind = cert(pts, X, Y)
        rep([Q.run_policy(W, c, ncert=len(W), masks=masks) for c in cases], name + " 固定顺序(现行)")
        for nb in (250.0, 400.0, 700.0, 1e9):
            rep([Q.run_policy_dyn(W, c, masks=masks, near_bonus=nb) for c in cases],
                name + " 顺序自适应 nb=%s" % ("inf" if nb > 1e8 else "%.0f" % nb))
        if name.startswith("R15"):
            for co in (2, 4, 5):
                rep([Q.run_policy(W, c, ncert=len(W), masks=masks, cull_obs=co) for c in cases],
                    name + " cull_obs=%d" % co)
            rep([Q.run_policy(W, c, ncert=len(W), masks=masks, side_clear=False) for c in cases],
                name + " 关闭顺路清除")
            Wc, ncore = Q.cover_first_order(W, masks[0], masks[1])
            mc = Q.build_masks(Wc)
            rep([Q.run_policy(Wc, c, ncert=len(Wc), masks=mc, dyn_stop=True) for c in cases],
                name + " 覆盖子集前置+动态终止（%d点前缀）" % ncore)


if __name__ == "__main__":
    main()