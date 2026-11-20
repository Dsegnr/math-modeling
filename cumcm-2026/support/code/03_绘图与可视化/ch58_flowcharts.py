"""
第五~八章 X.1 思路流程图（Q1~Q4 各一张）
输出：figures/fig_ch5_flow.*, fig_ch6_flow.*, fig_ch7_flow.*, fig_ch8_flow.*
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BASE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(BASE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["savefig.dpi"] = 300

C = {
    "输入": "#4f81bd",
    "建模": "#1f4e79",
    "算法": "#2e75b6",
    "判据": "#c0504d",
    "决策": "#9bbb59",
    "输出": "#f79646",
    "约束": "#7f7f7f",
}


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, "%s.%s" % (name, ext)), bbox_inches="tight")
    plt.close(fig)
    print("  [fig] %s" % name, flush=True)


def _w_units(s):
    """粗略显示宽度：CJK 记 1，ASCII 记 0.55；$...$ 内的命令名记 1"""
    out, i, inmath = 0.0, 0, False
    while i < len(s):
        ch = s[i]
        if ch == "$":
            inmath = not inmath
            i += 1
            continue
        if inmath and ch == "\\":
            i += 1
            while i < len(s) and (s[i].isalpha()):
                i += 1
            out += 1.0
            continue
        out += 1.0 if ord(ch) > 0x2E80 else 0.55
        i += 1
    return out


def _wrap(s, limit):
    """按显示宽度折行；**$...$ 数学段视为不可分割的原子**，否则中文会被切进数学模式"""
    toks, i, buf = [], 0, ""
    while i < len(s):
        if s[i] == "$":
            j = s.find("$", i + 1)
            j = len(s) - 1 if j == -1 else j
            if buf:
                toks.append(("t", buf))
                buf = ""
            toks.append(("m", s[i:j + 1]))
            i = j + 1
        else:
            buf += s[i]
            i += 1
    if buf:
        toks.append(("t", buf))
    lines, line, w = [], "", 0.0
    for kind, tk in toks:
        tw = _w_units(tk)
        if kind == "m":
            if w > 0 and w + tw > limit:
                lines.append(line)
                line, w = "", 0.0
            line += tk
            w += tw
        else:
            for ch in tk:
                cw = 1.0 if ord(ch) > 0x2E80 else 0.55
                if w + cw > limit and line:
                    lines.append(line)
                    line, w = "", 0.0
                line += ch
                w += cw
    if line:
        lines.append(line)
    return lines


def draw_flow(stages, title, fname, note=None, limit=34.0):
    """stages: [(标签, 文本), ...]；自动折行 + 动态框高"""
    BW = 8.4
    TXT_X = 1.15
    wrapped = []
    for tag, text in stages:
        ls = _wrap(text, limit)
        wrapped.append((tag, ls))
        pitch = 0.26 * len(ls) + 0.30
    bh_list = [0.26 * len(ls) + 0.28 for _, ls in wrapped]
    gap = 0.34
    total_h = sum(b + gap for b in bh_list)
    fig, ax = plt.subplots(figsize=(9.6, total_h + 1.1))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, total_h + 0.82)
    ax.axis("off")
    cx, y = 5.5, total_h + 0.15
    for i, (tag, ls) in enumerate(wrapped):
        bh = bh_list[i]
        y -= bh
        col = C.get(tag, "#4f81bd")
        for fc, al, ec, lw in ((col, 0.13, "none", 0), ("none", 1.0, col, 1.4)):
            ax.add_patch(FancyBboxPatch((cx - BW / 2, y), BW, bh,
                                        boxstyle="round,pad=0.05,rounding_size=0.12",
                                        facecolor=fc, edgecolor=ec, lw=lw, alpha=al))
        ax.text(cx - BW / 2 + 0.14, y + bh / 2, tag, ha="left", va="center",
                fontsize=9.0, color="white", zorder=5,
                bbox=dict(boxstyle="round,pad=0.20", fc=col, ec="none"))
        ax.text(cx - BW / 2 + TXT_X, y + bh / 2, "\n".join(ls), ha="left", va="center",
                fontsize=10.0, linespacing=1.45, zorder=5)
        if i < len(wrapped) - 1:
            ax.add_patch(FancyArrowPatch((cx, y - 0.01), (cx, y - 0.20),
                                         arrowstyle="-|>", mutation_scale=12,
                                         color="0.45", lw=1.3, zorder=2))
        y -= gap
    ax.set_title(title, fontsize=12.5, pad=16)
    if note:
        ax.text(0.06, total_h + 0.40, note, fontsize=8.5, va="bottom", ha="left",
                bbox=dict(fc="#fbfbfb", ec="0.75", alpha=0.98))
    save(fig, fname)


Q1 = [
    ("输入", "检测点 $S_k$、示向度 $\\theta_k$、误差界 $\\varepsilon=1^\\circ$"),
    ("建模", "楔形区域 $W_k$：以 $S_k$ 为顶点、张角 $2\\varepsilon$ 的闭凸楔形"),
    ("建模", "定位区域 $\\Omega=(\\bigcap_k W_k)\\cap\\bar B(O,1800)$（题面红四边形 ∩ 目标圆域）"),
    ("算法", "半平面精确裁剪 → 凸包（Andrew）→ 旋转卡壳求直径 $D$"),
    ("算法", "Welzl 算法求最小外接圆半径 $\\rho_{\\min}$"),
    ("判据", "ρ_min = D/2，当且仅当存在径点对 (A,B) 使 (X-A)·(X-B) <= 0"),
    ("输出", "覆盖：以 $D$ 为直径的圆可覆盖；不覆盖：给出反例（三点近正三角形，比值→$2/\\sqrt{3}$）"),
    ("决策", "桥接：$\\rho_{\\min}\\leq20$ m 当且仅当存在保证清除的开火点 → 接入问题三、四"),
]

Q2 = [
    ("输入", "一次示向度 $\\theta_1$（只给方位、不含距离）"),
    ("建模", "后验可行集 $\\Omega_1=W(S_1,\\theta_1,1^\\circ)\\cap\\bar B(S_1,1500)\\cap\\bar B(O,1800)$"),
    ("建模", "选点准则：最大化后验几何收缩效用 $\\mathbb{E}[\\ln\\frac{\\rho_{\\min}(\\Omega_1)}{\\rho_{\\min}(T_2)}]$"),
    ("约束", "保证可收集 $R_{\\rm recv}=\\bigcap_{x\\in\\Omega_1}\\bar B(x,1000)$（一般非圆盘）"),
    ("约束", "可达域 $R_{\\rm geo}$ 与交会角非病态 $R_{\\rm good}$；三者取交得候选区域 $S_2$"),
    ("算法", "候选网格枚举 + 精确凸多边形几何求 $\\rho_{\\min}$；minimax（最坏交会角）作对照"),
    ("判据", "最优：$\\ell\\approx840$ m、$g\\approx-543$ m（$\\psi\\approx56^\\circ$）；坏解：贴近源与直冲无正的最坏交会角下界"),
    ("决策", "第二次观测 → 更新为 $T_2$；$\\rho_{\\min}(T_2)\\leq20$ m 则开火，否则继续补测"),
]

Q3 = [
    ("输入", "圆域内 10~16 个全向源，个数与频道未知；机器狗自原点出发"),
    ("建模", "几何层：保证可探测集 $\\{p:\\|p-x\\|\\leq1000\\}$；点数下界对照（7 点仅 1 点可测 → 不可交会）"),
    ("建模", "估计层：角度区间取交为保证型可行集；稳健点估计作初值与排序"),
    ("建模", "决策层：$\\rho(T)\\leq20$ m 当且仅当存在保证清除的开火点"),
    ("算法", "19 点航点布局全覆盖（最大盲区 576.0 m）→ 逐航点扫频道"),
    ("算法", "病态射线对过滤 → 交点分量中位数 → 稳健精化（≥3 观测时启用）"),
    ("判据", "清除：$\\rho\\leq20$ 直冲；$20<\\rho\\leq40$ 沿长轴偏置；$\\rho>40$ 补测"),
    ("判据", "终止：$N_{\\rm clear}=16$；或 ≥10 且各未判定频道均有「频道×空间」覆盖证书（最小执行集 7 点）"),
    ("输出", "演练与三次正式测试；报告清除比例与平均定位清除时间（含日志）"),
]

Q4 = [
    ("输入", "圆域内混合全向源与定向源；定向方向未知；其余同问题三"),
    ("建模", "定向源覆盖角 = 定向方向 $\\pm90^\\circ$；负观测不提供距离信息"),
    ("建模", "L1 一重可见：$\\Delta_{\\max}(x)\\leq180^\\circ$ 当且仅当$x\\in\\mathrm{conv}(P_x)$"),
    ("建模", "L2 二重可见：$|P_x|\\geq2$；L3 几何可定位：存在可见点对，$|\\sin\\psi|\\geq\\sin30^\\circ$"),
    ("约束", "域外环绕带扩充航点；全域证书用细胞分解（或严格角度传播界）"),
    ("算法", "55 点布局：L1/L2/L3 三级全部通过（最坏角隙 150.0°、最少 3 点、最坏交会角 60.0°）"),
    ("判据", "对照：19 点有 3723 个网格点角隙超 180°（最坏 244.9°）→ 必然存在漏检朝向"),
    ("输出", "与问题三共用清除与终止判据；报告演练与三次正式测试结果"),
]


CH9 = [
    ("输入", "四问模型、算法与策略；18 局演练日志；四类覆盖证书"),
    ("建模", "三层检验：模型层（解析对照 + 蒙特卡洛 + 反例构造）、算法层（暴力对照 + 多起点 + 残差诊断）、策略层（多局演练 + 时间分解 + 参数扰动）"),
    ("约束", "覆盖类结论强制附口径：网格步长 + 朝向分辨率 + 所留余量；未标注口径者不得作为数学保证"),
    ("判据", "计时口径校验：$T_{\\rm virt}$ = 移动 + 检测 + 切频 + 清除，18 局相对误差 $0.00\\%$"),
    ("算法", "问题四全域（位置 $\\times$ 朝向）证书：搜索 $30$ m$\\times3^\\circ$，复核 $20/10/5$ m $\\times$ $2/1^\\circ$，未覆盖对数 0"),
    ("判据", "对照：原 55 点序走完全程 L1 = 99.99%（网格脆弱）；新 31 点证书 L1 = 100%、L2 = 95.6%"),
    ("判据", "灵敏度：接收半径取下界 1000 m 为保守口径；定向源负观测不含距离信息 $\\Rightarrow$ 证书由 8 点升至 31 点"),
    ("决策", "由检验驱动改进：顺路清除替代立即清除（移动 $-40\\%$）；两项被否决、一项回退、一项负结果"),
    ("输出", "稳健性结论：Q3 十一局 + Q4 六局全部 100% 清除；给出局限、改进方向与推广"),
]


if __name__ == "__main__":
    draw_flow(Q1, "图 5-1  问题一思路流程：定位区域 → 直径 → 覆盖判据 → 清除判据",
              "fig_ch5_flow", "注：半平面裁剪精确；与圆盘求交为 N 边形近似（N=720 时径向误差 0.0143 m）")
    draw_flow(Q2, "图 6-1  问题二思路流程：带接收约束的主动观测点设计",
              "fig_ch6_flow", "注：目标为后验几何收缩效用（非 Shannon 信息增益）；先验取 $\\Omega_1$ 上均匀（最大熵基线）")
    draw_flow(Q3, "图 7-1  问题三思路流程：覆盖 → 定位 → 清除三层决策",
              "fig_ch7_flow", "注：19 点为实测可行解；覆盖证书为严格保证，连续无新发现为非保证型加速")
    draw_flow(Q4, "图 8-1  问题四思路流程：定向源的可见性覆盖与三级证书",
              "fig_ch8_flow", "注：L1/L2/L3 为分层几何证书；全域结论为 20 m 网格下的数值证书")
    draw_flow(CH9, "图 9-1  第九章思路流程：模型—算法—策略三层检验",
              "fig_ch9_flow", "注：覆盖类结论一律附「网格步长 + 朝向分辨率 + 余量」口径；未标注口径的覆盖结论不作为数学保证")
    print("[done]", flush=True)
