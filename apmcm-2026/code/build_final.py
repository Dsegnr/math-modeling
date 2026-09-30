# -*- coding: utf-8 -*-
"""Final DOCX builder — equations embedded directly at correct positions."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from paper_content import *

from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls, qn
from docx.oxml import parse_xml, OxmlElement
from lxml import etree

BASE = r'D:\数模竞赛'
FIG = os.path.join(BASE, 'newfigures')
FALLBACK = os.path.join(BASE, 'figures')
doc = Document()

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
X = '{http://www.w3.org/XML/1998/namespace}space'
MT = lambda t: '{%s}%s' % (M, t)
eq_counter = [0]  # mutable counter

# ===== Page Setup =====
for s in doc.sections:
    s.page_width = Cm(21.0); s.page_height = Cm(29.7)
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Cm(2.5)

style = doc.styles['Normal']
style.font.name = 'Times New Roman'; style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
style.paragraph_format.line_spacing = 1.0
style.paragraph_format.space_after = Pt(0)

def set_font(run, cn='宋体', en='Times New Roman', sz=Pt(12)):
    run.font.name = en; run.font.size = sz
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None: rf = OxmlElement('w:rFonts'); rPr.insert(0, rf)
    rf.set(qn('w:eastAsia'), cn); rf.set(qn('w:ascii'), en); rf.set(qn('w:hAnsi'), en)

def H1(t):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = True
    set_font(r, '黑体', 'Times New Roman', Pt(14))
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.line_spacing = 1.0

def H2(t):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = True
    set_font(r, '黑体', 'Times New Roman', Pt(12))
    p.paragraph_format.space_before = Pt(8); p.paragraph_format.line_spacing = 1.0

def P(t):
    p = doc.add_paragraph(); r = p.add_run(t)
    set_font(r, '宋体', 'Times New Roman', Pt(12))
    p.paragraph_format.first_line_indent = Cm(0.74); p.paragraph_format.line_spacing = 1.0
    return p

def C(t, sz=12, b=False):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(t); r.bold = b
    set_font(r, '宋体' if not b else '黑体', 'Times New Roman', Pt(sz))
    p.paragraph_format.line_spacing = 1.0

def QR(label, text):
    p = doc.add_paragraph(); r = p.add_run(label+'：'); r.bold = True
    set_font(r, '宋体', 'Times New Roman', Pt(12))
    r = p.add_run(text); set_font(r, '宋体', 'Times New Roman', Pt(12))
    p.paragraph_format.first_line_indent = Cm(0.74); p.paragraph_format.line_spacing = 1.0

def Img(fn, cap, w=5.0):
    base = fn.replace('.pdf','.png'); cn = base.replace('.png','_CN.png')
    for d in [FIG, FALLBACK]:
        path = os.path.join(d, cn)
        if not os.path.exists(path): path = os.path.join(d, base)
        if os.path.exists(path): doc.add_picture(path, width=Inches(w)); break
    cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cp.add_run(cap); set_font(r, '宋体', 'Times New Roman', Pt(9))
    cp.paragraph_format.line_spacing = 1.0

def T3(cap, hdrs, data):
    if cap:
        cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(cap); r.bold = True; set_font(r, '宋体', 'Times New Roman', Pt(9))
    nr, nc = len(data)+1, len(hdrs)
    tbl = doc.add_table(rows=nr, cols=nc); tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    t = tbl._tbl; tp = t.tblPr or parse_xml('<w:tblPr %s></w:tblPr>'%nsdecls('w'))
    tp.append(parse_xml('<w:tblBorders %s>'%nsdecls('w')+
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/></w:tblBorders>'))
    for j, h in enumerate(hdrs):
        c = tbl.rows[0].cells[j]; c.text = ''
        pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER; pp.paragraph_format.line_spacing = 1.0
        rr = pp.add_run(str(h)); rr.bold = True; set_font(rr, '宋体', 'Times New Roman', Pt(9))
        tc = c._tc.get_or_add_tcPr()
        tc.append(parse_xml('<w:tcBorders %s><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>'%nsdecls('w')))
    for i, rd in enumerate(data):
        for j, v in enumerate(rd):
            c = tbl.rows[i+1].cells[j]; c.text = ''
            pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER; pp.paragraph_format.line_spacing = 1.0
            rr = pp.add_run(str(v)); set_font(rr, '宋体', 'Times New Roman', Pt(9))

# ===== OMML equation builder =====
def mr(s, it=True):
    r = etree.Element(MT('r'))
    if not it:
        rPr = etree.SubElement(r, MT('rPr')); etree.SubElement(rPr, MT('nor'))
    t = etree.SubElement(r, MT('t')); t.text = s; t.set(X, 'preserve')
    return r

def mfrac(num_els, den_els):
    f = etree.Element(MT('f'))
    fp = etree.SubElement(f, MT('fPr')); etree.SubElement(fp, MT('type')).set(MT('val'), 'bar')
    nm = etree.SubElement(f, MT('num'))
    for e in num_els: nm.append(e if etree.iselement(e) else mr(str(e)))
    dn = etree.SubElement(f, MT('den'))
    for e in den_els: dn.append(e if etree.iselement(e) else mr(str(e)))
    return f

def msub(base, sub):
    s = etree.Element(MT('sSub')); e = etree.SubElement(s, MT('e')); e.append(mr(base))
    sb = etree.SubElement(s, MT('sub')); sb.append(mr(sub, False))
    return s

def msup(base, sup):
    s = etree.Element(MT('sSup')); e = etree.SubElement(s, MT('e')); e.append(mr(base))
    sp = etree.SubElement(s, MT('sup')); sp.append(mr(sup, False))
    return s

def msum(lo, hi, inner):
    s = etree.Element(MT('nary')); sp = etree.SubElement(s, MT('naryPr'))
    c = etree.SubElement(sp, MT('chr')); c.set(MT('val'), 'Σ')
    l = etree.SubElement(sp, MT('limLoc')); l.set(MT('val'), 'subSup')
    sb = etree.SubElement(s, MT('sub')); sb.append(mr(lo, False))
    sh = etree.SubElement(s, MT('sup')); sh.append(mr(hi, False))
    ee = etree.SubElement(s, MT('e'))
    for el in inner: ee.append(el if etree.iselement(el) else mr(str(el)))
    return s

def msqrt(inner):
    s = etree.Element(MT('rad')); sp = etree.SubElement(s, MT('radPr'))
    d = etree.SubElement(sp, MT('degHide')); d.set(MT('val'), '1')
    ee = etree.SubElement(s, MT('e'))
    for el in inner: ee.append(el if etree.iselement(el) else mr(str(el)))
    return s

def EQ(formula_elements, intro_text):
    """Insert a properly formatted equation: intro line → centered OMML equation → next line"""
    eq_counter[0] += 1
    num = eq_counter[0]
    # Intro line
    ip = doc.add_paragraph(); ip.paragraph_format.first_line_indent = Cm(0.74)
    ip.paragraph_format.line_spacing = 1.0
    ir = ip.add_run(intro_text); set_font(ir, '宋体', 'Times New Roman', Pt(12))
    # Build OMML paragraph
    omp = etree.Element(MT('oMathPara')); om = etree.SubElement(omp, MT('oMath'))
    for el in formula_elements: om.append(el)
    om.append(mr('    (%d)' % num, False))
    ep = doc.add_paragraph(); ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ep.paragraph_format.line_spacing = 1.0
    ep.paragraph_format.space_before = Pt(6); ep.paragraph_format.space_after = Pt(6)
    ep._element.append(omp)
    return ep

# ===== COVER =====
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before = Pt(60)
r = p.add_run('基于多模型融合与机理-数据混合驱动的\n自来水厂水质预测与风险评估研究')
r.bold = True; set_font(r, '黑体', 'Times New Roman', Pt(18))
doc.add_paragraph()
ct = doc.add_table(rows=2, cols=3); ct.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, rd in enumerate([
    ['选题','2026年第十六届APMCM\n亚太地区大学生数学建模竞赛\n（中文赛项）','参赛编号'],
    ['A','2026年第十六届APMCM\n亚太地区大学生数学建模竞赛\n（中文赛项）','apmcm******']]):
    for j, v in enumerate(rd):
        ct.rows[i].cells[j].text = ''
        pp = ct.rows[i].cells[j].paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = pp.add_run(v); set_font(rr, '宋体', 'Times New Roman', Pt(10))
doc.add_page_break()

# ===== ABSTRACT =====
C('摘  要', 14, True)
P(ABSTRACT)
p = doc.add_paragraph(); r = p.add_run('关键词：'+KEYWORDS); r.bold = True
set_font(r, '宋体', 'Times New Roman', Pt(12))
doc.add_page_break()
print("Abstract done")

# ===== S1 =====
H1('一、问题重述')
H2('1.1 问题背景')
for pa in S1_BG: P(pa)
H2('1.2 问题要求')
QR('问题一', Q1_REQ); QR('问题二', Q2_REQ); QR('问题三', Q3_REQ); QR('问题四', Q4_REQ)
print("S1 done")

# ===== S2 =====
H1('二、问题分析')
H2('2.1 问题一分析'); P(S2_A1)
H2('2.2 问题二分析'); P(S2_A2)
H2('2.3 问题三分析'); P(S2_A3)
H2('2.4 问题四分析'); P(S2_A4)
Img('flowchart_overall.png','图1  总体建模思路流程图', 5.5)
print("S2 done")

# ===== S3 =====
H1('三、模型假设')
for a in ASSUMPTIONS: P(a)
print("S3 done")

# ===== S4 =====
H1('四、符号说明')
T3('表1  符号说明表',
   ['符号','含义','单位'],
   [['R/W NTU','原水浊度','NTU'],['FILT. NTU','滤后水浊度','NTU'],['NTU','出厂水浊度','NTU'],
    ['R/W PH','原水pH值','—'],['ALUM','混凝剂投加量','mg/L'],
    ['R/W FLOW','原水流量','m3/h'],['T/W FLOW','出厂水流量','m3/h'],
    ['C/W WELL LEVEL','清水池水位','m'],['τ','时滞参数','步(1步=2h)'],
    ['N','CSTR串联级数','—'],['HRT','水力停留时间','h'],
    ['η','超标幅度','%'],['R2','决定系数','—'],['RMSE','均方根误差','NTU']])
P('注：未列出的符号在正文中说明。变量简写严格沿用题目附录定义。')
print("S4 done")

# ===== S5: Problem 1 =====
H1('五、问题一模型的建立与求解')
Img('flowchart_q1.png','图2  问题一建模流程图', 5.0)
H2('5.1 数据预处理'); P(P1_INTRO)
H2('5.2 特征筛选'); P(P1_FS1)

# EQ(1) Mutual Info
EQ([mr('I(X;Y)'), mr(' = '),
    msum('x,y','',[mr('p(x,y)'), mr(' log '), mfrac([mr('p(x,y)')],[mr('p(x)p(y)')])])],
   '互信息的数学表达式如下：')

Img('fig_p1_feature_importance_compare.png','图3  三种特征重要性方法对比', 5.5)
H2('5.3 预测模型'); P(P1_MODEL)
H2('5.4 模型验证'); P(P1_VAL)

# EQ(2) RMSE
EQ([mr('RMSE'), mr(' = '),
    msqrt([mfrac([msum('i=1','n',[mr('(y_i - ŷ_i)^2')])],[mr('n')])])],
   '均方根误差（RMSE）的计算公式如下：')

# EQ(3) R2
EQ([msup('R','2'), mr(' = 1 - '),
    mfrac([msum('i=1','n',[mr('(y_i - ŷ_i)^2')])],
          [msum('i=1','n',[mr('(y_i - ȳ)^2')])])],
   '决定系数（R2）的计算公式如下：')

T3('表2  三模型滚动验证结果对比',
   ['模型','平均RMSE','平均MAE','平均R2','平均MAPE(%)'],
   [['XGBoost','0.235','0.097','0.734','12.6'],
    ['随机森林','0.449','0.149','0.381','13.7'],
    ['线性回归','0.596','0.338','-0.194','66.8']])

H2('5.5 SHAP分析'); P(P1_SHAP)
Img('fig_p1_shap_beeswarm.png','图4  SHAP蜂群图', 5.5)
Img('fig_p1_shap_dependence.png','图5  SHAP依赖图', 5.5)
H2('5.6 预测结果'); P(P1_PRED)
print("S5 done")

# ===== S6: Problem 2 =====
H1('六、问题二模型的建立与求解')
Img('flowchart_q2.png','图6  问题二建模流程图', 5.0)
H2('6.1 平稳性检验'); P(P2_ADF)
H2('6.2 预白化与CCF时滞识别'); P(P2_PW)

# EQ(4) CCF
EQ([msub('CCF','xy'), mr('(τ) = '),
    mfrac([mr('E[(x_{t-τ} - μ_x)(y_t - μ_y)]')],[mr('σ_x σ_y')])],
   '交叉相关函数（CCF）的定义如下：')

Img('fig_p2_ccf_prewhitening.png','图7  预白化前后CCF对比', 5.5)
H2('6.3 滞后互信息'); P(P2_MI)
H2('6.4 时滞参数'); P(P2_LAG)
Img('fig_p2_bootstrap_lags.png','图8  Bootstrap时滞分布', 5.5)
H2('6.5 ARIMAX模型'); P(P2_ARIMAX)

# EQ(5) ARIMAX general
EQ([mr('φ(B)(1-B)^d y_t = Σ β_k x_k(t-τ_k) + θ(B) ε_t')],
   'ARIMAX模型的一般形式为：')

# EQ(6) ARIMAX specific
EQ([mr('FILT.NTU(t) = φ_1 FILT(t-1) + φ_2 FILT(t-2) + β_1 RW_NTU(t-3) + β_2 RW_FLOW(t-2) + ε_t + θ_1 ε_{t-1}')],
   '代入时滞参数后，本模型的具体表达式为：')

T3('表3  ARIMAX(2,0,1)参数估计',
   ['参数','估计值','标准误','z值','P>|z|'],
   [['AR(1)','0.010','0.004','2.34','0.019'],
    ['AR(2)','0.804','0.003','252.82','<0.001'],
    ['MA(1)','0.373','0.005','79.75','<0.001'],
    ['R/W NTU(lag3)','-0.001','0.000','-1.79','0.074'],
    ['R/W FLOW(lag2)','0.001','0.003','0.41','0.679']])
Img('fig_p2_arimax_forecast.png','图9  ARIMAX预测对比', 5.0)
Img('fig_p2_residual_diagnostics.png','图10  ARIMAX残差诊断', 5.0)
print("S6 done")

# ===== S7: Problem 3 =====
H1('七、问题三模型的建立与求解')
Img('flowchart_q3.png','图11  问题三建模流程图', 5.0)
H2('7.1 物理模型'); P(P3_PHYS)

# EQ(7) Mass conservation
EQ([mr('V dC_{out}/dt = Q_{in} C_{in} - Q_{out} C_{out}')],
   '以清水池为控制体，溶质质量守恒方程为：')

# EQ(8) RTD
EQ([mr('E(t) = (N/τ)^N t^{N-1} exp(-Nt/τ) / Γ(N)')],
   'n级串联CSTR的停留时间分布（RTD）密度函数为：')

# EQ(9) Convolution
EQ([msub('NTU','physical'), mr('(t) = ∫_0^∞ FILT.NTU(t-s) E(s) ds')],
   '机理层面的出水浊度为滤后浊度序列与RTD的卷积：')

H2('7.2 LSTM残差修正'); P(P3_LSTM)

# EQ(10) Hybrid
EQ([mr('NTU(t+h) = NTU_{physical}(t+h) + ΔNTU_{LSTM}(t+h)')],
   '混合模型的最终输出为两部分的叠加：')

H2('7.3 消融实验'); P(P3_ABLATION)
T3('表4  消融实验结果',['模型','RMSE','R2'],
   [['纯RTD机理','0.655','-2.53'],['纯LSTM数据驱动','0.603','-1.99'],['RTD+LSTM混合','0.650','-2.48']])
Img('fig_p3_ablation.png','图12  消融实验对比', 5.5)
H2('7.4 突变场景与敏感性'); P(P3_SURGE)

# EQ(11) Sensitivity coefficient
EQ([mr('S = Δy / Δx')],
   '敏感度系数的定义如下：')

Img('fig_p3_surge_scenario.png','图13  进水波动下模型预测对比', 5.5)
Img('fig_p3_sensitivity.png','图14  控制变量扰动法敏感度分析', 5.0)
H2('7.5 预测结果'); P(P3_PRED_OUT)
print("S7 done")

# ===== S8: Problem 4 =====
H1('八、问题四模型的建立与求解')
Img('flowchart_q4.png','图15  问题四建模流程图', 5.0)
H2('8.1 小时到日级聚合'); P(P4_AGG)

# EQ(12) Exceedance
EQ([msub('η','h'), mr(' = max(0, (NTU_h - 1) / 1) × 100%')],
   '超标幅度的计算方式为：')

H2('8.2 梯形隶属度模糊评价'); P(P4_FUZZY)

# EQ(13) Trapezoid
EQ([msub('μ','A'), mr('(x) = { 0, x≤a or x≥d; (x-a)/(b-a), a<x<b; 1, b≤x≤c; (d-x)/(d-c), c<x<d }')],
   '梯形隶属度函数为分段函数，形式如下：')

# EQ(14) Combined weight
EQ([mr('w = λ w_{AHP} + (1-λ) w_{Entropy}')],
   '组合赋权的计算方式为：')

Img('fig_p4_membership.png','图16  梯形隶属度函数', 5.5)
H2('8.3 评价结果'); P(P4_RESULTS)
T3('表5  2026年1-3月风险等级分布',['风险等级','天数','占比'],
   [['安全','86','95.6%'],['低风险','1','1.1%'],['中风险','1','1.1%'],['高风险(一票否决)','2','2.2%']])
Img('fig_p4_risk_pie.png','图17  风险等级饼图', 4.0)
Img('fig_p4_risk_timeline.png','图18  日风险等级时间线', 5.5)
H2('8.4 转移矩阵与风险归因'); P(P4_MARKOV)
Img('fig_p4_markov.png','图19  马尔可夫转移概率矩阵', 4.5)
print("S8 done")

# ===== S9 =====
H1('九、模型的分析与检验')
H2('9.1 问题一模型检验'); P(V1)
Img('fig_ch9_p1_sensitivity.png','图20  RF参数灵敏度', 5.5)
H2('9.2 问题二模型检验'); P(V2)
Img('fig_ch9_p2_lag_sensitivity.png','图21  时滞参数灵敏度', 4.5)
Img('fig_ch9_p2_residual_normality.png','图22  残差正态性诊断', 5.0)
H2('9.3 问题三模型检验'); P(V3)
Img('fig_ch9_p3_rtd_sensitivity.png','图23  RTD参数灵敏度', 5.5)
H2('9.4 问题四模型检验'); P(V4)
Img('fig_ch9_p4_threshold_sensitivity.png','图24  隶属度阈值灵敏度', 5.0)
print("S9 done")

# ===== S10 =====
H1('十、模型评价、改进与推广')
H2('10.1 模型优点')
for p in PROS: P(p)
H2('10.2 模型缺点')
for c in CONS: P(c)
H2('10.3 模型改进')
for i in IMPROVE: P(i)
H2('10.4 模型推广'); P(EXTEND)
print("S10 done")

# ===== REFERENCES =====
H1('参考文献')
refs = [
    '[1] Kwarko-Kyei E, Tornyeviadzi P, Seidu R. A Machine Learning Approach to Predicting the Turbidity from Filters in a Water Treatment Plant[J]. Water, 2025, 17(20): 2938.',
    '[2] Karami H, et al. A hybrid framework of feature selection and interpretability for dissolved oxygen prediction in drinking water treatment plants[J]. Scientific Reports, 2026, 16: 6912.',
    '[3] Verhaeghe L, et al. Towards good modelling practice for parallel hybrid models for wastewater treatment processes[J]. Water Science and Technology, 2024, 89(11): 2971-2990.',
    '[4] Zhu J, et al. An enhanced combined model for water quality prediction utilizing spatiotemporal features and physical-informed constraints[J]. Expert Systems with Applications, 2025: 126937.',
    '[5] Box G E P, et al. Time Series Analysis: Forecasting and Control (5th ed.)[M]. Wiley, 2015.',
    '[6] Lundberg S M, Lee S I. A unified approach to interpreting model predictions[C]. NeurIPS, 2017.',
    '[7] Chen T, Guestrin C. XGBoost: A scalable tree boosting system[C]. ACM SIGKDD, 2016.',
    '[8] Mu Z, et al. Physics-guided transformer-based modeling for surface water quality prediction[J]. Sustainable Computing, 2025: 100466.',
    '[9] Cao X, et al. Fuzzy comprehensive evaluation for water quality early warning[J]. Water Supply, 2022, 22(12).',
]
for r in refs:
    p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.0
    rr = p.add_run(r); set_font(rr, '宋体', 'Times New Roman', Pt(10))

# ===== APPENDIX =====
H1('附录')
H2('附录1：核心代码说明')
T3('表6  核心代码文件',['文件名','功能'],
   [['01_data_preprocessing.py','数据读取、列名标准化、异常值处理、特征构造'],
    ['02_problem1_feature_prediction.py','四层筛选、三模型训练、Walk-Forward验证、SHAP分析'],
    ['03_problem2_timelag_model.py','ADF检验、预白化CCF、滞后MI、ARIMAX、格兰杰因果'],
    ['04_problem3_hybrid_model.py','质量守恒RTD、BiLSTM残差修正、消融、敏感度'],
    ['05_problem4_risk_assessment.py','梯形隶属度模糊评价、熵权AHP、一票否决、马尔可夫'],
    ['06_chapter9_validation.py','各模型参数灵敏度、残差诊断、交叉验证']])
H2('附录2：Excel文件清单')
T3('表7  附件Excel',['文件名','内容'],
   [['problem1_predictions.xlsx','问题一 三天预测值(36行)'],
    ['problem3_predictions_feb.xlsx','问题三 三天7-19时预测(21行)'],
    ['problem4_risk_assessment.xlsx','问题四 90天逐日风险等级'],
    ['problem4_march_detail.xlsx','问题四 3月份每日分类(31行)']])
H2('附录3：图表说明')
P('全文共25组图表(含PDF矢量图与PNG位图)。其中：流程图5张、问题一至四分析图16张、模型检验图4张。')

output = os.path.join(BASE, '论文_APMCM2026_A题.docx')
doc.save(output)
print(f'\nSaved: {output} | Equations: {eq_counter[0]}')
