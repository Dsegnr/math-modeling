"""离线筛选：把「补测」触发条件从"仅 1 条观测"扩展到"观测几何病态（交会角 < 阈值）"是否有收益"""
import sys
import numpy as np

import q4_offline_eval as Q


def rep(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-32s %7.1f%% %8.0f %8.0f %8.0f %8.0f %8.0f %8.0f %7.0f" %
          (label, ok, tt.mean(), per, np.mean([r["mv"] for r in rows]),
           np.mean([r["me"] for r in rows]), np.mean([r["sw"] for r in rows]),
           np.mean([r["cl"] for r in rows]), np.mean([r["n_meas"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    W, ncert = Q.load_W()
    rng = np.random.default_rng(31415)
    cases = [Q.gen_case(rng, "uniform") for _ in range(nrun)]
    print(" %-32s %8s %8s %8s %8s %8s %8s %7s" %
          ("配置（%d 局）" % nrun, "清除率", "总时间", "s/源", "移动", "检测", "切频", "measure"))
    rep([Q.run_p4(W, c, ncert, seed=i) for i, c in enumerate(cases)], "基线（仅 1 条观测才补测）")
    for g in (20.0, 30.0, 45.0):
        rep([Q.run_p4(W, c, ncert, seed=i, geom_fix=g) for i, c in enumerate(cases)],
            "扩展补测：交会角 < %.0f度 也补测" % g)


if __name__ == "__main__":
    main()