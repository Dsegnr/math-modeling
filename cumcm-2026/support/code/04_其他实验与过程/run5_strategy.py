"""B 题改进版策略（问题3/问题4 通用）
改进点：1) 7 点覆盖扫描并记录每频道观测 2) 单点观测频道做法向补测 3) 清除失败做误差椭圆定向搜索 4) 全程日志
"""
import json, math, os, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# 参赛队号必须由外部提供，禁止写死在代码中（支撑材料不得暴露身份）
ROBOT_ID = os.environ.get("CUMCM_ROBOT_ID", "") or (sys.argv[2] if len(sys.argv) > 2 else "")
if not ROBOT_ID:
    print("用法: 先设置环境变量 CUMCM_ROBOT_ID=<参赛队号>，或  python run5_strategy.py <日志名> <参赛队号>")
    sys.exit(1)
BASE="http://127.0.0.1:2026"; RID=ROBOT_ID; ARENA="default"
LOG=[]; _seq=0
def nid():
    global _seq; _seq+=1; return "%s-v5-%04d"%(RID,_seq)
def post(path,payload):
    body=json.dumps(payload).encode()
    req=Request(BASE+path,data=body,headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=10) as r: res=json.loads(r.read().decode("utf-8"))
    except HTTPError as e: res={"_http":e.code}
    except Exception as e: res={"_err":str(e)}
    LOG.append({"path":path,"payload":payload,"resp":res}); return res
def base(): return {"arena_id":ARENA,"robot_id":RID,"request_id":nid()}
def enter(): return post("/enter",base())
def exit_(): return post("/exit",base())
def measure(x,y,ch):
    p=base(); p["position"]={"x":float(x),"y":float(y)}; p["channel"]=int(ch); return post("/measure",p)
def clear(x,y,ch):
    p=base(); p["position"]={"x":float(x),"y":float(y)}; p["channel"]=int(ch); return post("/clear",p)
def vt():
    for e in reversed(LOG):
        v=e["resp"].get("virtual_time_s")
        if isinstance(v,(int,float)): return v
    return 0.0
def cross(a1,a2,p1,p2):
    t1,t2=math.radians(a1),math.radians(a2)
    d1=(math.cos(t1),math.sin(t1)); d2=(math.cos(t2),math.sin(t2))
    den=d1[0]*d2[1]-d1[1]*d2[0]
    if abs(den)<1e-9: return None
    t=((p2[0]-p1[0])*d2[1]-(p2[1]-p1[1])*d2[0])/den
    if t<=0: return None
    q=(p1[0]+t*d1[0], p1[1]+t*d1[1])
    return q if math.hypot(*q)<=2500 else None
def try_clear(est, ch, tag):
    x,y=est
    OFF = [(0,0),(0.5,0),(-0.5,0),(0,0.5),(0,-0.5),
           (0.35,0.35),(-0.35,0.35),(0.35,-0.35),(-0.35,-0.35),
           (1,0),(-1,0),(0,1),(0,-1)]
    for dx,dy in OFF:
        px,py=x+dx*20.0, y+dy*20.0
        r=clear(px,py,ch)
        if r.get("clear_result")=="success":
            print("   [%s] ch%-2d 清除成功 @(%.0f,%.0f) vt=%.1f"%(tag,ch,px,py,vt()))
            return (px,py)
        if r.get("_http") or r.get("_err"):
            print("   [%s] ch%-2d clear异常 %s"%(tag,ch,r)); return None
    print("   [%s] ch%-2d 清除失败（13 点试探）vt=%.1f"%(tag,ch,vt()))
    return None

NAME=sys.argv[1] if len(sys.argv)>1 else "run5"
r=enter(); print("enter:",r.get("accepted"),"预算",r.get("remaining_real_duration_s"))
RING=1500.0
pts=[(0.0,0.0)]+[(RING*math.cos(math.radians(60*k)),RING*math.sin(math.radians(60*k))) for k in range(6)]
obs={}; cleared={}; failed={}
for pi,(px,py) in enumerate(pts):
    print("检测点 %d (%.0f,%.0f) vt=%.1f"%(pi,px,py,vt()))
    for ch in range(1,21):
        if ch in cleared: continue
        m=measure(px,py,ch)
        if m.get("_http") or m.get("_err"): continue
        if m.get("measure_result")=="direction":
            obs.setdefault(ch,[]).append(((px,py),m["svd_deg"]))
            if len(obs[ch])>=2:
                (p1,a1),(p2,a2)=obs[ch][-2],obs[ch][-1]
                q=cross(a1,a2,p1,p2)
                if q:
                    got=try_clear(q,ch,"扫")
                    if got: cleared[ch]=got
                    else: failed[ch]=q
    print("   进度: 清除 %d | 失败 %d | vt=%.1f"%(len(cleared),len(failed),vt()))
# 阶段2：单点观测频道 -> 法向补测
for ch,lst in list(obs.items()):
    if ch in cleared or len(lst)>=2: continue
    (p,a)=lst[0]
    u=(math.cos(math.radians(a)),math.sin(math.radians(a)))
    n=(-u[1],u[0])
    done=False
    for d in (250.0,500.0):
        for sgn in (1,-1):
            p2=(p[0]+sgn*d*n[0], p[1]+sgn*d*n[1])
            if math.hypot(*p2)>2000: continue
            m2=measure(p2[0],p2[1],ch)
            if m2.get("measure_result")=="direction":
                obs[ch].append((p2,m2["svd_deg"]))
                q=cross(a,m2["svd_deg"],p,p2)
                if q:
                    got=try_clear(q,ch,"补测")
                    if got: cleared[ch]=got; done=True
                    else: failed[ch]=q
                break
        if done: break
    print("   补测 ch%-2d -> %s vt=%.1f"%(ch,"清除" if ch in cleared else "未清除",vt()))
# 阶段3：对失败点再做扩展搜索
for ch,q in list(failed.items()):
    if ch in cleared: continue
    got=try_clear(q,ch,"扩展")
    if got: cleared[ch]=got
e=exit_(); print("exit:",e.get("exit_reason"),"总虚拟时间 %.1f s"%vt())
print("清除 %d 个: %s"%(len(cleared),sorted(cleared)))
print("未清除: %s"%(sorted(set(obs)-set(cleared))))
_outdir=os.path.join(os.path.dirname(os.path.abspath(__file__)),"_scratch")
os.makedirs(_outdir,exist_ok=True)
json.dump({"case":NAME,"cleared":{str(k):v for k,v in cleared.items()},
           "observed":{str(k):len(v) for k,v in obs.items()},
           "log":LOG},
          open(os.path.join(_outdir,"run5_%s.json"%NAME),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("日志已存 run5_%s.json，请求数 %d"%(NAME,len(LOG)))
