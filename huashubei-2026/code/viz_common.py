# -*- coding: utf-8 -*-
"""
华数杯 matplotlib 中文适配 + 绘图模板
=====================================
用途：
  1. 一键解决中文白框（□）问题——原因是 matplotlib 默认字体不含中文字形；
  2. 西文 Times New Roman + 中文黑体/雅黑 混排，数学字体 stix；
  3. 统一高清导出：PNG 300dpi + PDF 矢量；
  4. 常用图表模板：折线、柱状、热力、箱线、直方+KDE、QQ图、ROC、收敛曲线。

用法：
  import chinese_font_setup  # 或直接复制 setup_chinese_font() 到你的脚本开头
  setup_chinese_font()
  fig, ax = plt.subplots()
  ...
  save_fig(fig, "fig01_demo.png")

适配原理：
  中文白框 = matplotlib 找不到中文字体，回退到默认字体（DejaVu Sans 无中文）。
  解决 = 把系统字体（SimHei/微软雅黑）注册进 matplotlib 字体管理器，并设置
         plt.rcParams['font.sans-serif']；同时关闭 unicode 负号（axes.unicode_minus=False），
         否则负号会显示成方框。
"""

import os
import platform
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager


def setup_chinese_font(prefer: str = "auto") -> str:
    """
    注册并启用中文字体，返回实际生效的中文字体名。

    prefer:
      "auto"   -> 按优先级自动选择：微软雅黑 > 黑体 > 宋体 > 楷体
      "SimHei" / "Microsoft YaHei" / "SimSun" / "KaiTi" -> 指定字体名
    """
    # 常见中文字体文件（Windows），按优先级排列
    candidates = [
        ("Microsoft YaHei", r"C:\Windows\Fonts\msyh.ttc"),
        ("Microsoft YaHei UI", r"C:\Windows\Fonts\msyh.ttc"),
        ("SimHei",            r"C:\Windows\Fonts\simhei.ttf"),
        ("SimSun",            r"C:\Windows\Fonts\simsun.ttc"),
        ("KaiTi",             r"C:\Windows\Fonts\simkai.ttf"),
        ("DengXian",          r"C:\Windows\Fonts\Deng.ttf"),
    ]

    # 1) 先把已安装的字体文件注册进 matplotlib（解决某些环境字体找不到的问题）
    for name, path in candidates:
        if os.path.exists(path):
            try:
                font_manager.fontManager.addfont(path)
            except Exception:
                pass

    # 2) 确定最终中文字体名
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = None
    if prefer != "auto":
        if prefer in available:
            chosen = prefer
        else:
            print(f"[font] 未找到指定字体 {prefer}，使用自动选择。")
    if chosen is None:
        for name, _ in candidates:
            if name in available:
                chosen = name
                break
    if chosen is None:
        # 兜底：把所有已注册字体里名称含中文字符的列出来，方便排查
        cn_fonts = [f.name for f in font_manager.fontManager.ttflist
                    if any('\u4e00' <= ch <= '\u9fff' for ch in f.name)]
        print("[font] 未找到常用中文字体！可用候选：", cn_fonts[:10])
        raise RuntimeError("没有可用中文字体，请安装 微软雅黑/黑体 或改用系统字体。")

    # 3) 全局 rcParams：
    #    - 中文字体必须放在最前。实测 matplotlib 3.10 在 sans-serif 列表中
    #      Times New Roman 优先时不会回退到中文字体，中文会渲染成白框。
    #    - 中文优先时，中文用雅黑/黑体、西文由该字体自带拉丁字形承担，可正常显示。
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [chosen, "Times New Roman"]

    plt.rcParams["axes.unicode_minus"] = False          # 负号正常显示（关键！）
    plt.rcParams["mathtext.fontset"] = "stix"           # 公式字体（与 Times 协调）
    plt.rcParams["font.size"] = 10.5
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["xtick.major.width"] = 0.6
    plt.rcParams["ytick.major.width"] = 0.6
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 300
    plt.rcParams["savefig.bbox"] = "tight"

    print(f"[font] 中文适配完成：{chosen} (matplotlib {matplotlib.__version__})")
    return chosen


def save_fig(fig, stem: str, folder: str = ".", dpi: int = 300):
    """统一保存：PNG 300dpi + PDF 矢量，文件名自动补编号前缀规则见交付规范。"""
    os.makedirs(folder, exist_ok=True)
    png = os.path.join(folder, f"{stem}.png")
    pdf = os.path.join(folder, f"{stem}.pdf")
    fig.savefig(png, dpi=dpi)
    fig.savefig(pdf)
    print(f"[fig] 已保存 {png} / {pdf}")
    return png


def style_ax(ax, xlabel="", ylabel="", title="", legend=True):
    """统一坐标轴样式：轴标签带单位、网格半透明、图例。"""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.35)
    if legend:
        ax.legend(frameon=False)
    return ax


# ---------------------------------------------------------------- 图表模板 ----

def template_line(x, y_list, labels, xlabel, ylabel, title, colors=None):
    """折线图：预测对比/时间序列/收敛曲线通用。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, y in enumerate(y_list):
        ax.plot(x, y, lw=1.6, label=labels[i],
                color=colors[i] if colors else None)
    style_ax(ax, xlabel, ylabel, title)
    return fig


def template_bar(categories, values, xlabel, ylabel, title, values_text=True):
    """柱状图：特征重要性/分类对比。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(categories, values, color="#4472C4", edgecolor="black", lw=0.5)
    if values_text:
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.3f}",
                    ha="center", va="bottom", fontsize=8)
    style_ax(ax, xlabel, ylabel, title, legend=False)
    return fig


def template_heatmap(df, title="相关系数热力图", cmap="RdBu_r", annot=True):
    """相关性/权重热力图：输入 pandas DataFrame。"""
    import numpy as np
    fig, ax = plt.subplots(figsize=(max(6, df.shape[1] * 0.75),
                                    max(5, df.shape[0] * 0.6)))
    im = ax.imshow(df.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(df.shape[1]), df.columns, rotation=45, ha="right")
    ax.set_yticks(range(df.shape[0]), df.index)
    if annot:
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                ax.text(j, i, f"{df.values[i, j]:.2f}", ha="center", va="center",
                        fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    return fig


def template_boxplot(data_list, labels, ylabel, title):
    """箱线图：异常值检测/组间分布对比。"""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot(data_list, tick_labels=labels, patch_artist=True,
               boxprops=dict(facecolor="#BDD7EE"))
    style_ax(ax, "", ylabel, title, legend=False)
    return fig


def template_hist_kde(data, xlabel, title, bins=40):
    """直方图+核密度：数据分布/预测结果分布。"""
    import numpy as np
    from scipy import stats
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(data, bins=bins, density=True, alpha=0.55, color="#8FAADC",
            edgecolor="black", lw=0.4, label="直方图")
    xs = np.linspace(min(data), max(data), 300)
    kde = stats.gaussian_kde(data)(xs)
    ax.plot(xs, kde, color="#C00000", lw=1.8, label="KDE")
    style_ax(ax, xlabel, "概率密度", title)
    return fig


def template_qq(data, title="正态性检验 QQ 图"):
    """QQ 图：配合 JB/Shapiro 检验使用。"""
    from scipy import stats
    fig, ax = plt.subplots(figsize=(6, 5))
    stats.probplot(data, dist="norm", plot=ax)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.35)
    return fig


def template_roc(fpr_list, tpr_list, auc_list, labels, title="ROC 曲线对比"):
    """ROC 曲线：分类模型对比（fpr/tpr/auc 各为 list）。"""
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    for fpr, tpr, auc_v, lab in zip(fpr_list, tpr_list, auc_list, labels):
        ax.plot(fpr, tpr, lw=1.8, label=f"{lab} (AUC={auc_v:.3f})")
    ax.plot([0, 1], [0, 1], ls="--", color="gray", lw=1)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.05)
    style_ax(ax, "假阳性率 (FPR)", "真阳性率 (TPR)", title)
    return fig


def template_convergence(iterations, values, label="目标函数值", title="算法收敛曲线"):
    """收敛曲线：GA/PSO/SA 求解过程。"""
    return template_line(iterations, [values], [label],
                         "迭代次数", "目标函数值", title)


def df_to_markdown_table(df, caption="", note=""):
    """DataFrame -> 三线表 Markdown（写作手直接粘贴）。"""
    lines = []
    if caption:
        lines.append(f"**表 {caption}**\n")
    header = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join([":---:"] * len(df.columns)) + "|"
    lines += [header, sep]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(f"{v:.4f}" if isinstance(v, float) else str(v)
                                       for v in row.values) + " |")
    if note:
        lines.append(f"\n*注：{note}*")
    return "\n".join(lines)


if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    setup_chinese_font()

    # 自检：画一张带中文、负号、公式的示例图
    x = np.linspace(0, 10, 100)
    y = np.sin(x) * np.exp(-x / 8) - 0.2
    fig = template_line(x, [y], ["示例曲线 y = sin(x)·e^(-x/8) - 0.2"],
                        "时间 t (h)", "数值", "中文适配自检：标题与负号应正常显示")
    save_fig(fig, "fig00_font_check", folder=".")

    # 自检：三线表输出
    demo = pd.DataFrame({"模型": ["线性回归", "XGBoost", "CatBoost"],
                         "RMSE": [0.4210, 0.2130, 0.1975],
                         "R²": [0.6123, 0.9041, 0.9172]})
    print(df_to_markdown_table(demo, caption="N 模型性能对比",
                               note="测试集结果，最优值加粗。"))
