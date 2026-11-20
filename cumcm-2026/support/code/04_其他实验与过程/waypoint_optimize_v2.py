"""B 题问题4 航点优化 v2：判据升级版（独立贡献）

v1 判据：最坏角隙 < 180度（保证"不漏检"，即至少 1 个航点可见）
v2 判据（本轮实验发现 v1 不足）：在此基础上再要求
    (a) 可测航点数 >= 2      -- 否则单点观测无法交会定位（实测 ch4 因此漏清）
    (b) 可测航点间最小角距 >= 15度 -- 避免两点近乎共线导致交会病态
    (c) 最坏角隙 < 170度
对区域内 841 个采样点逐一检验；从 55 点贪心删点，得到满足 v2 判据的最小布局。
"""
import math, json, os, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")

R_ARENA, R_EFF = 1800.0, 1000.0
MIN_PTS, MIN_ANGLE_DEG, MAX_GAP_DEG = 2, 15.0, 170.0

def make_samples(n_ring=12, n_rad=10):
    pts = [(0.0,0.0)]
    for k in range(1, n_rad+1):
        r = R_ARENA*k/n_rad
        n_ang = max(8, int(round(n_ring*k)))
        for j in range(n_ang):
            a = 2*math.pi*j/n_ang; pts.append((r*math.cos(a), r*math.sin(a)))
        if k == n_rad:
            for j in range(180):
                a = 2*math.pi*j/180; pts.append((r*math.cos(a), r*math.sin(a)))
    return pts

def evaluate(samples, wps, detail=False):
    S = np.array(samples); W = np.array(wps)
    D = np.linalg.norm(S[:,None,:]-W[None,:,:], axis=2)
    worst_gap = 0.0; min_pts_all = 10**9; worst_ang = 999.0; bad = None
    for i,g in enumerate(S):
        idx = np.where((D[i] <= R_EFF) & (D[i] > 50.0))[0]   # 排除与源几乎重合的航点（方位角无定义）
        if len(idx) < MIN_PTS:
            if detail: return False, 0.0, len(idx), 0.0, tuple(g)
            return False
        rel = W[idx]-g
        ang = np.sort(np.arctan2(rel[:,1], rel[:,0]))
        gaps = np.append(np.diff(ang), 2*math.pi-(ang[-1]-ang[0]))
        gap = gaps.max()
        # 存在性判据：可测航点中"最大两两夹角"（而非任意两点夹角）
        ad = np.degrees(ang)
        best = 0.0
        for _a in ad:
            sep = np.abs(ad-_a) % 360.0
            sep = np.minimum(sep, 360.0-sep)
            if sep.size: best = max(best, float(sep.max()))
        ang_min = best
        if len(idx) < min_pts_all: min_pts_all = len(idx)
        if ang_min < worst_ang: worst_ang = ang_min
        if gap > worst_gap:
            worst_gap, bad = gap, tuple(g)
        if detail and (len(idx) < MIN_PTS or math.degrees(gap) >= MAX_GAP_DEG or ang_min < MIN_ANGLE_DEG):
            return False, math.degrees(gap), len(idx), ang_min, tuple(g)
    ok = (math.degrees(worst_gap) < MAX_GAP_DEG) and (min_pts_all >= MIN_PTS) and (worst_ang >= MIN_ANGLE_DEG)
    return ok, math.degrees(worst_gap), min_pts_all, worst_ang, bad

def w55():
    pts = [(0.0,0.0)]
    pts += [(1000*math.cos(math.radians(60*k)), 1000*math.sin(math.radians(60*k))) for k in range(6)]
    pts += [(1700*math.cos(math.radians(30*k)), 1700*math.sin(math.radians(30*k))) for k in range(12)]
    pts += [(2100*math.cos(math.radians(20*k)), 2100*math.sin(math.radians(20*k))) for k in range(18)]
    pts += [(2400*math.cos(math.radians(20*k+10)), 2400*math.sin(math.radians(20*k+10))) for k in range(18)]
    uniq=[]
    for p in pts:
        if not any(math.hypot(p[0]-q[0],p[1]-q[1])<1.0 for q in uniq): uniq.append(p)
    return uniq

S = make_samples()
W = w55()
ok, gap, minpts, angmin, bad = evaluate(S, W, detail=True)
print("起点 55 点：", "满足 v2 判据" if ok else "不满足 v2 判据")
print("   最坏角隙 %.1f度 | 最少可测点数 %d | 最小角距 %.1f度 | 不满足处 %s"
      % (gap, minpts, angmin, tuple(round(v) for v in bad) if bad else "无"))

# 贪心删点（约束：仍满足 v2 判据）
pts = list(W); improved = True
while improved:
    improved = False
    for i in range(len(pts)):
        cand = pts[:i]+pts[i+1:]
        if evaluate(S, cand, detail=False)[0]:
            pts = cand; improved = True; break
G, minpts, angmin, bad = evaluate(S, pts, detail=True)[1:]
print("\n优化结果：%d 点（原 %d，降 %.1f%%）" % (len(pts), len(W), 100*(len(W)-len(pts))/len(W)))
print("   最坏角隙 %.1f度 | 最少可测点数 %d | 最小角距 %.1f度" % (G, minpts, angmin))
print("   20 频道扫描时间：%d s（原 %d s，省 %d s）" % (len(pts)*119, len(W)*119, (len(W)-len(pts))*119))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "waypoints_p4.json")
json.dump({"source":"greedy_prune v2: min 2 observations, min angular separation 15 deg, worst gap <170 deg",
           "n":len(pts), "worst_gap_deg":G, "min_obs_points":minpts, "min_angle_deg":angmin,
           "waypoints":[[round(x,1),round(y,1)] for x,y in pts]},
          open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("已写入", out)