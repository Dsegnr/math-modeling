"""
把 q4_detect_cover.py 得到的「证书前缀 + 补给点」巡回写入 waypoints_p4.json
（原 55 点布局自动备份到 _scratch/archive/）
"""
import os
import json
import shutil
import math
import csv
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "_scratch", "certset_p4_cover.json")
DST = os.path.join(BASE, "waypoints_p4.json")
ARCH = os.path.join(BASE, "_scratch", "archive")


def worst_gap(pts, step=20.0, rmin=1000.0):
    g = np.arange(-1800.0, 1800.0 + step, step)
    GX, GY = np.meshgrid(g, g)
    m = GX ** 2 + GY ** 2 <= 1800.0 ** 2
    X, Y = GX[m], GY[m]
    W = np.array(pts)
    d = np.sqrt((X[:, None] - W[None, :, 0]) ** 2 + (Y[:, None] - W[None, :, 1]) ** 2)
    A = np.degrees(np.arctan2(Y[:, None] - W[None, :, 1], X[:, None] - W[None, :, 0])) % 360.0
    vis = d <= rmin
    cnt = vis.sum(axis=1)
    ang = np.where(vis, A, np.nan)
    ang.sort(axis=1)
    idx = np.arange(len(cnt))
    first = ang[:, 0]
    last = ang[idx, np.maximum(cnt - 1, 0)]
    dd = np.diff(ang, axis=1)
    inner = np.where(np.isnan(dd), -1.0, dd).max(axis=1)
    wrap = 360.0 - (last - first)
    return float(np.maximum(inner, wrap).max())


def main():
    os.makedirs(ARCH, exist_ok=True)
    d = json.load(open(SRC, encoding="utf-8"))
    if os.path.exists(DST):
        bak = os.path.join(ARCH, "waypoints_p4_v1_55pt.json")
        if not os.path.exists(bak):
            shutil.copy2(DST, bak)
            print("[backup] %s" % bak)
    tour = d["tour"]
    out = {
        "source": "Q4 全域保证检出证书巡回：前 %d 点为 (位置x朝向) 全覆盖证书集，"
                  "其后为 L2/L3 补给点。证书集在 5 mx1度 网格（40.7 万位置 x 360 朝向）上零漏覆盖。"
                  % d["n_cert"],
        "n": len(tour),
        "n_cert": d["n_cert"],
        "cert_len_m": d["cert_len_m"],
        "approx_tour_len_m": d["tour_len_m"],
        "worst_gap_deg": round(worst_gap(tour), 1),
        "waypoints": [[round(float(x), 1), round(float(y), 1)] for x, y in tour],
    }
    json.dump(out, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[write] %s：%d 点（证书前缀 %d 点，前缀里程 %.0f m，全域最坏角隙 %.1f度）"
          % (DST, len(tour), d["n_cert"], d["cert_len_m"], out["worst_gap_deg"]))
    # 同步 output/tables 中的证书表，保证文档、表、图三者顺序一致（以本脚本读入的证书为准）
    tab = os.path.join(BASE, "output", "tables", "tab_q4_detect_cover.csv")
    os.makedirs(os.path.dirname(tab), exist_ok=True)
    with open(tab, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["项目", "值"])
        w.writerow(["保底接收半径 r_min / m", 990.0])
        w.writerow(["覆盖半角（留余量）/ 度", 89.0])
        w.writerow(["保证检出证书集点数 K*", d["n_cert"]])
        w.writerow(["L2/L3 补充点数", len(tour) - d["n_cert"]])
        w.writerow(["新巡回总点数", len(tour)])
        w.writerow(["证书前缀里程 / m", round(d["cert_len_m"], 1)])
        w.writerow(["复核 5 m x 1度 网格未覆盖对数", d["miss_check"].get("5 m x 1deg", -1)])
        w.writerow([])
        w.writerow(["证书前缀序号", "航点 x / m", "航点 y / m", "到原点距离 / m"])
        for i, (x, y) in enumerate(tour[:d["n_cert"]], 1):
            w.writerow([i, round(float(x), 1), round(float(y), 1), round(math.hypot(x, y), 1)])
    print("[tab] %s" % tab)


if __name__ == "__main__":
    main()