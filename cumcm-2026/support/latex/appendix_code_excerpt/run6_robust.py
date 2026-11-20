# 主策略程序 run6_robust.py（核心函数摘录，完整可运行版本见支撑材料）

# ray_intersect()：两示向线求交
def ray_intersect(p1, a1, p2, a2):
    t1, t2 = math.radians(a1), math.radians(a2)
    d1 = (math.cos(t1), math.sin(t1)); d2 = (math.cos(t2), math.sin(t2))
    den = d1[0]*d2[1] - d1[1]*d2[0]
    if abs(den) < 1e-9: return None
    t = ((p2[0]-p1[0])*d2[1] - (p2[1]-p1[1])*d2[0]) / den
    s = ((p2[0]-p1[0])*d1[1] - (p2[1]-p1[1])*d1[0]) / den
    if t <= 0 or s <= 0: return None            # 只接受前方交点
    q = (p1[0] + t*d1[0], p1[1] + t*d1[1])
    return q if math.hypot(*q) <= 2200 else None  # 交点须在合理范围

# huber_wls()：Huber 加权最小二乘精化
def huber_wls(obs, x0, delta=60.0, iters=60):
    """obs: [((px,py), theta_deg), ...]；最小化 Sigma rho((x-S)-n)，n 为方位线单位法向"""
    ns = [(-math.sin(math.radians(a)), math.cos(math.radians(a))) for _, a in obs]
    pts = [p for p, _ in obs]
    x, y = x0
    for _ in range(iters):
        num_x = num_y = den = 0.0
        for (px, py), (nx, ny) in zip(pts, ns):
            r = (x-px)*nx + (y-py)*ny           # 到方位线的有符号垂距
            w = 1.0 if abs(r) <= delta else delta/abs(r)   # Huber 权重
            # 目标 0.5*Sigma w (r)^2 -> 正规方程
            a11 = nx*nx; a12 = nx*ny; a22 = ny*ny
            b1 = nx*(px*nx + py*ny); b2 = ny*(px*nx + py*ny)
            num_x += w*(a11*x + a12*y); num_y += w*(a12*x + a22*y)  # 占位，实际用增量式
            den += w
        # 增量式重新累加（简洁写法）
        A = [[0.0, 0.0], [0.0, 0.0]]; b = [0.0, 0.0]
        for (px, py), (nx, ny) in zip(pts, ns):
            r = (x-px)*nx + (y-py)*ny
            w = 1.0 if abs(r) <= delta else delta/max(abs(r), 1e-9)
            a11 = nx*nx; a12 = nx*ny; a22 = ny*ny
            c = px*nx + py*ny
            A[0][0] += w*a11; A[0][1] += w*a12; A[1][0] += w*a12; A[1][1] += w*a22
            b[0] += w*nx*c; b[1] += w*ny*c
        det = A[0][0]*A[1][1] - A[0][1]*A[1][0]
        if abs(det) < 1e-12: break
        nx_ = (A[1][1]*b[0] - A[0][1]*b[1]) / det
        ny_ = (A[0][0]*b[1] - A[1][0]*b[0]) / det
        if abs(nx_-x) < 1e-6 and abs(ny_-y) < 1e-6:
            x, y = nx_, ny_; break
        x, y = nx_, ny_
    return (x, y)

# locate()：定位主入口
def locate(obs):
    """obs: [((px,py), theta_deg), ...] -> 估计位置"""
    if len(obs) < 2: return None
    I = []
    for (p1,a1),(p2,a2) in itertools.combinations(obs, 2):
        q = ray_intersect(p1,a1,p2,a2)
        if q: I.append(q)
    if not I: return None
    xs = sorted(q[0] for q in I); ys = sorted(q[1] for q in I)
    x0 = (xs[len(xs)//2], ys[len(ys)//2])
    return huber_wls(obs, x0)

# waypoints()：航点生成
def waypoints(mode):
    global NCERT
    # 问题4：若存在离线优化得到的航点文件（最坏角隙<170度约束下贪心删点），优先使用
    if mode == "p4":
        wp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "waypoints_p4.json")
        if os.path.exists(wp_file):
            try:
                data = json.load(open(wp_file, encoding="utf-8"))
                NCERT = int(data.get("n_cert", 0))
                _clm = data.get("cert_len_m")
                wps = [tuple(map(float, p)) for p in data["waypoints"]]
                print("[证书] Q4 证书前缀 %d 点（里程 %s m）：前 %d 点构成全域 (位置x朝向) 保证检出证书集，扫完前缀且已检出源全部清除即可安全终止"
                      % (NCERT, ("%.0f" % _clm) if _clm else "?", NCERT))
                print("[航点] 载入优化布局：%d 点，最坏角隙 %.1f度" % (len(wps), data.get("worst_gap_deg", float("nan"))))
                return wps
            except Exception as ex:
                print("[航点] 读取优化布局失败，回退默认:", ex)
    pts = [(0.0,0.0)]
    pts += [(1000*math.cos(math.radians(60*k)), 1000*math.sin(math.radians(60*k))) for k in range(6)]
    pts += [(1700*math.cos(math.radians(30*k)), 1700*math.sin(math.radians(30*k))) for k in range(12)]
    if mode == "p4":
        pts += [(2100*math.cos(math.radians(20*k)), 2100*math.sin(math.radians(20*k))) for k in range(18)]
        pts += [(2400*math.cos(math.radians(20*k+10)), 2400*math.sin(math.radians(20*k+10))) for k in range(18)]
    uniq = []
    for p in pts:
        if not any(math.hypot(p[0]-q[0], p[1]-q[1]) < 1.0 for q in uniq): uniq.append(p)
    if mode == "p3":
        # 单环 15 点：半径 990 m（盲区 990 m <= r_min = 1000 m，全域 L1/L2 证书通过）。
        # 离线复现器（400~800 局）显示其总时间比 17 点交会友好建证集约低 23%：
        #   巡回里程 ~= 2piR + R ~= 6.75 km（17 点为 13.71 km），而更小的外环半径使巡回收紧。
        R_RING, N_RING = 990.0, 15       # 单环建证集：半径 990 m（盲区 <= 1000 m）、15 点
        SEQ = [(R_RING * math.cos(2 * math.pi * k / N_RING),
                R_RING * math.sin(2 * math.pi * k / N_RING)) for k in range(N_RING)]
        rem = list(SEQ)
        cur = (0.0, 0.0)
        seq = []
        while rem:
            j = min(rem, key=lambda q: math.hypot(q[0] - cur[0], q[1] - cur[1]))
            seq.append(j)
            cur = j
            rem.remove(j)
        uniq = seq
        print("[cert] p3 采用单环 990 mx15 建证集（盲区 990 m <= r_min = 1000 m，L2 二重可见），已按最近邻排序")
    return uniq

# 主流程
r = enter()
if not isinstance(r, dict) or not r.get("accepted"):
    print("FATAL: /enter 未被接受，立即中止，避免空跑。响应 =", r)
    sys.exit(2)
print("enter:", r.get("accepted"), "| 模式:", MODE, "| 真实预算", r.get("remaining_real_duration_s"), "s")
W = waypoints(MODE); print("航点数:", len(W))
obs = {}; cleared = {}; failed = {}; stale = 0; prev_obs_n = 0

# mean_bearing()：多测点示向度取中位
def mean_bearing(ch):
    """观测到的示向度循环均值（度）。三条示向度近共线时，它就是距离方向。"""
    o = obs.get(ch, [])
    if not o:
        return None
    sx = sum(math.cos(math.radians(a)) for _, a in o)
    sy = sum(math.sin(math.radians(a)) for _, a in o)
    if abs(sx) < 1e-12 and abs(sy) < 1e-12:
        return None
    return math.degrees(math.atan2(sy, sx))

# remeasure_ortho()：法向补测
def remeasure_ortho(ch, est):
    """横向偏移复测：沿平均示向度的法向偏移 400/600 m 取一条近似正交的新示向度。

    近共线（三条射线夹角十几度）时误差主要落在距离方向，沿同一方向回退复测不增加横向
    约束；换到法向观测点才能把交会条件重新变良态。
    """
    mb = mean_bearing(ch)
    if mb is None:
        return None
    t = math.radians(mb)
    nx, ny = -math.sin(t), math.cos(t)
    for s in (400.0, -400.0, 600.0, -600.0):
        px, py = est[0] + s * nx, est[1] + s * ny
        if math.hypot(px, py) > 2600.0:
            continue
        m = measure(px, py, ch)
        if m.get("measure_result") == "direction":
            obs.setdefault(ch, []).append(((px, py), m["svd_deg"]))
            e2 = locate(obs[ch])
            if e2:
                print("   [横向复测] ch%-2d 偏移 %+.0f m -> 新估计 (%.0f,%.0f) vt=%.1f"
                      % (ch, s, e2[0], e2[1], vt()))
                return e2
    return None

# try_clear()：清除请求与判定
def try_clear(est, ch, tag):
    """开清：先在估计点 18 m 邻域试探，再沿平均示向度（距离方向）延伸到 60 m。

    近共线交会下估计误差主要沿距离方向（实测可达 39 m），故第二层沿距离方向补点；
    两层都失败记为一次失败，连续三次失败进入冷却，避免在错误盆地反复折返。
    """
    x, y = est
    ring = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(0.5,0),(-0.5,0),(0,0.5),(0,-0.5),
            (0.707,0.707),(0.707,-0.707),(-0.707,0.707),(-0.707,-0.707)]
    cand = [(x+dx*18.0, y+dy*18.0) for dx, dy in ring]   # 18 m：规避 /clear 判据可能为“严格 <20 m”
    mb = mean_bearing(ch)
    if mb is not None:
        t = math.radians(mb)
        ux, uy = math.cos(t), math.sin(t)
        nx, ny = -uy, ux
        cand += [(x + s*ux, y + s*uy) for s in (30.0, 45.0, 60.0, -30.0, -45.0)]
        cand += [(x + s*nx, y + s*ny) for s in (30.0, -30.0, 45.0, -45.0)]
    for px, py in cand:
        if math.hypot(px, py) > 2600.0:
            continue
        CLEAR_TRIES[ch] = CLEAR_TRIES.get(ch, 0) + 1
        res = clear(px, py, ch)
        if res.get("clear_result") == "success":
            FAIL_CNT.pop(ch, None); COOLDOWN.discard(ch)
            print("   [%s] ch%-2d 清除成功 @(%.0f,%.0f) vt=%.1f" % (tag, ch, px, py, vt())); return (px,py)
        if res.get("_http") or res.get("_err"):
            print("   [%s] ch%-2d 异常 %s" % (tag, ch, res)); return None
    _n = FAIL_CNT.get(ch, 0) + 1
    FAIL_CNT[ch] = _n
    if _n >= 3 and ch not in COOLDOWN:
        COOLDOWN.add(ch)
        print("   [冷却] ch%-2d 连续 %d 次清除失败 -> 暂停顺路开清，等新方向示向度 vt=%.1f" % (ch, _n, vt()))
    return None

# well_conditioned()：交会角良态判据
def well_conditioned(ch, gamma=30.0):
    """观测是否足以信任：至少 3 条示向度。

    由日志反演可知示向度存在约 1度 量级的离群误差：两条射线无任何冗余，一旦其中一条
    是离群值（或两者近于平行），交点误差可达数十米；3 条观测时 Huber 加权最小二乘
    至少能抗 1 条离群，故统一以">=3 条观测"作为停测与开清的门槛。
    """
    o = obs.get(ch, [])
    return len(o) >= 3

# cert_visited()：证书点访问标记
def cert_visited():
    for (cx, cy) in CERT_PTS:
        hit = False
        for (a, b) in VISITED:
            if abs(a - cx) < 1e-9 and abs(b - cy) < 1e-9:
                hit = True
                break
        if not hit:
            return False
    return True


for wi,(wx,wy) in enumerate(W):
    print("航点 %d/%d (%.0f,%.0f) vt=%.1f" % (wi+1, len(W), wx, wy, vt()))
    for ch in range(1,21):
        if ch in cleared: continue
        if SKIP_PENDING and ch in PENDING and well_conditioned(ch): continue
        m = measure(wx, wy, ch)
        if m.get("_http") or m.get("_err"): continue
        mr = m.get("measure_result")
        if mr == "near":
            res = clear(wx, wy, ch)
            if res.get("clear_result") == "success":
                cleared[ch] = (wx,wy); print("   ch%-2d near->清除成功 vt=%.1f" % (ch, vt()))
            continue
        if mr != "direction": continue
        _prev = mean_bearing(ch)
        obs.setdefault(ch, []).append(((wx,wy), m["svd_deg"]))
        if ch in COOLDOWN and _prev is not None:
            _dd = abs((m["svd_deg"] - _prev + 180.0) % 360.0 - 180.0)
            if _dd >= 45.0 and RELEASE_CNT.get(ch, 0) < MAX_RELEASE:
                RELEASE_CNT[ch] = RELEASE_CNT.get(ch, 0) + 1
                COOLDOWN.discard(ch); FAIL_CNT.pop(ch, None)
                print("   [冷却解除] ch%-2d 新示向度与原方向差 %.0f度，恢复开清 vt=%.1f" % (ch, _dd, vt()))
        est = locate(obs[ch])
        if not est: continue
        if SIDE_CLEAR:
            PENDING[ch] = est
            continue
        got = try_clear(est, ch, "定位")
        if got: cleared[ch] = got
        else:
            failed[ch] = est
            print("   ch%-2d 清除失败，改用横向偏移复测 (估计 %.0f,%.0f) vt=%.1f" % (ch, est[0], est[1], vt()))
            est2 = remeasure_ortho(ch, est)
            if est2:
                got2 = try_clear(est2, ch, "复测")
                if got2: cleared[ch] = got2; failed.pop(ch, None)
    print("   进度: 清除 %d | 待解 %d | vt=%.1f" % (len(cleared), len(set(obs)-set(cleared)), vt()))
    # 兜底终止（次级判据）：证书/建证集已扫完 且 已检出源全部清除 且 连续 8 个航点无新发现
    if SIDE_CLEAR and PENDING:
        _nxt = W[wi + 1] if wi + 1 < len(W) else (wx, wy)
        for _c in list(PENDING):
            if not well_conditioned(_c) or _c in COOLDOWN or CLEAR_TRIES.get(_c, 0) >= ATTEMPT_CAP:
                continue
            _e = PENDING[_c]
            _d1 = math.hypot(_e[0] - wx, _e[1] - wy)
            _d2 = math.hypot(_nxt[0] - _e[0], _nxt[1] - _e[1])
            _d0 = math.hypot(_nxt[0] - wx, _nxt[1] - wy)
            _cur = _d1 + _d2 - _d0
            _best = _cur
            _lim = (NCERT if (MODE == "p4" and NCERT > 0) else len(W)) - 1
            for _j in range(wi + 1, _lim):
                _a, _b = W[_j], W[_j + 1]
                _v = (math.hypot(_e[0] - _a[0], _e[1] - _a[1])
                      + math.hypot(_b[0] - _e[0], _b[1] - _e[1])
                      - math.hypot(_b[0] - _a[0], _b[1] - _a[1]))
                if _v < _best:
                    _best = _v
            if _cur <= _best + 1e-6:
                _ok = try_clear(_e, _c, "顺路")
                if _ok:
                    cleared[_c] = _ok
                    PENDING.pop(_c, None)
                    continue
                _e2 = remeasure_ortho(_c, _e)
                if _e2:
                    PENDING[_c] = _e2
                    _ok2 = try_clear(_e2, _c, "顺路复测")
                    if _ok2:
                        cleared[_c] = _ok2
                        PENDING.pop(_c, None)
    VISITED.append((wx, wy))
    _singles = [c for c in range(1, 21)
                if c not in cleared and c not in TRIED_SINGLE and len(obs.get(c, [])) == 1]
    if _singles and cert_visited():
        for _c in _singles:
            TRIED_SINGLE.add(_c)
            _p0, _bb = obs[_c][0]
            for _fw, _sd in ((0.0, 700.0), (0.0, -700.0), (300.0, 700.0), (300.0, -700.0),
                             (500.0, 700.0), (500.0, -700.0), (800.0, 500.0), (800.0, -500.0)):
                _t = math.radians(_bb)
                _px = _p0[0] + _fw * math.cos(_t) - _sd * math.sin(_t)
                _py = _p0[1] + _fw * math.sin(_t) + _sd * math.cos(_t)
                _m = measure(_px, _py, _c)
                if _m.get("measure_result") != "direction":
                    continue
                obs[_c].append(((_px, _py), _m["svd_deg"]))
                _e = locate(obs[_c])
                if not _e:
                    continue
                _g = try_clear(_e, _c, "补测")
                if _g:
                    cleared[_c] = _g
                    PENDING.pop(_c, None)
                    print("   [补测] ch%-2d 单观测->主动补测定位后清除成功 vt=%.1f" % (_c, vt()))
                else:
                    PENDING[_c] = _e
                    print("   [补测] ch%-2d 单观测->补测已定位但清除失败，转入收尾 vt=%.1f" % (_c, vt()))
                break
    all_cleared = (len(obs) == len(cleared))
    if JOINT_REORDER and PENDING and len(W) - wi - 1 >= 2:
        _tail = W[wi + 1:]
        _ord = joint_order((wx, wy), list(_tail), list(PENDING.values()))
        _nw = [t for t in _ord
               if any(abs(t[0] - u[0]) < 1e-9 and abs(t[1] - u[1]) < 1e-9 for u in _tail)]
        if len(_nw) == len(_tail):
            W[wi + 1:] = _nw
    if MODE == "p4" and NCERT > 0:
        if all_cleared and len(cleared) >= NMAX_SRC:
            print("   [cert] 已清除 %d 个源，达到题面源数上界 %d => 必然已全部清除，提前终止（剩余 %d 个航点未走）"
                  % (len(cleared), NMAX_SRC, len(W) - wi - 1))
            break
        if cert_visited():
            while PENDING:
                _c = min(PENDING, key=lambda c: math.hypot(PENDING[c][0] - wx, PENDING[c][1] - wy))
                _e = PENDING.pop(_c)
                if CLEAR_TRIES.get(_c, 0) >= TAIL_CAP:
                    continue
                _ok = try_clear(_e, _c, "收尾")
                if _ok:
                    cleared[_c] = _ok
                    continue
                _e2 = remeasure_ortho(_c, _e)
                if _e2:
                    _ok2 = try_clear(_e2, _c, "收尾复测")
                    if _ok2:
                        cleared[_c] = _ok2
                    elif _c not in RETRY2:
                        RETRY2.add(_c)
                        PENDING[_c] = _e2      # 再给一轮横向复测机会
            if len(obs) == len(cleared):
                print("   [cert] Q4 证书前缀 %d 点已扫完且已检出源全部清除 => 全域保证无漏检，提前终止（剩余 %d 个航点未走）"
                      % (NCERT, len(W) - wi - 1))
                break
            print("   [警告] 证书已扫完但仍有 %d 个源未清除，继续扫描剩余航点" % (len(obs) - len(cleared)))
        prev_obs_n = len(obs)
        continue
    if MODE == "p3" and len(VISITED) >= len(W) and PENDING:
        while PENDING:
            _c = min(PENDING, key=lambda c: math.hypot(PENDING[c][0] - wx, PENDING[c][1] - wy))
            _e = PENDING.pop(_c)
            if CLEAR_TRIES.get(_c, 0) >= TAIL_CAP:
                continue
            _ok = try_clear(_e, _c, "收尾")
            if _ok:
                cleared[_c] = _ok
                continue
            _cx, _cy = 0.6 * _e[0], 0.6 * _e[1]
            _m2 = measure(_cx, _cy, _c)
            if _m2.get("measure_result") == "direction":
                obs.setdefault(_c, []).append(((_cx, _cy), _m2["svd_deg"]))
                _e2 = locate(obs[_c])
                if _e2:
                    _ok2 = try_clear(_e2, _c, "收尾复测")
                    if _ok2:
                        cleared[_c] = _ok2
        all_cleared = (len(obs) == len(cleared))
    if all_cleared and len(cleared) >= NMAX_SRC and MODE == "p3":
        print("   [cert] 已清除 %d 个源，达到题面源数上界 %d => 必然已全部清除，提前终止（剩余 %d 个航点未走）"
              % (len(cleared), NMAX_SRC, len(W) - wi - 1))
        break
    if MODE == "p3" and all_cleared and len(VISITED) >= len(W):
        print("   [cert] 建证集已扫完且已检出源全部清除，按覆盖证书终止（剩余 %d 个航点未走）" % (len(W) - wi - 1))
        break
    if all_cleared and cert_visited() and len(obs) == prev_obs_n and wi >= 6:
        stale += 1
        if stale >= 8:
            print("   已检出源全部清除且连续 %d 个航点无新发现，提前终止（剩余 %d 个航点未走）"
                  % (stale, len(W)-wi-1))
            break
    else:
        stale = 0
    prev_obs_n = len(obs)

e = exit_()
print("exit:", e.get("exit_reason"), "| 总虚拟时间 %.1f s" % vt())
print("检出频道 %d: %s" % (len(obs), sorted(obs)))
print("清除 %d: %s" % (len(cleared), sorted(cleared)))
print("未清除: %s" % sorted(set(obs)-set(cleared)))
_outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
os.makedirs(_outdir, exist_ok=True)
json.dump({"case": NAME, "mode": MODE, "waypoints": len(W),
           "observed": {str(k): len(v) for k,v in obs.items()},
           "cleared": sorted(cleared), "virtual_time_s": vt(), "log": LOG},
          open(os.path.join(_outdir, "run6_%s.json" % NAME), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("日志已存 _scratch/run6_%s.json，请求数 %d" % (NAME, len(LOG)))

# ...（其余辅助函数与完整可运行版本见支撑材料）