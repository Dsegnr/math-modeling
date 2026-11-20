"""Q4 策略变体离线比选：停测阈值、单观测补测、清除策略、证书段长度"""
import sys
import numpy as np

import q4_offline_eval as Q


def rep(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-34s %7.1f%% %8.0f %8.0f %8.0f %8.0f %8.0f %7.0f %6.2f" %
          (label, ok, tt.mean(), per, np.mean([r["mv"] for r in rows]),
           np.mean([r["me"] for r in rows]), np.mean([r["sw"] for r in rows]),
           np.mean([r["n_meas"] for r in rows]), np.mean([r["n_miss"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    W, ncert = Q.load_W()
    rng = np.random.default_rng(2718)
    cases = [Q.gen_case(rng, "uniform") for _ in range(nrun)]
    print(" %-34s %8s %8s %8s %8s %8s %7s %6s" %
          ("配置（%d 局）" % nrun, "清除率", "总时间", "s/源", "移动", "检测", "measure", "失败"))
    rep([Q.run_p4(W, c, ncert, seed=i) for i, c in enumerate(cases)], "基线（现行：cull=3+补测）")
    rep([Q.run_p4(W, c, ncert, seed=i, cull=2) for i, c in enumerate(cases)], "cull=2（2 条即停测）")
    rep([Q.run_p4(W, c, ncert, seed=i, cull=4) for i, c in enumerate(cases)], "cull=4")
    rep([Q.run_p4(W, c, ncert, seed=i, single_fix=False) for i, c in enumerate(cases)], "关闭单观测补测")
    rep([Q.run_p4(W, c, ncert, seed=i, cull=2, single_fix=True) for i, c in enumerate(cases)],
        "cull=2 + 补测")


if __name__ == "__main__":
    main()
