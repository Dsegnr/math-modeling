# -*- coding: utf-8 -*-
"""按 APMCM 获奖论文格式规范化华数杯论文（正文区；附录/参考文献内容不动）。

规范：
- 页面：A4，四边距 2.5cm；
- Normal：宋体(eastAsia)/Times New Roman(ascii) 12pt，单倍行距，段后 0；
- 标题：一级黑体 14pt 加粗、二级黑体 12pt 加粗（段前 8pt），独立成段；
- 正文：宋体/Times 12pt，首行缩进 2 字符，单倍行距，段后 0；
- 图注/表注：9pt 居中，表注加粗，编号"图1  标题"（去冒号）；
- 数据表格：三线表（上 1.5pt/表头下 0.75pt/下 1.5pt，无竖线），9pt；
- 公式表格：去掉边框（保留 pdf2docx 的公式内容布局）。
"""
import copy
import re
import docx
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = r"D:\数模竞赛\华数杯2026\A题项目\华数杯2026_A题\写作素材\华数杯论文_精修版.docx"
d = docx.Document(SRC)
body = d.element.body

# 找到附录标题段（正文区边界）
appendix_p = None
for par in d.paragraphs:
    t = par.text.strip()
    if t.startswith("附") and "录" in t[:6]:
        appendix_p = par._p
        break
print("附录锚点:", appendix_p is not None)


def in_main(el):
    if appendix_p is None:
        return True
    for child in body.iterchildren():
        if child is el:
            return True
        if child is appendix_p:
            return False
    return True


def set_run_font(r, ea="宋体", ascii_f="Times New Roman", size=12, bold=None):
    rPr = r._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), ascii_f)
    rFonts.set(qn("w:hAnsi"), ascii_f)
    rFonts.set(qn("w:eastAsia"), ea)
    r.font.size = Pt(size)
    if bold is not None:
        r.font.bold = bold


# ---------- 1) 页面边距 ----------
sec = d.sections[0]
sec.top_margin = Cm(2.5)
sec.bottom_margin = Cm(2.5)
sec.left_margin = Cm(2.5)
sec.right_margin = Cm(2.5)
print("页面边距已设 2.5cm")

# ---------- 2) Normal 样式 ----------
st = d.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(12)
rpr = st.element.get_or_add_rPr()
rf = rpr.find(qn("w:rFonts"))
if rf is None:
    rf = OxmlElement("w:rFonts")
    rpr.insert(0, rf)
rf.set(qn("w:ascii"), "Times New Roman")
rf.set(qn("w:hAnsi"), "Times New Roman")
rf.set(qn("w:eastAsia"), "宋体")
pPr = st.element.get_or_add_pPr()
sp = pPr.find(qn("w:spacing"))
if sp is None:
    sp = OxmlElement("w:spacing")
    pPr.append(sp)
sp.set(qn("w:after"), "0")
sp.set(qn("w:line"), "240")
sp.set(qn("w:lineRule"), "auto")
print("Normal 样式已设")

# ---------- 3) 拆分标题+正文合并段 ----------
paras = d.paragraphs
split_count = 0
for par in list(paras):
    if not in_main(par._p):
        continue
    t = par.text
    if not re.match(r"^\d+(\.\d+)?\t", t):
        continue
    if "\n" not in t:
        continue
    # 换行在 XML 中是 w:br 元素；按文档顺序收集 w:br 前后的 w:t
    br = None
    for el in par._p.iter():
        if el.tag == qn("w:br"):
            br = el
            break
    if br is None:
        continue
    before_wts = []
    after_wts = []
    found = False
    for el in par._p.iter():
        if el is br:
            found = True
            continue
        if el.tag == qn("w:t"):
            (after_wts if found else before_wts).append(el)
    title_text = "".join(w.text or "" for w in before_wts)
    # 标题段：深拷贝原段，只保留标题文本（第一个 w:t），清空其余，删除 w:br
    title_p = copy.deepcopy(par._p)
    first_t = True
    for wt in title_p.iter(qn("w:t")):
        if first_t:
            wt.text = title_text
            first_t = False
        else:
            wt.text = ""
    for b in title_p.iter(qn("w:br")):
        b.getparent().remove(b)
    # 原段改为正文段：清空 w:br 前的 w:t，删除 w:br，保留之后的 w:t
    for wt in before_wts:
        wt.text = ""
    if after_wts:
        after_wts[0].text = (after_wts[0].text or "").lstrip("\t")
    br.getparent().remove(br)
    par._p.addprevious(title_p)
    split_count += 1
print("拆分标题合并段:", split_count)

# ---------- 4) 标题格式 ----------
paras = d.paragraphs
h1 = h2 = 0
for par in paras:
    if not in_main(par._p):
        continue
    t = par.text.strip()
    if re.match(r"^\d+\t", t):
        for r in par.runs:
            set_run_font(r, ea="黑体", ascii_f="Times New Roman", size=14, bold=True)
        pf = par.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(12)
        pf.space_after = Pt(6)
        pf.line_spacing = 1.0
        h1 += 1
    elif re.match(r"^\d+\.\d+\t", t):
        for r in par.runs:
            set_run_font(r, ea="黑体", ascii_f="Times New Roman", size=12, bold=True)
        pf = par.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(8)
        pf.space_after = Pt(4)
        pf.line_spacing = 1.0
        h2 += 1
print("一级标题:", h1, "二级标题:", h2)

# ---------- 5) 正文段落格式 ----------
paras = d.paragraphs
body_count = 0
for par in paras:
    if not in_main(par._p):
        continue
    t = par.text.strip()
    if not t:
        continue
    if re.match(r"^\d+(\.\d+)?\t", t):
        continue
    if re.match(r"^(图|表)\d+[:：]", t):
        continue
    if t.startswith(("摘要", "关键词")):
        continue
    if par._p.findall(".//" + qn("w:drawing")):
        continue
    # 跳过子图注 (a)(b)(c)
    if re.match(r"^\([a-d]\)", t):
        continue
    pf = par.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.line_spacing = 1.0
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    # 首行缩进 2 字符
    pPr = par._p.get_or_add_pPr()
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    ind.set(qn("w:firstLineChars"), "200")
    ind.set(qn("w:firstLine"), "480")
    # 字体：普通 run 统一宋体/Times 12pt（跳过含数学符号字体的 run）
    for r in par.runs:
        if r.font.element.rPr is not None and r.font.element.rPr.rFonts is not None:
            ea = r.font.element.rPr.rFonts.get(qn("w:eastAsia"))
            if ea in ("CMMI12", "CMSY8", "CMEX10", "CMMI10", "CMSY10"):
                continue
        set_run_font(r, ea="宋体", ascii_f="Times New Roman", size=12)
    body_count += 1
print("正文段落格式化:", body_count)

# ---------- 6) 图注/表注 ----------
paras = d.paragraphs
cap = 0
for par in paras:
    if not in_main(par._p):
        continue
    t = par.text.strip()
    m = re.match(r"^(图|表)(\d+)[:：]\s*(.*)", t)
    if not m:
        continue
    kind, num, title = m.group(1), m.group(2), m.group(3)
    is_tbl = kind == "表"
    new_text = f"{kind}{num}  {title}"
    if not par.runs:
        par.add_run(new_text)
    else:
        par.runs[0].text = new_text
        for r in par.runs[1:]:
            r.text = ""
        for r in par.runs:
            set_run_font(r, ea="宋体", ascii_f="Times New Roman", size=9, bold=is_tbl)
    pf = par.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.line_spacing = 1.0
    cap += 1
print("图注/表注格式化:", cap)

# ---------- 7) 表格：三线表 / 公式表去边框 ----------
def set_tbl_borders(tbl, none=False):
    tblPr = tbl._tbl.tblPr
    borders = tblPr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tblPr.append(borders)
    for tag in ("w:top", "w:left", "w:bottom", "w:right", "w:insideH", "w:insideV"):
        el = borders.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            borders.append(el)
        if none:
            el.set(qn("w:val"), "none")
            el.set(qn("w:sz"), "0")
            el.set(qn("w:space"), "0")
        else:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")


def is_formula_tbl(tbl):
    txt = "".join(c.text for row in tbl.rows for c in row.cells)
    return bool(re.search(r"\(\d+\)", txt)) and len(tbl.rows) <= 4 and len(txt) < 300


data_tbl = 0
formula_tbl = 0
for tbl in d.tables:
    if not in_main(tbl._tbl):
        continue
    if is_formula_tbl(tbl):
        set_tbl_borders(tbl, none=True)
        # 公式表单元格字号保持（数学符号），但去掉编号单元格的杂散格式
        formula_tbl += 1
        continue
    # 数据表：三线表
    set_tbl_borders(tbl, none=False)
    # 上下 1.5pt（sz=12），表头下 0.75pt（sz=6）单独处理表头行
    tblPr = tbl._tbl.tblPr
    borders = tblPr.find(qn("w:tblBorders"))
    for tag, sz in (("w:top", "12"), ("w:bottom", "12")):
        el = borders.find(qn(tag))
        el.set(qn("w:sz"), sz)
    # 表头行下边框
    if tbl.rows:
        for cell in tbl.rows[0].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcB = tcPr.find(qn("w:tcBorders"))
            if tcB is None:
                tcB = OxmlElement("w:tcBorders")
                tcPr.append(tcB)
            bottom = tcB.find(qn("w:bottom"))
            if bottom is None:
                bottom = OxmlElement("w:bottom")
                tcB.append(bottom)
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "0")
            bottom.set(qn("w:color"), "000000")
    # 单元格字号 9pt、居中
    for row in tbl.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
                par.paragraph_format.space_before = Pt(0)
                par.paragraph_format.space_after = Pt(0)
                par.paragraph_format.line_spacing = 1.0
                for r in par.runs:
                    if r.font.size is None or r.font.size.pt > 10:
                        set_run_font(r, ea="宋体", ascii_f="Times New Roman", size=9)
    data_tbl += 1
print("数据表三线表:", data_tbl, "公式表去边框:", formula_tbl)

# ---------- 8) 摘要/关键词 ----------
paras = d.paragraphs
for par in paras:
    t = par.text.strip()
    if t == "摘要":
        for r in par.runs:
            set_run_font(r, ea="黑体", ascii_f="Times New Roman", size=14, bold=True)
        pf = par.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf.space_before = Pt(6)
        pf.space_after = Pt(6)
    elif t.startswith("关键词"):
        for i, r in enumerate(par.runs):
            set_run_font(r, ea="宋体", ascii_f="Times New Roman", size=12,
                         bold=(i == 0 and r.text.strip().endswith("：")))
        pf = par.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.space_before = Pt(6)
        pf.space_after = Pt(6)

d.save(SRC)
print("SAVED:", SRC)
