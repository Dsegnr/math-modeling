"""
Q4 观测审计：检查「定向源是否真的只在覆盖角内被检出」

对一局演练日志，按频道列出：
  - 每个航点序号上是否检出 direction、方位角 svd_deg
  - 检出的航点在全域中的分布（相对源估计位置的方向角跨度）

若某源只在少数几个方向被检出 => 证实「定向覆盖角 +-90度」的束内可见语义
若某源在近乎全方向都被检出   => 说明该源为全向源，或束内语义需重新核对
"""
import os
import sys
import json
import math

BASE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(path):
    d = load(path)
    log = d["log"]
    # 复原航点序列（按 /measure 出现的顺序去重，用坐标）
    wp_seq = []
    seen = set()
    for e in log:
        p = e.get("payload", {})
        if e["path"] == "/measure" and "position" in p:
            k = (round(p["position"]["x"], 1), round(p["position"]["y"], 1))
            if k not in seen:
                seen.add(k)
                wp_seq.append(k)
    wp_index = {k: i + 1 for i, k in enumerate(wp_seq)}
    print("日志: %s" % os.path.basename(path))
    print("航点序列长度 = %d" % len(wp_seq))
    print("清除数 = %d / 检出数 = %d | 虚拟时间 = %.1f s\n" % (len(d["cleared"]), len(d["observed"]), d["virtual_time_s"]))

    obs = {}
    near = {}
    for e in log:
        if e["path"] != "/measure":
            continue
        r = e.get("resp", {})
        p = e.get("payload", {})
        ch = p.get("channel")
        pos = (round(p["position"]["x"], 1), round(p["position"]["y"], 1))
        if r.get("measure_result") == "direction":
            obs.setdefault(ch, []).append((wp_index.get(pos, -1), pos, r.get("svd_deg")))
        elif r.get("measure_result") == "near":
            near.setdefault(ch, []).append((wp_index.get(pos, -1), pos))

    for ch in sorted(obs, key=lambda c: min(o[0] for o in obs[c])):
        lst = obs[ch]
        idxs = [o[0] for o in lst]
        print("ch%-2d  检出 %2d 次 | 航点序号 %s" % (ch, len(lst), idxs))
        print("      方位角: %s" % ["%.1f" % o[2] for o in lst])
        if ch in near:
            print("      near 航点: %s" % [n[0] for n in near[ch]])
    print("\n全向源候选（检出航点数 >= 8 且分布很广，或出现过 near）:")
    for ch in sorted(obs):
        if len(obs[ch]) >= 8 or ch in near:
            print("   ch%-2d 检出 %d 次%s" % (ch, len(obs[ch]), "  [有 near]" if ch in near else ""))
    early = {c: min(o[0] for o in obs[c]) for c in obs}
    print("\n各频道首次检出航点序号: %s" % dict(sorted(early.items(), key=lambda kv: kv[1])))

    # 源估计位置（成功清除点）与「背向/朝向」分析
    est = {}
    for e in log:
        if e["path"] != "/clear":
            continue
        r = e.get("resp", {})
        if r.get("clear_result") == "success":
            p = e["payload"]
            est[p["channel"]] = (p["position"]["x"], p["position"]["y"])
    print("\n源估计位置 / 朝向诊断（outward_deg>0 表示束心背离圆心）:")
    print("  %-5s %-22s %-9s %-9s %-10s %s" % ("ch", "估计位置", "r/m", "pos角/度", "束心角/度", "背向角/度"))
    outward = []
    for ch in sorted(est):
        x, y = est[ch]
        rr = math.hypot(x, y)
        posang = math.degrees(math.atan2(y, x)) % 360
        dirs = []
        for _, pos, _svd in obs.get(ch, []):
            dirs.append(math.degrees(math.atan2(pos[1] - y, pos[0] - x)) % 360)
        if len(dirs) >= 2:
            # 圆周均值
            sx = sum(math.cos(math.radians(a)) for a in dirs)
            sy = sum(math.sin(math.radians(a)) for a in dirs)
            ori = math.degrees(math.atan2(sy, sx)) % 360
        elif dirs:
            ori = dirs[0]
        else:
            ori = float("nan")
        d = (ori - posang + 540) % 360 - 180
        outward.append(d)
        print("  ch%-3d (%7.0f,%7.0f)   %6.0f   %7.1f   %8.1f   %+8.1f" % (ch, x, y, rr, posang, ori, d))
    if outward:
        print("\n  背向角统计: n=%d | 均值=%.1f度 | |背向角|>90度 的源数=%d (占比 %.0f%%)"
              % (len(outward), sum(outward) / len(outward),
                 sum(1 for d in outward if abs(d) > 90),
                 100.0 * sum(1 for d in outward if abs(d) > 90) / len(outward)))


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        BASE, "_scratch", "archive", "practice_0911_q4run2_run6_p4.json")
    main(p)