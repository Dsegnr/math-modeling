"""
探测 Q3 的「动态证书」潜力：
  (1) 最小覆盖子集大小（贪心）；(2) 沿现用巡回，第几个点后覆盖完备；
  (3) 若把覆盖子集前置，前缀里程能压到多少。
"""
import math
import numpy as np

import q3_offline_eval as Q
from q3_tune import ring


def grid(step=40.0):
    g = np.arange(-1800.0, 1800.0 + step, step)
    X, Y = np.meshgrid(g, g)
    m = X ** 2 + Y ** 2 <= 1800.0 ** 2
    return X[m], Y[m]


def masks_of(pts, X, Y):
    """返回 (masks, full)：full 为全域位掩码"""
    masks = [int.from_bytes(np.packbits((X - p[0]) ** 2 + (Y - p[1]) ** 2 <= 1000.0 ** 2).tobytes(), "little")
             for p in pts]
    full = 0
    for m in masks:
        full |= m
    return masks, full


def cover_idx(masks, order, full):
    acc = 0
    for k, i in enumerate(order, 1):
        acc |= masks[i]
        if acc == full:
            return k
    return None


def greedy_cover(masks, n, full):
    chosen, cur = [], 0
    while cur != full:
        best, bj = -1, -1
        for j in range(n):
            if j in chosen:
                continue
            g = (masks[j] & ~cur).bit_count()
            if g > best:
                best, bj = g, j
        if best <= 0:
            return None
        chosen.append(bj)
        cur |= masks[bj]
    return chosen


def tour_len(pts):
    s, cur = 0.0, (0.0, 0.0)
    for p in pts:
        s += math.hypot(p[0] - cur[0], p[1] - cur[1])
        cur = p
    return s


def main():
    X, Y = grid()
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    layouts = {"S17(现用)": S17, "R15(单环990x15)": ring(990, 15)}
    print(" %-18s %6s %8s %10s %12s %12s" %
          ("布局", "点数", "最小覆盖集", "现序完备点", "现序全巡回/m", "覆盖集前置/m"))
    for name, pts in layouts.items():
        pts = [tuple(map(float, p)) for p in pts]
        m, full = masks_of(pts, X, Y)
        n = len(pts)
        C = greedy_cover(m, n, full)
        W = Q.nn_tour(pts)
        idx = {tuple(p): i for i, p in enumerate(pts)}
        order = [idx[tuple(p)] for p in W]
        k = cover_idx(m, order, full)
        cfirst = Q.nn_tour([pts[j] for j in C])
        print(" %-18s %6d %8d %10s %12.0f %12.0f" %
              (name, n, len(C), k, tour_len(W), tour_len(cfirst)))


if __name__ == "__main__":
    main()