"""问题三离线复现器：不消耗演练次数的布局与策略开关比选。
按实测日志反演模拟器语义：可见性取 dist <= r_i（r_i 属源，落在 [1000,1500]）；
计时为移动 dist/5 s、measure 5 s、切频 1 s、clear 成功 5 s 失败 3 s。
用法：python q3_offline_eval.py [局数]"""
import os
import sys
import math
import itertools
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA = 1800.0
V = 5.0


# 与 run6_robust.py 一致的定位内核
def ray_intersect(p1, a1, p2, a2):
    t1, t2 = math.radians(a1), math.radians(a2)
    d1 = (math.cos(t1), math.sin(t1))
    d2 = (math.cos(t2), math.sin(t2))
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
    s = ((p2[0] - p1[0]) * d1[1] - (p2[1] - p1[1]) * d1[0]) / den
    if t <= 0 or s <= 0:
        return None
    q = (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return q if math.hypot(*q) <= 2200 else None


def huber_wls(obs, x0, delta=60.0, iters=60):
    ns = [(-math.sin(math.radians(a)), math.cos(math.radians(a))) for _, a in obs]
    pts = [p for p, _ in obs]
    x, y = x0
    for _ in range(iters):
        A = [[0.0, 0.0], [0.0, 0.0]]
        b = [0.0, 0.0]
        for (px, py), (nx, ny) in zip(pts, ns):
            r = (x - px) * nx + (y - py) * ny
            w = 1.0 if abs(r) <= delta else delta / max(abs(r), 1e-9)
            A[0][0] += w * nx * nx
            A[0][1] += w * nx * ny
            A[1][0] += w * nx * ny
            A[1][1] += w * ny * ny
            c = px * nx + py * ny
            b[0] += w * nx * c
            b[1] += w * ny * c
        det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
        if abs(det) < 1e-12:
            break
        nx_ = (A[1][1] * b[0] - A[0][1] * b[1]) / det
        ny_ = (A[0][0] * b[1] - A[1][0] * b[0]) / det
        if abs(nx_ - x) < 1e-6 and abs(ny_ - y) < 1e-6:
            x, y = nx_, ny_
            break
        x, y = nx_, ny_
    return (x, y)


def locate(obs):
    if len(obs) < 2:
        return None
    I = []
    for (p1, a1), (p2, a2) in itertools.combinations(obs, 2):
        q = ray_intersect(p1, a1, p2, a2)
        if q:
            I.append(q)
    if not I:
        return None
    xs = sorted(q[0] for q in I)
    ys = sorted(q[1] for q in I)
    return huber_wls(obs, (xs[len(xs) // 2], ys[len(ys) // 2]))


# 演练器语义
class Sim:
    def __init__(self, case, bear_sigma=0.0, seed=0):
        self.src = case                      # {ch: (x, y, r)}
        self.bear_sigma = bear_sigma
        self.rng = np.random.default_rng(seed)
        self.t = 0.0
        self.pos = (0.0, 0.0)
        self.cur_ch = 1
        self.mv = self.me = self.sw = self.cl = 0.0
        self.n_meas = self.n_ok = self.n_miss = 0

    def _move(self, p):
        d = math.hypot(p[0] - self.pos[0], p[1] - self.pos[1])
        self.mv += d / V
        self.t += d / V
        self.pos = p

    def measure(self, p, ch):
        self._move(p)
        self.me += 5.0
        self.t += 5.0
        self.n_meas += 1
        if ch != self.cur_ch:
            self.sw += 1.0
            self.t += 1.0
            self.cur_ch = ch
        s = self.src.get(ch)
        if s is None:
            return "none"
        d = math.hypot(s[0] - p[0], s[1] - p[1])
        if d <= 5.0:
            return "near"
        if d <= s[2]:
            a = math.degrees(math.atan2(s[1] - p[1], s[0] - p[0])) % 360.0
            if self.bear_sigma > 0:
                a = (a + float(self.rng.normal(0.0, self.bear_sigma))) % 360.0
            return a
        return "none"

    def clear(self, p, ch):
        self._move(p)
        s = self.src.get(ch)
        ok = s is not None and math.hypot(s[0] - p[0], s[1] - p[1]) <= 20.0
        self.cl += 5.0 if ok else 3.0
        self.t += 5.0 if ok else 3.0
        self.n_ok += 1 if ok else 0
        self.n_miss += 0 if ok else 1
        return ok


OFF = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)]


def build_masks(W, step=40.0):
    g = np.arange(-1800.0, 1800.0 + step, step)
    GX, GY = np.meshgrid(g, g)
    m = GX ** 2 + GY ** 2 <= ARENA ** 2
    X, Y = GX[m], GY[m]
    masks = []
    for (wx, wy) in W:
        cov = (X - wx) ** 2 + (Y - wy) ** 2 <= 1000.0 ** 2
        masks.append(int.from_bytes(np.packbits(cov).tobytes(), "little"))
    return masks, (1 << len(X)) - 1


def cover_first_order(W, masks, full):
    """把覆盖子集（贪心最小覆盖）前置：先用最少航点完成全域覆盖证书，其余点排在后面备用。"""
    n = len(W)
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
            break
        chosen.append(bj)
        cur |= masks[bj]
    rest = [j for j in range(n) if j not in chosen]
    seq = list(chosen)
    cur_p = (0.0, 0.0)
    out = []
    pool = list(seq)
    while pool:
        j = min(pool, key=lambda k: math.hypot(W[k][0] - cur_p[0], W[k][1] - cur_p[1]))
        out.append(j)
        cur_p = W[j]
        pool.remove(j)
    pool = list(rest)
    while pool:
        j = min(pool, key=lambda k: math.hypot(W[k][0] - cur_p[0], W[k][1] - cur_p[1]))
        out.append(j)
        cur_p = W[j]
        pool.remove(j)
    return [W[j] for j in out], len([j for j in seq])


def wc_ok(obs_ch, est, gamma=30.0):
    """观测几何良态：>=3 条观测，或两条观测在源处夹角 >= gamma（与 run6_robust 同口径）"""
    if len(obs_ch) >= 3:
        return True
    if len(obs_ch) < 2 or est is None:
        return False
    v = [(p[0] - est[0], p[1] - est[1]) for p, _ in obs_ch[:2]]
    n1 = math.hypot(*v[0])
    n2 = math.hypot(*v[1])
    if n1 < 1e-6 or n2 < 1e-6:
        return True
    c = (v[0][0] * v[1][0] + v[0][1] * v[1][1]) / (n1 * n2)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
    if ang > 90.0:
        ang = 180.0 - ang
    return ang >= gamma


def run_policy(W, case, ncert, nmax=16, side_clear=True, prune=True, cull_obs=3, masks=None,
               dyn_stop=False, bear_sigma=0.0, seed=0, wc_gamma=None, prepend=None):
    if masks is None:
        masks, full = build_masks(W)
    else:
        masks, full = masks
    sim = Sim(case, bear_sigma=bear_sigma, seed=seed)
    obs, cleared, pending = {}, {}, {}
    measured_idx = {}
    visited = 0
    for wi, (wx, wy) in enumerate(W):
        for ch in range(1, 21):
            if ch in cleared:
                continue
            if prune and ch not in pending and len(measured_idx.get(ch, ())) > 0:
                acc = 0
                for _k in measured_idx[ch]:
                    acc |= masks[_k]
                if acc == full:
                    continue
            if side_clear and ch in pending and len(obs.get(ch, [])) >= cull_obs:
                if wc_gamma is None or wc_ok(obs.get(ch, []), pending.get(ch), wc_gamma):
                    continue
            mr = sim.measure((wx, wy), ch)
            measured_idx.setdefault(ch, []).append(wi)
            if mr == "near":
                if sim.clear((wx, wy), ch):
                    cleared[ch] = (wx, wy)
                continue
            if mr == "none":
                continue
            obs.setdefault(ch, []).append(((wx, wy), mr))
            est = locate(obs[ch])
            if est:
                pending[ch] = est
        # 顺路清除（绕道代价最小的航点上）
        if side_clear and pending:
            nxt = W[wi + 1] if wi + 1 < len(W) else (wx, wy)
            for ch in list(pending):
                e = pending[ch]
                d1 = math.hypot(e[0] - wx, e[1] - wy)
                d2 = math.hypot(nxt[0] - e[0], nxt[1] - e[1])
                d0 = math.hypot(nxt[0] - wx, nxt[1] - wy)
                cur = d1 + d2 - d0
                lim = (ncert if ncert > 0 else len(W)) - 1
                best = cur
                for j in range(wi + 1, lim):
                    a, b = W[j], W[j + 1]
                    v = (math.hypot(e[0] - a[0], e[1] - a[1]) + math.hypot(b[0] - e[0], b[1] - e[1])
                         - math.hypot(b[0] - a[0], b[1] - a[1]))
                    if v < best:
                        best = v
                if cur > best + 1e-6:
                    continue
                ok = False
                for dx, dy in OFF:
                    if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), ch):
                        ok = True
                        break
                if ok:
                    cleared[ch] = e
                    pending.pop(ch, None)
                else:
                    cx, cy = 0.6 * e[0], 0.6 * e[1]
                    mr = sim.measure((cx, cy), ch)
                    if isinstance(mr, float):
                        obs.setdefault(ch, []).append(((cx, cy), mr))
                        e2 = locate(obs[ch])
                        if e2:
                            pending[ch] = e2
        if len(cleared) >= nmax:
            break
        visited |= masks[wi]
        reached = (wi >= ncert - 1) or (dyn_stop and visited == full)
        if reached and (wi >= ncert - 1 or len(cleared) == len(obs)):
            for ch in list(pending):
                e = pending.pop(ch)
                ok = False
                for dx, dy in OFF:
                    if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), ch):
                        ok = True
                        break
                if not ok:
                    cx, cy = 0.6 * e[0], 0.6 * e[1]
                    mr = sim.measure((cx, cy), ch)
                    if isinstance(mr, float):
                        obs.setdefault(ch, []).append(((cx, cy), mr))
                        e2 = locate(obs[ch])
                        if e2:
                            for dx, dy in OFF:
                                if sim.clear((e2[0] + dx * 20.0, e2[1] + dy * 20.0), ch):
                                    ok = True
                                    break
                if ok:
                    cleared[ch] = e
            if len(cleared) >= len([c for c in range(1, 21) if c in obs]):
                break
    return {"t": sim.t, "mv": sim.mv, "me": sim.me, "sw": sim.sw, "cl": sim.cl,
            "n_src": len(case), "cleared": len(cleared), "n_meas": sim.n_meas,
            "n_miss": sim.n_miss}


def gen_case(rng):
    n = int(rng.integers(10, 17))
    chs = rng.choice(np.arange(1, 21), size=n, replace=False)
    case = {}
    for ch in chs:
        while True:
            x, y = rng.uniform(-1800, 1800, 2)
            if x * x + y * y <= ARENA ** 2:
                break
        case[int(ch)] = (float(x), float(y), float(rng.uniform(1000, 1500)))
    return case


def run_policy_dyn(W, case, nmax=16, masks=None, cull_obs=3, src_bonus=25.0, near_bonus=400.0):
    """顺序完全自适应的策略：证书集固定，但"下一个去哪个航点 / 先去清哪个源"每步重算。

    证书仅约束"必须访问哪些航点"，不约束访问顺序，故该策略与固定顺序版共享同一覆盖证书。
    near_bonus：若某待清源距当前点不足该值，优先顺路清掉。
    """
    sim = Sim(case)
    obs, cleared, pending = {}, {}, {}
    unvisited = set(range(len(W)))
    cur = (0.0, 0.0)
    while True:
        if len(cleared) >= nmax:
            break
        best = None
        for j in sorted(unvisited):
            d = math.hypot(W[j][0] - cur[0], W[j][1] - cur[1])
            if best is None or d < best[0]:
                best = (d, "w", j)
        for ch, e in pending.items():
            d = math.hypot(e[0] - cur[0], e[1] - cur[1])
            if d <= near_bonus:
                d -= 1e6                      # 近旁源优先顺路清除
            else:
                d -= src_bonus
            if best is None or d < best[0]:
                best = (d, "s", ch)
        if best is None:
            break
        if best[1] == "w":
            j = best[2]
            unvisited.discard(j)
            wx, wy = W[j]
            for ch in range(1, 21):
                if ch in cleared:
                    continue
                if ch in pending and len(obs.get(ch, [])) >= cull_obs:
                    continue
                mr = sim.measure((wx, wy), ch)
                if mr == "near":
                    if sim.clear((wx, wy), ch):
                        cleared[ch] = (wx, wy)
                    continue
                if mr == "none":
                    continue
                obs.setdefault(ch, []).append(((wx, wy), mr))
                e = locate(obs[ch])
                if e:
                    pending[ch] = e
            cur = (wx, wy)
        else:
            ch = best[2]
            e = pending.pop(ch)
            ok = False
            for dx, dy in OFF:
                if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), ch):
                    ok = True
                    break
            if ok:
                cleared[ch] = e
            else:
                cx, cy = 0.6 * e[0], 0.6 * e[1]
                mr = sim.measure((cx, cy), ch)
                if isinstance(mr, float):
                    obs.setdefault(ch, []).append(((cx, cy), mr))
                    e2 = locate(obs[ch])
                    if e2:
                        for dx, dy in OFF:
                            if sim.clear((e2[0] + dx * 20.0, e2[1] + dy * 20.0), ch):
                                ok = True
                                break
                        if ok:
                            cleared[ch] = e2
                        else:
                            pending[ch] = e2
                else:
                    pending[ch] = e
            cur = sim.pos
        if not unvisited and len(cleared) == len(obs):
            break
    return {"t": sim.t, "mv": sim.mv, "me": sim.me, "sw": sim.sw, "cl": sim.cl,
            "n_src": len(case), "cleared": len(cleared), "n_meas": sim.n_meas,
            "n_miss": sim.n_miss}


def _path_len(seq, cur):
    s, p = 0.0, cur
    for t in seq:
        s += math.hypot(t[0] - p[0], t[1] - p[1])
        p = t
    return s


def joint_order(cur, wp_pts, src_pts, iters=30):
    """对「剩余航点 U 待清源」做最近邻 + 2-opt，返回最优路径序列（开放路径，起点 cur）"""
    pool = list(wp_pts) + list(src_pts)
    if not pool:
        return []
    rem, p, seq = list(pool), cur, []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - p[0], q[1] - p[1]))
        seq.append(j)
        p = j
        rem.remove(j)
    best = _path_len(seq, cur)
    improved, r = True, 0
    while improved and r < iters:
        improved, r = False, r + 1
        n = len(seq)
        for i in range(n - 1):
            for j in range(i + 1, n):
                cand = seq[:i] + seq[i:j + 1][::-1] + seq[j + 1:]
                v = _path_len(cand, cur)
                if v < best - 1e-9:
                    seq, best, improved = cand, v, True
    return seq


def run_policy_joint(W, case, nmax=16, masks=None, cull_obs=3, wc_gamma=None,
                     bear_sigma=0.0, seed=0):
    """每步对「剩余航点 U 待清源」重解联合路径（最近邻 + 2-opt），再执行下一站。"""
    if masks is None:
        masks, full = build_masks(W)
    else:
        masks, full = masks
    sim = Sim(case, bear_sigma=bear_sigma, seed=seed)
    obs, cleared, pending = {}, {}, {}
    unvisited = set(range(len(W)))
    cur = (0.0, 0.0)
    while True:
        if len(cleared) >= nmax:
            break
        wps = [W[j] for j in sorted(unvisited)]
        srcs = list(pending.values())
        seq = joint_order(cur, wps, srcs)
        if not seq:
            break
        tgt = seq[0]
        # 判断目标是航点还是源
        wj = None
        for j in sorted(unvisited):
            if abs(W[j][0] - tgt[0]) < 1e-9 and abs(W[j][1] - tgt[1]) < 1e-9:
                wj = j
                break
        if wj is not None:
            unvisited.discard(wj)
            wx, wy = W[wj]
            for ch in range(1, 21):
                if ch in cleared:
                    continue
                if ch in pending and (wc_gamma is None
                                      or wc_ok(obs.get(ch, []), pending.get(ch), wc_gamma)):
                    continue
                mr = sim.measure((wx, wy), ch)
                if mr == "near":
                    if sim.clear((wx, wy), ch):
                        cleared[ch] = (wx, wy)
                    continue
                if mr == "none":
                    continue
                obs.setdefault(ch, []).append(((wx, wy), mr))
                e = locate(obs[ch])
                if e:
                    pending[ch] = e
            cur = (wx, wy)
        else:
            # 目标是某个待清源
            ch = None
            for c, e in pending.items():
                if abs(e[0] - tgt[0]) < 1e-9 and abs(e[1] - tgt[1]) < 1e-9:
                    ch = c
                    break
            if ch is None:
                break
            e = pending.pop(ch)
            ok = False
            for dx, dy in OFF:
                if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), ch):
                    ok = True
                    break
            if ok:
                cleared[ch] = e
            else:
                cx, cy = 0.6 * e[0], 0.6 * e[1]
                mr = sim.measure((cx, cy), ch)
                if isinstance(mr, float):
                    obs.setdefault(ch, []).append(((cx, cy), mr))
                    e2 = locate(obs[ch])
                    if e2:
                        for dx, dy in OFF:
                            if sim.clear((e2[0] + dx * 20.0, e2[1] + dy * 20.0), ch):
                                ok = True
                                break
                        if ok:
                            cleared[ch] = e2
                        else:
                            pending[ch] = e2
                else:
                    pending[ch] = e
            cur = sim.pos
        if not unvisited and len(cleared) == len(obs):
            break
    return {"t": sim.t, "mv": sim.mv, "me": sim.me, "sw": sim.sw, "cl": sim.cl,
            "n_src": len(case), "cleared": len(cleared), "n_meas": sim.n_meas,
            "n_miss": sim.n_miss}


def gen_case_old(rng):
    n = int(rng.integers(10, 17))
    chs = rng.choice(np.arange(1, 21), size=n, replace=False)
    case = {}
    for ch in chs:
        while True:
            x, y = rng.uniform(-1800, 1800, 2)
            if x * x + y * y <= ARENA ** 2:
                break
        case[int(ch)] = (float(x), float(y), float(rng.uniform(1000, 1500)))
    return case


def nn_tour(pts, start=(0.0, 0.0)):
    rem, cur, out = list(pts), start, []
    while rem:
        j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
        out.append(j)
        cur = j
        rem.remove(j)
    return out


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    rng = np.random.default_rng(20260911)
    S17 = [(779, -450), (1427, -464), (1237, -1237), (453, -1690), (0, -900), (-464, -1427),
           (-875, -1516), (-1214, -882), (-900, 0), (-1750, 0), (-1516, 875), (-875, 1516),
           (-450, 779), (0, 1750), (464, 1427), (849, 849), (1690, 453)]
    W = nn_tour([tuple(map(float, p)) for p in S17])
    print("Q3 离线复现：17 点建证集，%d 局随机案例" % nrun)
    rows = []
    for _ in range(nrun):
        case = gen_case(rng)
        rows.append(run_policy(W, case, ncert=len(W)))
    tt = np.array([r["t"] for r in rows])
    ok = np.array([r["cleared"] == r["n_src"] for r in rows])
    print("  清除率 = %.1f%% | 平均总时间 %.0f s | 平均 %.0f s/源" %
          (100 * ok.mean(), tt.mean(), (tt / np.array([r["n_src"] for r in rows])).mean()))
    for k, lab in (("mv", "移动"), ("me", "检测"), ("sw", "切频"), ("cl", "清除")):
        v = np.array([r[k] for r in rows])
        print("  %s %.0f s (%.1f%%)" % (lab, v.mean(), 100 * v.mean() / tt.mean()))
    print("  平均 measure 次数 %.0f | 平均 clear 失败 %.1f" %
          (np.mean([r["n_meas"] for r in rows]), np.mean([r["n_miss"] for r in rows])))


if __name__ == "__main__":
    main()
