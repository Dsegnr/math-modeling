# -*- coding: utf-8 -*-
"""把 pdf2docx 生成的公式表格重构为规范公式段：
公式居中 + 编号右对齐（制表位），文本取自原 PDF 公式原文。
"""
import re
import docx
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"D:\数模竞赛\华数杯2026\A题项目\华数杯2026_A题\写作素材\华数杯论文_精修版.docx"
d = docx.Document(SRC)
body = d.element.body

# 公式原文映射（编号 -> 规范文本；原 PDF 提取）
F = {
    1: "G=(V, E), V={s1,…,sN, L, R}, E={(u,v)|d(u,v)≤TH}",
    2: "dAA(si,sj)≤2RA+δ=2×30+1.8=61.8 nm",
    3: "dAF(si,F)≤RA+δ=30+1.8=31.8 nm",
    4: "dAB=RA+RB+δ=231.8 nm, dBB=2RB+δ=401.8 nm, dBF=RB+δ=201.8 nm",
    5: "d(si,sj)=min_{u,v∈[0,1]} |si(u)−sj(v)|",
    6: "导通 ⇔ find(L)=find(R)",
    7: "N=round(φVC/(100VA))",
    8: "VA=πRA²HA=π×30²×5000≈1.414×10⁷ nm³, VB=(4/3)πRB³≈3.35×10⁷ nm³",
    9: "X(ω)=1（L与R连通），0（L与R不连通）",
    10: "P(φ)=E[X(ω)]",
    11: "P̂=p̂=k/M, k=Σm=1..M X(ωm)",
    12: "Var(P̂)≈P(φ)[1−P(φ)]/M≈p̂(1−p̂)/M",
    13: "CI95%=[(A−B)/C, (A+B)/C], A=p̂+z²/(2M), B=z√(p̂(1−p̂)/M+z²/(4M²)), C=1+z²/M",
    14: "P(φ)=1/(1+exp[−(φ−φ0)/s])",
    15: "P(φ)=1−exp[−a(φ−φc)ᵝ], φ>φc",
    16: "minθ Σi=1..n wi[P̂i−P(φi;θ)]²",
    17: "AIC=n ln(RSS)+2p",
    18: "P(φ*)=0.90",
    19: "φ=100NVA/VC %",
    20: "N*=min{N:L95(N)≥0.90}",
    21: "φ*=100N*VA/VC %",
    22: "Nmid=⌊(Nlo+Nhi)/2⌋",
    23: "C(ϕA,ϕB)=1000×(1.05ϕA+0.05ϕB)",
    24: "min C(ϕA,ϕB), s.t. P(ϕA,ϕB)≥0.90, ϕA,ϕB≥0",
    25: "ϕA+w·ϕB≥ϕ*A",
    26: "w=ϕ*A/ϕ*B≈0.022",
    27: "CB=1000·cB·(ϕ*A/w)",
    28: "cA·ϕ*A<cB·ϕ*A/w ⇔ w<cB/cA≈0.0476",
    29: "min 1.05ϕA+0.05ϕB, s.t. ϕA+wϕB≥ϕ*A",
    30: "P(ϕA,ϕB)=1/(1+e^(−(b0+b1ϕA+b2ϕB+b3ϕA²+b4ϕB²+b5ϕAϕB)))",
    31: "min C(ϕA,ϕB)+λ·max(0, 0.90−Psurf(ϕA,ϕB))",
    32: "tB,eff=(RB+δ)−RB=δ=1.8 nm",
    33: "η=(d−TH)/TH",
    34: "Δ(M)≈z√(P̂(1−P̂)/M)",
    35: "M≥z²P̂(1−P̂)/ε², z=1.96",
    36: "ΔP(φ)=PA1(φ)−PC1(φ)",
    37: "Δφ*=φ*(f)−φ*(1)",
    38: "S=(Δφ*/φ*)/(Δf/f)",
}


def make_formula_para(formula_text, num):
    """构造公式段落：居中 tab + 右对齐 tab。"""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    for pos, align in (("4536", "center"), ("9072", "right")):
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), align)
        tab.set(qn("w:pos"), pos)
        tabs.append(tab)
    pPr.append(tabs)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:line"), "240")
    spacing.set(qn("w:lineRule"), "auto")
    spacing.set(qn("w:after"), "0")
    pPr.append(spacing)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "left")
    pPr.append(jc)
    p.append(pPr)
    # 公式 run
    r1 = OxmlElement("w:r")
    rPr1 = OxmlElement("w:rPr")
    rf1 = OxmlElement("w:rFonts")
    rf1.set(qn("w:ascii"), "Times New Roman")
    rf1.set(qn("w:hAnsi"), "Times New Roman")
    rf1.set(qn("w:eastAsia"), "宋体")
    rPr1.append(rf1)
    sz1 = OxmlElement("w:sz")
    sz1.set(qn("w:val"), "24")
    rPr1.append(sz1)
    r1.append(rPr1)
    t1 = OxmlElement("w:t")
    t1.text = formula_text
    r1.append(t1)
    p.append(r1)
    # tab run
    r2 = OxmlElement("w:r")
    tab_el = OxmlElement("w:tab")
    r2.append(tab_el)
    p.append(r2)
    # 编号 run
    r3 = OxmlElement("w:r")
    rPr3 = OxmlElement("w:rPr")
    rf3 = OxmlElement("w:rFonts")
    rf3.set(qn("w:ascii"), "Times New Roman")
    rf3.set(qn("w:hAnsi"), "Times New Roman")
    rf3.set(qn("w:eastAsia"), "宋体")
    rPr3.append(rf3)
    sz3 = OxmlElement("w:sz")
    sz3.set(qn("w:val"), "24")
    rPr3.append(sz3)
    r3.append(rPr3)
    t3 = OxmlElement("w:t")
    t3.text = f"({num})"
    r3.append(t3)
    p.append(r3)
    return p


# 收集所有公式表格（含编号），按 body 顺序处理
appendix_p = None
for par in d.paragraphs:
    t = par.text.strip()
    if t.startswith("附") and "录" in t[:6]:
        appendix_p = par._p
        break


def in_main(el):
    if appendix_p is None:
        return True
    for child in body.iterchildren():
        if child is el:
            return True
        if child is appendix_p:
            return False
    return True


rebuilt = 0
skipped = []
for tbl in list(d.tables):
    if not in_main(tbl._tbl):
        continue
    txt = "".join(c.text for row in tbl.rows for c in row.cells)
    nums = [int(n) for n in re.findall(r"\((\d{1,2})\)", txt)]
    if not nums:
        continue
    nums = sorted(set(nums))
    # 生成公式段（按编号）
    paras = []
    ok = True
    for n in nums:
        if n not in F:
            skipped.append((n, txt[:40]))
            ok = False
            break
        paras.append(make_formula_para(F[n], n))
    if not ok:
        continue
    # 在表格位置插入公式段（表格前）
    for p_el in paras:
        tbl._tbl.addprevious(p_el)
    body.remove(tbl._tbl)
    rebuilt += 1

print("重构公式表:", rebuilt)
if skipped:
    print("未覆盖编号:", skipped)
d.save(SRC)
print("SAVED")
