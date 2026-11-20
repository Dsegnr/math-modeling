"""B 题问题4：航点角隙判据的独立推导与航点数量优化（纯计算，不连模拟器）

判据推导：
  设航点集 W、源位于 G，只有满足 |G-w| <= r_eff_min = 1000 m 的航点才可能探测到该源。
  把这些"可测航点"按相对 G 的方位角排序，相邻方位角之差（含首尾环绕）的最大值称为
  最坏角隙 Delta_max(G)。定向源的有效辐射扇区为 180度，因此
      Delta_max(G) < 180度  <=>  任意定向方向都存在至少一个位于扇区内的可测航点  <=>  不会漏检。
  取区域内所有 G 的最大值即得布局的最坏角隙；这也是"零盲区"之外的第二个必要条件。
"""
import math, json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np

R_ARENA = 1800.0     # 目标区域半径
R_EFF   = 1000.0     # 有效接收半径下界（保守按最坏情况设计）

def make_samples(n_ring=12, n_rad=10):
    """区域内外均匀+边界加密采样"""
    pts = [(0.0, 0.0)]
    for k in range(1, n_rad + 1):
        r = R_ARENA * k / n_rad
        n_ang = max(8, int(round(n_ring * k)))
        for j in range(n_ang):
            a = 2 * math.pi * j / n_ang
            pts.append((r * math.cos(a), r * math.sin(a)))
        # 边界再加密
        if k == n_rad:
            for j in range(180):
                a = 2 * math.pi * j / 180
                pts.append((r * math.cos(a), r * math.sin(a)))
    return pts

def worst_gap(samples, wps):
    S = np.array(samples); W = np.array(wps)
    D = np.linalg.norm(S[:, None, :] - W[None, :, :], axis=2)
    worst = 0.0; worst_g = None
    for i, g in enumerate(S):
        idx = np.where(D[i] <= R_EFF)[0]
        if len(idx) < 2:
            return 180.0, tuple(g)
        rel = W[idx] - g
        ang = np.sort(np.arctan2(rel[:, 1], rel[:, 0]))
        gaps = np.diff(ang)
        gaps = np.append(gaps, 2 * math.pi - (ang[-1] - ang[0]))
        m = gaps.max()
        if m > worst: worst, worst_g = m, tuple(g)
    return math.degrees(worst), worst_g

def w19():
    pts = [(0.0, 0.0)]
    pts += [(1000*math.cos(math.radians(60*k)), 1000*math.sin(math.radians(60*k))) for k in range(6)]
    pts += [(1700*math.cos(math.radians(30*k)), 1700*math.sin(math.radians(30*k))) for k in range(12)]
    return pts

def w55():
    pts = w19()
    pts += [(2100*math.cos(math.radians(20*k)), 2100*math.sin(math.radians(20*k))) for k in range(18)]
    pts += [(2400*math.cos(math.radians(20*k+10)), 2400*math.sin(math.radians(20*k+10))) for k in range(18)]
    uniq = []
    for p in pts:
        if not any(math.hypot(p[0]-q[0], p[1]-q[1]) < 1.0 for q in uniq): uniq.append(p)
    return uniq

def greedy_prune(wps, samples, target=170.0, verbose=True):
    pts = list(wps)
    improved = True
    while improved:
        improved = False
        for i in range(len(pts)):
            cand = pts[:i] + pts[i+1:]
            gap, _ = worst_gap(samples, cand)
            if gap < target:
                pts = cand; improved = True
                if verbose: print("   删去 1 点 -> 剩余 %d 点, 最坏角隙 %.1f度" % (len(pts), gap))
                break
    return pts

S = make_samples()
print("采样点数量:", len(S))
for name, W in [("19 点（域内环形）", w19()), ("55 点（含域外环绕带）", w55())]:
    g, where = worst_gap(S, W)
    print("%s: 航点 %d, 最坏角隙 %.1f度, 位置 %s, 判定 %s"
          % (name, len(W), g, tuple(round(v) for v in where), "满足<180度" if g < 180 else "违例>=180度"))

print("\n--- 独立优化：在“最坏角隙 <170度”约束下贪心删点（从 55 点出发）---")
W0 = w55()
G0, _ = worst_gap(S, W0)
print("起点: %d 点, 角隙 %.1f度" % (len(W0), G0))
Wopt = greedy_prune(W0, S, target=170.0)
Gopt, where = worst_gap(S, Wopt)
print("优化结果: %d 点, 最坏角隙 %.1f度（位置 %s）" % (len(Wopt), Gopt, tuple(round(v) for v in where)))
print("航点数下降 %.1f%%，扫描时间预计从 %d s 降到 %d s（20 频道 x 119 s/点）"
      % (100*(len(W0)-len(Wopt))/len(W0), len(W0)*119, len(Wopt)*119))
out = {"samples": len(S), "w19": {"n": len(w19()), "gap": worst_gap(S, w19())[0]},
       "w55": {"n": len(W0), "gap": G0},
       "optimized": {"n": len(Wopt), "gap": Gopt,
                     "waypoints": [[round(x,1), round(y,1)] for x, y in Wopt]}}
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
os.makedirs(d, exist_ok=True)
json.dump(out, open(os.path.join(d, "waypoint_optimize.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("结果已存 _scratch/waypoint_optimize.json")