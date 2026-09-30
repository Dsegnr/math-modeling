# -*- coding: utf-8 -*-
"""华数杯五~八章初稿 docx 构建（基于 APMCM 参考文档样式）。"""
import os
import shutil
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn

REF = r"D:\数模竞赛\APMCM2026\作品\2026第16届APMCM作品\Aapmcm26203467.docx"
FINAL = r"D:\数模竞赛\华数杯2026\A题项目\华数杯2026_A题\写作素材\五至八章_模型建立与求解_初稿.docx"
BASE = r"D:\数模竞赛\华数杯2026\A题项目\华数杯2026_A题"
IMG = os.path.join(BASE, "图片")
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

shutil.copy(REF, FINAL)
doc = Document(FINAL)
body_el = doc.element.body
for child in list(body_el):
    if child.tag != qn("w:sectPr"):
        body_el.remove(child)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def set_run(r, size=None, bold=None, east="宋体", west="Times New Roman"):
    r.font.name = west
    rPr = r._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), east)
    if size is not None:
        r.font.size = Pt(size)
    if bold is not None:
        r.font.bold = bold


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    _set_outline(p, 0)
    set_run(p.add_run(text), size=14, bold=True, east="黑体")


def h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    _set_outline(p, 1)
    set_run(p.add_run(text), size=12, bold=True, east="黑体")


def _set_outline(p, level):
    pPr = p._p.get_or_add_pPr()
    el = OxmlElement("w:outlineLvl")
    el.set(qn("w:val"), str(level))
    pPr.append(el)


def body(text):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(21)
    set_run(p.add_run(text), size=12)


def fig(sub, name, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(IMG, sub, name), width=Cm(14))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run(cap.add_run(caption), size=9)


def tab_caption(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_run(p.add_run(text), size=9, bold=True)


def set_table_geometry(table, widths_cm):
    tbl = table._tbl
    tblPr = tbl.tblPr
    dxa_list = [int(round(w * 567)) for w in widths_cm]
    total_dxa = sum(dxa_list)
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), str(total_dxa))
    tblW.set(qn("w:type"), "dxa")
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    cm = OxmlElement("w:tblCellMar")
    for side, w in [("left", "108"), ("right", "108"),
                    ("top", "40"), ("bottom", "40")]:
        el = OxmlElement("w:" + side)
        el.set(qn("w:w"), w)
        el.set(qn("w:type"), "dxa")
        cm.append(el)
    tblPr.append(cm)
    old = tbl.find(qn("w:tblGrid"))
    if old is not None:
        tbl.remove(old)
    grid = OxmlElement("w:tblGrid")
    for w in dxa_list:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(w))
        grid.append(gc)
    tbl.insert(1, grid)
    for row in table.rows:
        for cell, w in zip(row.cells, dxa_list):
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.append(tcW)
            tcW.set(qn("w:w"), str(w))
            tcW.set(qn("w:type"), "dxa")


def three_line(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge, sz in [("top", "12"), ("bottom", "12")]:
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), sz)
        el.set(qn("w:color"), "000000")
        borders.append(el)
    for edge in ("left", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "none")
        borders.append(el)
    tblPr.append(borders)
    trPr = table.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    trPr.append(th)
    for cell in table.rows[0].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcB = OxmlElement("w:tcBorders")
        bt = OxmlElement("w:bottom")
        bt.set(qn("w:val"), "single")
        bt.set(qn("w:sz"), "6")
        bt.set(qn("w:color"), "000000")
        tcB.append(bt)
        tcPr.append(tcB)


def add_table(caption, headers, rows, widths, aligns=None, size=9):
    tab_caption(caption)
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    set_table_geometry(t, widths)
    three_line(t)
    t.alignment = 1
    all_rows = [headers] + rows
    for i, row in enumerate(all_rows):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            if aligns and aligns[j] == "c":
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            set_run(r, size=size, bold=(i == 0))
    doc.add_paragraph()


# ---------- OMML 公式构建器 ----------
def mr(t):
    return '<m:r><m:t xml:space="preserve">%s</m:t></m:r>' % esc(t)


def msub(b, s):
    return "<m:sSub><m:e>%s</m:e><m:sub>%s</m:sub></m:sSub>" % (b, s)


def msup(b, s):
    return "<m:sSup><m:e>%s</m:e><m:sup>%s</m:sup></m:sSup>" % (b, s)


def mfrac(n, d):
    return "<m:f><m:num>%s</m:num><m:den>%s</m:den></m:f>" % (n, d)


def mrad(x):
    return ('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
            "<m:deg/><m:e>%s</m:e></m:rad>" % x)


def macc(x, ch="^"):
    return ('<m:acc><m:accPr><m:chr m:val="%s"/></m:accPr>'
            "<m:e>%s</m:e></m:acc>" % (ch, x))


def mdel(x):
    return ('<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>'
            "<m:e>%s</m:e></m:d>" % x)


def mrow(*xs):
    return "".join(xs)


def add_eq(number, inner):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT)
    omath = parse_xml('<m:oMath xmlns:m="%s" xmlns:w="%s">%s</m:oMath>'
                      % (M_NS, W_NS, inner))
    p._p.append(omath)
    set_run(p.add_run("\t（公式%s）" % number), size=12)


def note(text):
    p = doc.add_paragraph()
    set_run(p.add_run(text), size=10.5, east="楷体")


# ================= 公式对象 =================
PH = macc(mr("p"))
F1 = mrow(msub(mr("d"), mr("AA")), mr("("), msub(mr("s"), mr("i")), mr(", "),
          msub(mr("s"), mr("j")), mr(") ≤ 2"), msub(mr("R"), mr("A")),
          mr("+δ = 2×30+1.8 = 61.8 nm"))
F2 = mrow(msub(mr("d"), mr("AF")), mr("("), msub(mr("s"), mr("i")),
          mr(", 面) ≤ "), msub(mr("R"), mr("A")),
          mr("+δ = 30+1.8 = 31.8 nm"))
F3 = mrow(mr("N = round(φ·"),
          mfrac(msub(mr("V"), mr("C")), msub(mr("V"), mr("A"))), mr(")"),
          mr("，"), msub(mr("V"), mr("C")), mr(" = 10¹² nm³，"),
          msub(mr("V"), mr("A")), mr(" = π×30²×5000 ≈ 1.414×10⁷ nm³"))
F4 = mrow(mr("X(ω) = 1（L 与 R 连通），否则 X(ω) = 0"))
F5 = mrow(PH, mr(" = "), mfrac(mr("k"), mr("M")),
          mr("，k = Σ"), msub(mr("X"), mr("m")))
F6 = mrow(
    mr("95% CI = ["),
    mfrac(
        mrow(PH, mr("+"), mfrac(msup(mr("z"), mr("2")), mr("2M")), mr("−"),
             mrad(mrow(mfrac(mrow(PH, mr("(1−"), PH, mr(")")), mr("M")),
                       mr("+"),
                       mfrac(msup(mr("z"), mr("2")),
                             msup(mr("4M"), mr("2")))))),
        mrow(mr("1+"), mfrac(msup(mr("z"), mr("2")), mr("M")))),
    mr(", "),
    mfrac(
        mrow(PH, mr("+"), mfrac(msup(mr("z"), mr("2")), mr("2M")), mr("+"),
             mrad(mrow(mfrac(mrow(PH, mr("(1−"), PH, mr(")")), mr("M")),
                       mr("+"),
                       mfrac(msup(mr("z"), mr("2")),
                             msup(mr("4M"), mr("2")))))),
        mrow(mr("1+"), mfrac(msup(mr("z"), mr("2")), mr("M")))),
    mr("]，z = 1.96"))
F7 = mrow(mr("P(φ) = "),
          mfrac(mr("1"),
                mrow(mr("1+"), msup(mr("e"), mr("−(φ−φ0)/s")))))
F8 = mrow(mr("P(φ) = 1 − "),
          msup(mr("e"), mr("−a(φ−φ_c)^β")), mr("，φ > φ_c"))
F9 = mrow(mr("AIC = n·ln"), mdel(mfrac(mr("RSS"), mr("n"))), mr("+2p"))
F10 = mrow(mr("φ* = min{ N·"),
           mfrac(msub(mr("V"), mr("A")), msub(mr("V"), mr("C"))),
           mr(" ：P̂ 的 95% CI 下界 ≥ 0.90 }"))
F11 = mrow(mr("C(φA,φB) = 1000 × (1.05·φA + 0.05·φB)（元）"))
F12 = mrow(mr("min C(φA,φB)，s.t. P(φA,φB) ≥ 0.90，φA,φB ≥ 0"))
F13 = mrow(msub(mr("φ"), mr("A")), mr("+"), mr("w·"),
           msub(mr("φ"), mr("B")), mr(" ≥ "),
           msub(msup(mr("φ"), mr("*")), mr("A")))
F14 = mrow(
    mr("P(φA,φB) = "),
    mfrac(mr("1"),
          mrow(mr("1+"),
               msup(mr("e"),
                    mr("−(b0+b1φA+b2φB+b3φA²+b4φB²+b5φAφB)")))))


# ================= 四、符号说明 =================
h1("四、符号说明")
body("文中主要符号及其含义、单位见表1（符号说明表），未列出的符号在正文中说明。"
     "变量简写严格沿用题目定义；体积分数一律以百分数表示，距离单位统一为 nm，"
     "成本单位统一为元。")
add_table("表1  符号说明表",
          ["符号", "含义", "单位"],
          [["a", "微构体边长（10 μm）", "nm"],
           ["V_C", "微构体体积 = 10¹² nm³ = 1000 μm³", "nm³"],
           ["R_A", "介质 A 底面半径", "nm"],
           ["H_A", "介质 A 高（长）", "nm"],
           ["R_B", "介质 B 半径", "nm"],
           ["V_A", "单根介质 A 体积 = πR_A²H_A ≈ 1.414×10⁷", "nm³"],
           ["V_B", "单个介质 B 体积 = 4/3πR_B³ ≈ 3.35×10⁷", "nm³"],
           ["δ", "导通表面间距阈值（1.8）", "nm"],
           ["d_AA", "A-A 接触轴线距离阈值（61.8 = 2R_A+δ）", "nm"],
           ["d_AF", "A-面接触轴线距离阈值（31.8 = R_A+δ）", "nm"],
           ["d_AB", "A-B 接触距离阈值（231.8 = R_A+R_B+δ）", "nm"],
           ["d_BB", "B-B 接触距离阈值（401.8 = 2R_B+δ）", "nm"],
           ["d_BF", "B-面接触距离阈值（201.8 = R_B+δ）", "nm"],
           ["G=(V,E)", "接触图：节点集 V、边集 E", "—"],
           ["s_i", "第 i 段介质 A 的轴线线段", "—"],
           ["P_i、Q_i", "线段 s_i 的两端点坐标", "nm"],
           ["L、R", "左、右带电面节点", "—"],
           ["N_A、N_B", "介质 A、B 的数量", "根/个"],
           ["φ、φA、φB", "介质体积分数", "%"],
           ["φ*", "问题三定稿临界体积分数（1.359%，取 1.36%）", "%"],
           ["φ*_A、φ*_B", "纯 A、纯 B 的临界体积分数", "%"],
           ["w", "等效体积权重 w=φ*_A/φ*_B≈0.022", "—"],
           ["ω", "随机构型", "—"],
           ["X(ω)", "构型导通示性变量（导通为 1，否则为 0）", "—"],
           ["M", "蒙特卡洛样本量（3000/点）", "个"],
           ["k", "M 个构型中的导通构型数", "个"],
           ["P̂", "导通概率估计 = k/M", "—"],
           ["P(φ)", "导通概率", "—"],
           ["CI", "95% 置信区间", "—"],
           ["z", "标准正态分布 95% 分位数（1.96）", "—"],
           ["φ0、s", "sigmoid 模型参数", "—"],
           ["φ_c、a、β", "幂律截断模型参数", "—"],
           ["RSS", "残差平方和", "—"],
           ["AIC", "赤池信息准则", "—"],
           ["n", "样本点个数（AIC 中）", "个"],
           ["p", "模型参数个数（AIC 中）", "个"],
           ["C", "总填充成本", "元"],
           ["c_A、c_B", "介质 A、B 单价（1.05、0.05）", "元/μm³"],
           ["b0~b5", "Logistic 代理曲面系数", "—"],
           ["round(·)", "四舍五入取整", "—"],
           ["E[·]", "数学期望", "—"]],
          [2.6, 11.2, 2.2], ["c", "l", "c"], size=9)

# ================= 五、问题一 =================
h1("五、问题一模型的建立与求解")
h2("5.1 思路流程")
fig("2_各问思路流程图", "fig_q1_flow.png", "图1  问题一建模流程图")
body("问题一的核心是把“几何接触能否构成通路”转化为“图是否连通”的判定问题。"
     "整体思路分为五个阶段：首先对附件三个分表进行解析与数据解读，明确“每一行代表一段介质 A”"
     "及其边界截断存储特征；其次把每段介质抽象为图节点，并加入左、右两个带电面作为源汇节点；"
     "然后以“表面间距不超过 1.8 nm”的物理判据换算成轴线距离阈值，批量计算线段-线段、线段-面"
     "最短距离并生成接触边；随后用并查集合并所有接触节点，检查左面与右面是否同根；最后输出"
     "三组微构体的导通结论、关键断口证据与接触网络可视化。")
h2("5.2 数据预处理与可视化")
body("附件包含三个分表（组1、组2、组3），每一行表示一段介质 A，前三列与后三列分别为圆柱两顶点"
     "坐标。预处理阶段完成三项工作。")
body("第一，行-介质对应关系确认。三个分表行数分别为 12、49、535。若把每行视为一段有效介质段，"
     "则各表介质数量即行数；进一步按“同根圆柱合并”口径，组1 的 12 段可合并为 9 根圆柱，组2 的"
     "49 段合并为 39 根，组3 的 535 段合并为 354 根。组3 的 354 根圆柱恰好等于 "
     "round(0.5%×10¹²/(π×30²×5000))，说明附件组3 是体积分数约 0.5% 的随机样本，"
     "长度折算体积分数为 0.4965%。")
body("第二，边界截断特征识别。数据洞察发现，附件行距并不恒为 5000 nm，大量线段端点落在 5000 nm "
     "附近，符合“介质越界后被边界截断、分段存储”的数据生成方式。以组1 第1行与第12行为例，两段"
     "端点坐标互为周期镜像、方向向量共线，是同一根圆柱被边界切成的两段。这一发现直接支撑"
     "“每行=独立有效段”的主口径，以及“同根合并”的敏感性口径。")
body("口径处理说明：附件说明明确规定“每一行表示一个介质 A”，因此本文主判定口径将每一行视为一个"
     "独立介质段，直接按轴线距离阈值判定接触与连通，组1 不导通、组2 与组3 导通。从物理同一性看，"
     "同一根圆柱被截成的两段本质上属于同一导电体，若将其合并为一个节点，则组1 亦判定为导通"
     "（三组全部导通）。考虑到赛题以“每一行表示一个介质 A”作为附件的权威数据定义，本文正式结论按"
     "该口径给出；同时将“同根合并”的物理口径作为模型敏感性分析在第九章系统对照。两口径差异仅"
     "体现在组1，不影响组2、组3 结论及问题二~四全部结果。")
fig("3_正文结果图", "q1_data_overview.png", "图2  三组行长度分布直方图（红色虚线为标称行长 5000 nm）")
fig("3_正文结果图", "q1_boundary_example.png", "图3  组1 第1行与第12行周期镜像共线证据")
h2("5.3 模型建立")
body("设第 i 段介质 A 的轴线线段为 s_i=(P_i,Q_i)，P_i、Q_i∈ℝ³。将微构体抽象为无向图 G=(V,E)："
     "节点集合 V={s_1,…,s_N}∪{L,R}，其中 L、R 分别表示左、右带电面；边集合 E 由接触判定生成，"
     "两节点之间的最短距离不超过阈值则连边。介质表面间距不超过 1.8 nm 视为导通，介质 A 为半径 "
     "30 nm 的圆柱，因此轴线距离判据为：")
add_eq(1, F1)
add_eq(2, F2)
body("其中 d_AA 为两线段轴线之间的最短距离，d_AF 为线段轴线到带电面（x=±5000 nm 平面）的最短距离。"
     "线段-线段最短距离采用三维参数化最近点对求解：对 s(u)=P+u(Q−P)、t(v)=A+v(B−A) 求 "
     "min‖s(u)−t(v)‖ 并对 u,v∈[0,1] 做边界钳制。微构体导通当且仅当 L 与 R 在 G 中连通："
     "存在一条从 L 出发、经介质段节点、到达 R 的路径。")
add_table("表2  阈值与节点类型说明",
          ["接触类型", "判定对象", "轴线距离阈值（nm）", "表达式"],
          [["A-A", "线段-线段", "61.8", "2R_A+1.8"],
           ["A-面", "线段-带电面", "31.8", "R_A+1.8"]],
          [2.9, 4.0, 4.5, 4.5], ["c", "c", "c", "c"])
h2("5.4 模型求解")
body("算法采用“距离计算 + 并查集”两阶段实现：① 初始化并查集，令每个节点（N 段 + L + R）各自成集；"
     "② 批量计算全部 N(N−1)/2 个线段对的最短距离，以及 N 个线段到左右面的距离；③ 对距离不超过"
     "阈值的节点对执行 union 合并；④ 查询 find(L) 与 find(R)，若同根则输出“导通”，否则输出"
     "“不导通”；⑤ 若导通，在接触图上用 BFS/DFS 回溯重构一条左→右跨接路径用于可视化。距离计算"
     "全部向量化分块执行，复杂度为 O(N²) 对距离 + 并查集近似 O(Nα(N))，为完全确定性计算。"
     "三组判定结果如下。")
add_table("表3  三组微构体导通判定结果",
          ["组", "有效段数", "合并圆柱数", "主口径", "合并口径", "连通簇数", "最大连通簇段数"],
          [["组1", "12", "9", "不导通", "导通", "6", "4"],
           ["组2", "49", "39", "导通", "导通", "11", "34"],
           ["组3", "535", "354", "导通", "导通", "214", "258"]],
          [1.5, 2.1, 2.3, 2.4, 2.4, 2.2, 2.6],
          ["c", "c", "c", "c", "c", "c", "c"])
fig("3_正文结果图", "q1_group1_network.png", "图4  组1 接触网络（断口 d≈279 nm 红色虚线标注）")
fig("3_正文结果图", "q1_group2_network.png", "图5  组2 接触网络（最大簇 34 段，黑色跨接路径闭环）")
fig("3_正文结果图", "q1_group3_network.png", "图6  组3 大规模接触网络（535 节点）")
h2("5.5 结果分析与讨论")
body("主口径（每行=独立有效段、直接距离判定）下：组1 不导通、组2 导通、组3 导通。组1 不导通的"
     "关键证据是最大连通簇仅含 4 段，且左右面之间存在一处轴线距离约 279 nm 的断口，远大于 61.8 nm "
     "阈值，任何路径都无法跨过该断口。组2 与组3 均存在完整的左→右跨接路径，最大连通簇分别达 "
     "34 段与 258 段，说明当介质数量达到一定程度后，接触网络已具备宏观连通性。")
body("合并口径（同根圆柱先合并为一个节点）下三组全部导通，主要影响组1：第1行与第12行合并后，"
     "断口被同一根圆柱的周期镜像段补上。该口径差异已作为第九章敏感性分析的内容，正文以主口径"
     "结论为准并注明合并口径的判定结果，保证结论口径透明。组1 的判定按附件行独立口径给出；若按"
     "同根合并的物理口径，组1 亦导通（三组全导通），该口径差异已在第九章敏感性中对照分析。")

# ================= 六、问题二 =================
h1("六、问题二模型的建立与求解")
h2("6.1 思路流程")
fig("2_各问思路流程图", "fig_q2_flow.png", "图7  问题二建模流程图")
body("问题二需要回答“仅填充介质 A 时，微构体在不同体积分数下的导通概率”。思路分为五步："
     "数量换算得到每个体积分数对应的介质根数；按 C1 口径随机生成介质（位置均匀、方向球面均匀、"
     "完全位于盒内）；复用问题一的“距离+并查集”内核逐构型判定是否贯穿导通；对每个体积分数独立"
     "生成 M=3000 个构型做蒙特卡洛统计；最后用 Wilson 95% 置信区间刻画估计不确定性，并输出 "
     "p-φ 相变曲线、典型构型与收敛诊断。")
h2("6.2 数据预处理与可视化")
body("体积分数 φ 与介质根数 N 的换算关系为：")
add_eq(3, F3)
body("题目要求计算 φ=0.5%、0.6%、0.7%、1.0% 四个点；为刻画相变曲线并支撑问题三拟合，另补充 "
     "0.8%、0.9%、1.1%~1.5%，共 11 个点。各点根数如下。")
add_table("表4  体积分数与介质根数换算",
          ["φ(%)", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0", "1.1", "1.2", "1.3", "1.4", "1.5"],
          [["N", "354", "424", "495", "566", "637", "707", "778", "849", "920", "990", "1061"]],
          [1.6] + [1.3] * 11, ["c"] * 12)
body("随机口径确定为 C1：介质完全位于微构体内部，位置均匀、方向球面均匀、越界拒绝重采。"
     "口径辨析（第九章详述）表明，若采用周期卷回类口径（A1/B1），0.5%~1.5% 区间导通概率恒接近 1，"
     "与题目给出该区间需要“计算概率”的设定不符；只有 C1 给出非平凡相变，故全文采用 C1。")
h2("6.3 模型建立")
body("设某一体积分数 φ 下随机构型 ω，定义示性变量：")
add_eq(4, F4)
body("导通概率定义为 P(φ)=E[X]，蒙特卡洛估计量为：")
add_eq(5, F5)
body("由于 P̂ 为二项比例估计，采用 Wilson 得分区间构造 95% 置信区间，避免正态近似在概率接近 "
     "0 或 1 时区间越界：")
add_eq(6, F6)
body("单构型判定与问题一完全一致（A-A 61.8 nm、A-面 31.8 nm、并查集判连通），保证问题一至问题四"
     "“判定内核”统一。")
h2("6.4 模型求解")
body("求解算法如下：① 对每个 φ 换算 N；② 对 m=1…M，按 C1 采样生成 N 根线段（越界重采），"
     "调用算法1判定导通并记录 X_m；③ 统计 k=ΣX_m，计算 P̂ 与 Wilson 区间；④ 输出概率表、p-φ "
     "曲线、收敛诊断与多种子复现。每个 φ 的 3000 个构型按块分配至 8 个进程并行执行，单点耗时约 "
     "1~4 分钟。全部 11 点结果如下。")
add_table("表5  介质 A 导通概率（M=3000，Wilson 95% 区间）",
          ["φ(%)", "N", "M", "P̂", "95% CI"],
          [["0.5", "354", "3000", "0.060", "[0.052, 0.069]"],
           ["0.6", "424", "3000", "0.214", "[0.200, 0.229]"],
           ["0.7", "495", "3000", "0.364", "[0.347, 0.382]"],
           ["0.8", "566", "3000", "0.506", "[0.488, 0.524]"],
           ["0.9", "637", "3000", "0.631", "[0.614, 0.648]"],
           ["1.0", "707", "3000", "0.730", "[0.714, 0.746]"],
           ["1.1", "778", "3000", "0.805", "[0.791, 0.819]"],
           ["1.2", "849", "3000", "0.863", "[0.850, 0.875]"],
           ["1.3", "920", "3000", "0.902", "[0.891, 0.912]"],
           ["1.4", "990", "3000", "0.929", "[0.920, 0.938]"],
           ["1.5", "1061", "3000", "0.949", "[0.941, 0.957]"]],
          [1.8, 2.2, 2.2, 2.4, 7.4],
          ["c", "c", "c", "c", "c"])
fig("3_正文结果图", "q2_p_phi_curve.png", "图8  p-φ 相变曲线")
fig("3_正文结果图", "q2_convergence_1.00%.png", "图9  φ=1.0% 处样本量收敛曲线")
fig("3_正文结果图", "q2_typical_configs.png", "图10  导通/不导通典型构型接触网络对比")
fig("3_正文结果图", "q2_cluster_sizes.png", "图11  φ=0.7%/1.0% 渗流簇大小分布")
fig("3_正文结果图", "q2_evolution.png", "图12  φ=0.5%~1.5% 相变演化多面板")
h2("6.5 结果分析与讨论")
body("导通概率随体积分数呈典型 S 形相变：0.5% 时仅 6.0%，1.0% 时升至 73.0%，1.5% 时达到 94.9%，"
     "相变主体位于 0.6%~1.2% 区间。收敛诊断显示累积估计在 M 约 1000 后趋于稳定，且 6 个随机种子"
     "（每种子 M=300）的合并结果与总样本一致（1.0% 处合并 P̂=0.733），说明 3000 样本量足以支撑 "
     "0.01 量级的概率分辨率。")
body("从渗流结构看，φ=0.7% 时最大连通簇仅占全部介质约一半，且未跨接；φ=1.0% 时最大簇占比升至 "
     "80% 以上并出现稳定跨接路径。这一“孤立簇→跨接→全导通”的演化过程与经典渗流理论一致，"
     "也是问题三求解 φ* 的物理基础。")

# ================= 七、问题三 =================
h1("七、问题三模型的建立与求解")
h2("7.1 思路流程")
fig("2_各问思路流程图", "fig_q3_flow.png", "图13  问题三建模流程图")
body("问题三要求在“导通概率不低于 90%”的约束下求最低体积分数 φ*，并精确到 0.01%。为保证结论"
     "不被单一方法绑架，采用“渗透模型拟合反解 ⊕ 概率二分”双方法互证：先由粗扫蒙特卡洛曲线拟合"
     "渗透模型并解析反解；再用整数 N 层面的概率二分给出保守解；最后在双方法区间内做 N 层面高样本"
     "细化扫描，以“95% CI 下界 ≥ 0.90”为可行判据定稿，并用 3 个随机种子终验。")
h2("7.2 数据准备")
body("直接复用问题二 11 点高精度概率表（表5）作为拟合与二分的数据基础。二分与细化阶段按需在 φ* "
     "邻域补充高样本蒙特卡洛（M=3000/点），保证判据的统计强度。")
h2("7.3 模型建立")
body("渗透模型拟合采用两种函数形式：")
add_eq(7, F7)
add_eq(8, F8)
body("参数由加权非线性最小二乘估计（权重取 Wilson 区间宽度的倒数），模型选择依据 AIC：")
add_eq(9, F9)
body("拟合反解即求 P(φ*)=0.90 的根。概率二分以整数 N 为决策变量：对候选 N，φ=N·V_A/V_C，做 "
     "M 样本蒙特卡洛；若 CI 下界 ≥0.90 则判“可行”，否则“不可行”；按二分规则收缩区间，得到保守"
     "的 φ*_bis。最终判据统一为：")
add_eq(10, F10)
h2("7.4 模型求解")
body("① 由表5 拟合 sigmoid 与幂律，AIC 选优，解析反解 φ*_fit；② 整数 N 二分（初始区间 "
     "0~round(2%×V_C/V_A)），M=3000/点，得 φ*_bis；③ 在 [min(φ*_fit,φ*_bis)−0.05%, "
     "max(φ*_fit,φ*_bis)+0.05%] 内取约 9 个 N 层面点，各 M=3000，按公式10取最小可行 N；"
     "④ 定稿 φ*_final 处用 3 个随机种子 × M=3000 合并终验。拟合参数与三方法结果如下。")
add_table("表6  渗透模型拟合参数",
          ["模型", "AIC", "拟合反解 φ*"],
          [["sigmoid", "−26.1", "1.229%"],
           ["幂律截断（最优）", "−80.6", "1.298%"]],
          [5.5, 4.0, 5.0], ["c", "c", "c"])
add_table("表7  φ* 邻域 N 层面细化扫描（M=3000/点）",
          ["N", "φ(%)", "P̂", "95% CI", "可行"],
          [["883", "1.248", "0.873", "[0.861, 0.885]", "否"],
           ["898", "1.270", "0.882", "[0.870, 0.893]", "否"],
           ["914", "1.292", "0.890", "[0.879, 0.901]", "否"],
           ["929", "1.313", "0.896", "[0.885, 0.906]", "否"],
           ["945", "1.336", "0.904", "[0.893, 0.914]", "否"],
           ["961", "1.359", "0.911", "[0.900, 0.921]", "是"],
           ["976", "1.380", "0.916", "[0.906, 0.925]", "是"],
           ["992", "1.402", "0.924", "[0.914, 0.933]", "是"],
           ["1008", "1.425", "0.930", "[0.920, 0.938]", "是"]],
          [1.8, 2.4, 2.2, 7.0, 1.8], ["c", "c", "c", "c", "c"])
add_table("表8  三方法 φ* 与终验",
          ["方法", "φ*", "N", "终验 M", "P̂", "95% CI", "满足"],
          [["拟合反解", "1.298%", "918", "3000", "0.891", "[0.880, 0.902]", "否"],
           ["概率二分", "1.376%", "973", "3000", "0.914", "[0.903, 0.924]", "是"],
           ["细化定稿", "1.359%", "961", "9000（3种子×3000）", "0.911", "[0.905, 0.917]", "是"]],
          [2.25, 2.1, 1.75, 3.7, 1.75, 2.8, 1.5],
          ["c", "c", "c", "c", "c", "c", "c"])
fig("3_正文结果图", "q3_fit_curve.png", "图14  渗透模型拟合与双方法 φ* 标注")
fig("3_正文结果图", "q3_phi_star_zoom.png", "图15  φ* 邻域局部放大（M=3000）")
fig("3_正文结果图", "q3_methods_compare.png", "图16  三方法 φ* 与终验 P̂ 双轴对比")
fig("3_正文结果图", "q3_diagnostics.png", "图17  拟合曲线与残差诊断（AIC/RMSE）")
h2("7.5 结果分析与讨论")
body("定稿 φ*=1.359%（N=961），对应体积分数精确到两位小数为 1.36%，3 种子合并终验 P̂=0.911、"
     "95% CI=[0.905,0.917]，CI 下界高于 0.90，满足题目“概率不低于 90%”的可靠性要求。")
body("三方法对比体现了统计严谨性的价值：拟合反解（1.298%）点估计虽越过 90%，但其 CI 下界仅 "
     "0.880，按“CI 下界≥0.90”的判据并不达标，属于偏乐观解；概率二分（1.376%）全程保守；"
     "细化定稿（1.359%）介于两者之间且为满足判据的最小值。拟合诊断显示幂律截断残差在 Wilson "
     "区间内随机绕零（RMSE 约 0.3%），sigmoid 残差呈系统性 S 形（RMSE 约 4%），AIC 相差 54.5，"
     "模型选择明确；同时两条拟合曲线在 P=90% 附近几乎重合，说明 φ* 对模型形式不敏感，互证成立。")

# ================= 八、问题四 =================
h1("八、问题四模型的建立与求解")
h2("8.1 思路流程")
fig("2_各问思路流程图", "fig_q4_flow.png", "图18  问题四建模流程图")
body("问题四在同时填充介质 A（1.05 元/μm³）与介质 B（0.05 元/μm³）时，求“导通概率不低于 90%”"
     "约束下总成本最低的填充量。思路分为四步：先标定纯 A、纯 B 基线并计算等效体积权重；理论层用"
     "线性规划求成本下界；工程层用代理曲面做二维搜索给出混合候选；所有候选必须经真实蒙特卡洛验证，"
     "最终从可行集中取成本最小者，并输出成本-概率前沿。")
h2("8.2 数据准备与基线可视化")
fig("3_正文结果图", "concept_geometry.png", "图19  微构体几何模型与接触阈值判定概念图")
body("基线数据包括：纯 A 概率曲线（问题二表5，含 φ*_A=1.359%）；纯 B 体积分数扫描 0.25~0.60 "
     "（M=400/点）；混合二维粗网格 φA∈{0,0.25%,…,1.5%} × φB∈{0,5%,…,30%}（M=100/点）；"
     "混合区细化 φA∈{0.5%,0.75%,1.0%,1.25%} × φB∈{20%~35%，步长 2.5%}（M=500/点）。"
     "全部点均为真实蒙特卡洛，用于代理拟合、前沿与验证。")
add_table("表9  问题四数据点设计",
          ["数据集", "覆盖范围", "样本量/点", "点数"],
          [["纯 B 扫描", "φB=25%~60%", "400", "10"],
           ["纯 A 高值", "φA=1.35%~2.0%", "400", "4"],
           ["混合粗网格", "φA×φB=7×6", "100", "42"],
           ["混合细化", "φA×φB=4×7", "500", "28"]],
          [4.2, 6.0, 3.4, 2.4], ["c", "c", "c", "c"])
h2("8.3 模型建立")
body("微构体体积 V_C=1000 μm³（10 μm 边长立方体），总成本为：")
add_eq(11, F11)
body("优化问题为：")
add_eq(12, F12)
body("其中 P(φA,φB) 为混合体系导通概率（A 圆柱与 B 球共存，接触阈值 A-A 61.8、A-B 231.8、"
     "B-B 401.8、A-面 31.8、B-面 201.8 nm，判定仍为并查集）。由于纯 B 达标体积分数远高于纯 A，"
     "引入等效体积权重 w=φ*_A/φ*_B≈0.022，将约束松弛为线性形式：")
add_eq(13, F13)
body("得到理论层线性规划：min 1.05φA+0.05φB，s.t. φA+wφB≥φ*_A。工程层以 Logistic 代理曲面"
     "拟合概率：")
add_eq(14, F14)
body("并以罚函数 SLSQP 做二维搜索得到混合候选。")
h2("8.4 模型求解")
body("① 标定 φ*_A（问题三定稿）、φ*_B（纯 B 扫描按 CI 规则插值）；② 计算 w，解 LP 得极点 "
     "(φA,φB)；③ 用粗网格+细化点拟合代理曲面，2D 优化得混合候选；④ 所有候选（纯A、纯B、LP极点、"
     "2D候选、混合试探、混合细化最优）做真实 MC 验证（M=1000）；⑤ 可行集中取成本最小者为最优，"
     "输出成本-概率前沿。候选验证结果如下（成本单位为元）。")
add_table("表10  候选方案真实 MC 验证（M=1000）",
          ["候选方案", "φA(%)", "φB(%)", "成本（元）", "P̂", "95% CI", "可行"],
          [["纯 A（问题三 φ*）", "1.359", "0", "14.27", "0.932", "[0.915, 0.946]", "是"],
           ["纯 B（φ*_B≈61.4%）", "0", "61.43", "30.71", "0.902", "[0.882, 0.919]", "否"],
           ["LP 极点", "1.359", "0", "14.27", "同纯A", "—", "是"],
           ["2D 代理优化", "1.114", "0.244", "11.82", "0.818", "[0.793, 0.841]", "否"],
           ["混合试探 1.0%A+30%B", "1.000", "30.00", "25.50", "0.842", "[0.818, 0.863]", "否"],
           ["混合细化最优 (1.25%A+30%B)", "1.250", "30.00", "28.13", "0.941", "[0.925, 0.954]", "是"]],
          [4.1, 1.6, 1.8, 2.4, 1.7, 2.9, 1.4],
          ["c", "c", "c", "c", "c", "c", "c"])
add_table("表11  三方案成本对比",
          ["方案", "体积分数合计(%)", "成本（元）"],
          [["纯 A（φ*=1.359%）", "1.359", "14.27"],
           ["纯 B（φ*_B≈61%，未达标）", "61.43", "30.71"],
           ["混合最优（退化为纯 A）", "1.359", "14.27"]],
          [8.0, 4.8, 3.2], ["c", "c", "c"])
fig("3_正文结果图", "q4_contour.png", "图20  A+B 概率曲面等高线与候选点")
fig("3_正文结果图", "q4_frontier.png", "图21  成本-导通概率前沿（全部真实 MC 点）")
fig("3_正文结果图", "q4_comparison.png", "图22  纯A/纯B/混合最优成本柱状图")
fig("3_正文结果图", "q4_pure_curves.png", "图23  A/B 导通效率对比与面接触瓶颈标注")
fig("3_正文结果图", "concept_bottleneck.png", "图24  球体“面接触瓶颈”机理示意")
h2("8.5 结果分析与讨论")
body("最优方案为纯 A：φ*=1.359%，总成本 14.27 元。纯 B 即使在 61.4%（外推，已超过 60% 扫描上限）"
     "体积分数下，P̂=0.902 但 CI 下界仅 0.882，按“CI 下界≥0.90”判据仍不达标，且成本 30.71 元是"
     "纯 A 的 2.15 倍；混合区最便宜的可行点 (1.25%A, 30%B) 成本 28.13 元，也远高于纯 A。因此"
     "理论层 LP 极点、工程层优化与真实验证一致指向纯 A。")
body("机理上，球形介质 B 存在“面接触瓶颈”：B 球完全位于盒内时，球心距带电面必须 ≤201.8 nm 才能"
     "接触，而球半径 200 nm 使有效贴面厚度仅约 1.8 nm；即使体相已渗流（60% 时 P≈0.90），也很难"
     "同时贴紧左右两面形成跨接。相比之下，A 圆柱轴线距面 ≤31.8 nm 即接触，单根长 5000 nm 可贴面"
     "并深入体相，多根链式跨接即可导通，因此 A 在体积分数与成本两个维度上均占优。")
body("另一个值得强调的工程结论是：代理曲面给出的混合候选（11.82 元）表面成本更低，但真实蒙特卡洛"
     "验证 P̂=0.818 不达标，说明代理模型在可行边界附近存在系统性乐观偏差，任何优化候选都必须经过"
     "真实 MC 验证才能采信——这也是方法设计中“理论层+工程层+验证层”三层并行的意义所在。")

# 收尾：保证 sectPr 在 body 末尾
sectPr = body_el.find(qn("w:sectPr"))
if sectPr is not None:
    body_el.remove(sectPr)
    body_el.append(sectPr)

doc.save(FINAL)
print("SAVED", FINAL)
