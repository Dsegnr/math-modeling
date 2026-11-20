"""问题四离线复现器：证书前缀 + 顺路清除 + 累计 3 条示向度门槛 + 对角试探点 + 单观测补测 + 证书式终止。
与问题三复现器同源，差异在定向源的覆盖角（负观测不含距离信息）。
用法：python q4_offline_eval.py [局数] [theta模式：uniform|inward]"""
import os
import sys
import json
import math
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ARENA, V = 1800.0, 5.0
OFF = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5),
       (0.707, 0.707), (0.707, -0.707), (-0.707, 0.707), (-0.707, -0.707)]
SUP = ((0.0, 700.0), (0.0, -700.0), (300.0, 700.0), (300.0, -700.0),
       (500.0, 700.0), (500.0, -700.0), (800.0, 500.0), (800.0, -500.0))


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
    for (p1, a1), (p2, a2) in __import__("itertools").combinations(obs, 2):
        q = ray_intersect(p1, a1, p2, a2)
        if q:
            I.append(q)
    if not I:
        return None
    xs = sorted(q[0] for q in I)
    ys = sorted(q[1] for q in I)
    return huber_wls(obs, (xs[len(xs) // 2], ys[len(ys) // 2]))


class Sim:
    def __init__(self, case, seed=0, bear_sigma=0.05):
        self.src = case                     # {ch: (x, y, r, theta, is_omni)}
        self.rng = np.random.default_rng(seed)
        self.bear_sigma = bear_sigma
        self.t = self.mv = self.me = self.sw = self.cl = 0.0
        self.pos = (0.0, 0.0)
        self.cur = 1
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
        if ch != self.cur:
            self.sw += 1.0
            self.t += 1.0
            self.cur = ch
        s = self.src.get(ch)
        if s is None:
            return "none"
        x, y, r, th, omni = s
        d = math.hypot(x - p[0], y - p[1])
        if d > r:
            return "none"
        if d <= 5.0:
            return "near"
        if not omni:
            a = math.degrees(math.atan2(p[1] - y, p[0] - x)) % 360.0
            if abs((a - th + 180.0) % 360.0 - 180.0) > 90.0:
                return "none"
        a2 = math.degrees(math.atan2(y - p[1], x - p[0])) % 360.0
        if self.bear_sigma > 0:
            a2 = (a2 + float(self.rng.normal(0.0, self.bear_sigma))) % 360.0
        return a2

    def clear(self, p, ch):
        self._move(p)
        s = self.src.get(ch)
        ok = s is not None and math.hypot(s[0] - p[0], s[1] - p[1]) <= 20.0
        self.cl += 5.0 if ok else 3.0
        self.t += 5.0 if ok else 3.0
        self.n_ok += 1 if ok else 0
        self.n_miss += 0 if ok else 1
        return ok


def gen_case(rng, theta_mode="uniform"):
    n = int(rng.integers(10, 17))
    chs = rng.choice(np.arange(1, 21), size=n, replace=False)
    nd = int(rng.binomial(n, 0.5))
    dirs = set(rng.choice(chs, size=nd, replace=False).tolist())
    case = {}
    for ch in chs:
        while True:
            x, y = rng.uniform(-ARENA, ARENA, 2)
            if x * x + y * y <= ARENA ** 2:
                break
        if ch in dirs:
            if theta_mode == "inward":
                th = (math.degrees(math.atan2(-y, -x)) + float(rng.normal(0, 60))) % 360.0
            else:
                th = float(rng.uniform(0, 360))
            case[int(ch)] = (float(x), float(y), float(rng.uniform(1000, 1500)), th, False)
        else:
            case[int(ch)] = (float(x), float(y), float(rng.uniform(1000, 1500)), 0.0, True)
    return case


def pair_angle(obs_ch, est):
    """已定位频道的最优交会角（源处两可见点夹角，取 <=90 的等价锐角）"""
    if len(obs_ch) < 2 or est is None:
        return 0.0
    best = 0.0
    for i in range(len(obs_ch)):
        for j in range(i + 1, len(obs_ch)):
            v1 = (obs_ch[i][0][0] - est[0], obs_ch[i][0][1] - est[1])
            v2 = (obs_ch[j][0][0] - est[0], obs_ch[j][0][1] - est[1])
            n1, n2 = math.hypot(*v1), math.hypot(*v2)
            if n1 < 1e-6 or n2 < 1e-6:
                return 90.0
            c = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
            a = math.degrees(math.acos(c))
            if a > 90.0:
                a = 180.0 - a
            best = max(best, a)
    return best


def run_p4(W, case, ncert, nmax=16, seed=0, bear_sigma=0.05, cull=3, single_fix=True,
           geom_fix=None):
    sim = Sim(case, seed=seed, bear_sigma=bear_sigma)
    obs, cleared, pending = {}, {}, {}
    measured = set()
    single_tried = set()
    for wi, (wx, wy) in enumerate(W):
        for ch in range(1, 21):
            if ch in cleared:
                continue
            if ch in pending and len(obs.get(ch, [])) >= cull:
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
        # 顺路清除（绕道最省段，且候选段限定在证书段内）
        if pending:
            nxt = W[wi + 1] if wi + 1 < len(W) else (wx, wy)
            for ch in list(pending):
                if len(obs.get(ch, [])) < cull:
                    continue
                e = pending[ch]
                d1 = math.hypot(e[0] - wx, e[1] - wy)
                d2 = math.hypot(nxt[0] - e[0], nxt[1] - e[1])
                d0 = math.hypot(nxt[0] - wx, nxt[1] - wy)
                cur = d1 + d2 - d0
                lim = ncert - 1
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
                        obs[ch].append(((cx, cy), mr))
                        e2 = locate(obs[ch])
                        if e2:
                            pending[ch] = e2
        # 单观测主动补测
        if single_fix and wi >= ncert - 1:
            singles = [c for c in range(1, 21)
                       if c not in cleared and c not in single_tried and len(obs.get(c, [])) == 1]
            if geom_fix is not None:
                singles += [c for c in range(1, 21)
                            if c not in cleared and c not in single_tried and len(obs.get(c, [])) >= 2
                            and pair_angle(obs.get(c, []), pending.get(c)) < geom_fix]
            for c in singles:
                single_tried.add(c)
                p0, bb = obs[c][0]
                for fw, sd in SUP:
                    t = math.radians(bb)
                    pm = (p0[0] + fw * math.cos(t) - sd * math.sin(t),
                          p0[1] + fw * math.sin(t) + sd * math.cos(t))
                    mr = sim.measure(pm, c)
                    if not isinstance(mr, float):
                        continue
                    obs[c].append((pm, mr))
                    e = locate(obs[c])
                    if not e:
                        continue
                    ok = False
                    for dx, dy in OFF:
                        if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), c):
                            ok = True
                            break
                    if ok:
                        cleared[c] = e
                        pending.pop(c, None)
                    else:
                        pending[c] = e
                    break
        if len(cleared) >= nmax:
            break
        if wi >= ncert - 1:
            for c in list(pending):
                e = pending.pop(c)
                ok = False
                for dx, dy in OFF:
                    if sim.clear((e[0] + dx * 20.0, e[1] + dy * 20.0), c):
                        ok = True
                        break
                if not ok:
                    cx, cy = 0.6 * e[0], 0.6 * e[1]
                    mr = sim.measure((cx, cy), c)
                    if isinstance(mr, float):
                        obs[c].append(((cx, cy), mr))
                        e2 = locate(obs[c])
                        if e2:
                            for dx, dy in OFF:
                                if sim.clear((e2[0] + dx * 20.0, e2[1] + dy * 20.0), c):
                                    ok = True
                                    break
                if ok:
                    cleared[c] = e
            if len(cleared) == len(obs):
                break
    return {"t": sim.t, "mv": sim.mv, "me": sim.me, "sw": sim.sw, "cl": sim.cl,
            "n_src": len(case), "cleared": len(cleared), "n_meas": sim.n_meas,
            "n_miss": sim.n_miss}


def load_W():
    d = json.load(open(os.path.join(BASE, "waypoints_p4.json"), encoding="utf-8"))
    W = [tuple(map(float, p)) for p in d["waypoints"]]
    return W, int(d["n_cert"])


def main():
    nrun = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    mode = sys.argv[2] if len(sys.argv) > 2 else "uniform"
    W, ncert = load_W()
    rng = np.random.default_rng(20260911)
    rows = []
    for i in range(nrun):
        case = gen_case(rng, mode)
        rows.append(run_p4(W, case, ncert, seed=i))
    tt = np.array([r["t"] for r in rows])
    ok = np.mean([r["cleared"] == r["n_src"] for r in rows]) * 100
    per = np.mean([r["t"] / max(r["n_src"], 1) for r in rows])
    print("Q4 离线复现（%d 局，theta~%s，证书段 %d 点）：" % (nrun, mode, ncert))
    print("  清除率 %.1f%% | 平均总时间 %.0f s | 平均 %.0f s/源" % (ok, tt.mean(), per))
    for k, lab in (("mv", "移动"), ("me", "检测"), ("sw", "切频"), ("cl", "清除")):
        v = np.array([r[k] for r in rows])
        print("  %s %.0f s (%.1f%%)" % (lab, v.mean(), 100 * v.mean() / tt.mean()))
    print("  平均 measure %.0f 次 | 平均 clear 失败 %.2f 次" %
          (np.mean([r["n_meas"] for r in rows]), np.mean([r["n_miss"] for r in rows])))


if __name__ == "__main__":
    main()
