"""
加入示向度噪声后，对比"按观测数停测"与"按观测几何良态停测"。
用法：python q3_noise.py [局数]
"""
import sys
import numpy as np

import q3_offline_eval as Q
from q3_tune import ring


def rep(rows, label):
    tt = np.array([r["t"] for r in rows])
    ok = 100 * np.mean([r["cleared"] == r["n_src"] for r in rows])
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print(" %-30s %7.1f%% %8.0f %8.0f %7.1f %6.0f %7.0f" %
          (label, ok, tt.mean(), per, np.mean([r["n_miss"] for r in rows]),
           np.mean([r["n_meas"] for r in rows]), np.mean([r["sw"] for r in rows])))


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    W = Q.nn_tour([tuple(map(float, p)) for p in ring(990, 15)])
    masks = Q.build_masks(W)
    rng = np.random.default_rng(8080)
    cases = [Q.gen_case(rng) for _ in range(nrun)]
    print(" %-30s %8s %8s %8s %7s %6s %7s" %
          ("配置", "清除率", "总时间", "s/源", "清除失败", "measure", "切频"))
    for sg in (0.0, 0.05, 0.10):
        print(" -- 示向度噪声 sigma = %.2f度 --" % sg)
        for lab, kw in (("cull=2（仅按条数）", dict(cull_obs=2)),
                        ("cull=3（仅按条数）", dict(cull_obs=3)),
                        ("cull=2 + 几何良态30度", dict(cull_obs=2, wc_gamma=30.0)),
                        ("cull=2 + 几何良态20度", dict(cull_obs=2, wc_gamma=20.0))):
            rows = [Q.run_policy(W, c, ncert=len(W), masks=masks, bear_sigma=sg, seed=i, **kw)
                    for i, c in enumerate(cases)]
            rep(rows, lab)


if __name__ == "__main__":
    main()