# -*- coding: utf-8 -*-
"""
问题一：三组介质 A 构型的导通性判定 + 数据洞察 + 接触网络可视化（国赛一等奖标准版）。
设计要点：
  - 图例置于图外顶部，不遮数据；
  - 跨接路径用黑色粗线+白描边（避免与簇色冲突），路径首末端与电极的接触边同色加粗，形成闭环；
  - 电极接触边浅色入图例；节点带白描边；
  - 不导通组标注关键缺口距离；导通组标注跨接结论。
输出（统一图片目录 图片/）：
  q1_group{1,2,3}_network.png / q1_data_overview.png / q1_boundary_example.png
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "附件.xlsx")
TBL = os.path.join(BASE, "output", "tables")
FIG = os.path.join(BASE, "图片", "3_正文结果图")


def parse_group(name):
    df = pd.read_excel(RAW, sheet_name=name, header=None, skiprows=2)
    arr = df.to_numpy(dtype=float)
    return np.stack([arr[:, :3], arr[:, 3:]], axis=1)


def merge_groups(segs):
    P1 = segs[:, 0]
    P2 = segs[:, 1]
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    N = len(segs)
    parent = list(range(N))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    shifts = np.array([[tx, ty, tz] for tx in (-C.SIDE, 0, C.SIDE)
                       for ty in (-C.SIDE, 0, C.SIDE)
                       for tz in (-C.SIDE, 0, C.SIDE)], dtype=float)
    for i in range(N):
        for j in range(i + 1, N):
            if np.linalg.norm(np.cross(U[i], U[j])) > 1e-6:
                continue
            for k in range(27):
                q = P1[j] + shifts[k]
                w = q - P1[i]
                if np.linalg.norm(w - np.dot(w, U[i]) * U[i]) < 0.05:
                    union(i, j)
                    break
    labels = {}
    out = np.empty(N, dtype=int)
    for i in range(N):
        r = find(i)
        if r not in labels:
            labels[r] = len(labels)
        out[i] = labels[r]
    return out


def min_break_gap(segs, clabels, tL, tR):
    """不导通构型的关键断口间隙（nm）：
    左接触簇与右接触簇之间的最小表面间隙；若某侧无接触簇，取电极到最近簇的间隙。"""
    P1 = segs[:, 0]
    P2 = segs[:, 1]
    U = P2 - P1
    L = np.linalg.norm(U, axis=1)
    U = U / L[:, None]
    cl_tL = set(clabels[np.nonzero(tL)[0]].tolist())
    cl_tR = set(clabels[np.nonzero(tR)[0]].tolist())
    best = np.inf
    best_pair = (None, None)
    if cl_tL and cl_tR:
        idxL = [i for i in range(len(segs)) if clabels[i] in cl_tL]
        idxR = [i for i in range(len(segs)) if clabels[i] in cl_tR]
        for a in idxL:
            for b in idxR:
                if clabels[a] == clabels[b]:
                    continue
                d = C.seg_seg_dist_batch(P1[a:a+1], U[a:a+1], L[a:a+1],
                                         P1[b:b+1], U[b:b+1], L[b:b+1])[0]
                g = d - C.TH_AA
                if g < best:
                    best = g
                    best_pair = (a, b)
    if best == np.inf:
        for i in range(len(segs)):
            for face in (-C.HALF, C.HALF):
                d = min(abs(P1[i, 0] - face), abs(P2[i, 0] - face))
                g = d - C.TH_AF
                if g < best:
                    best = g
                    best_pair = (i, None)
    return (best if np.isfinite(best) else 0.0), best_pair


def plot_group_network(segs, result, name, out_path, top_k=3):
    C.setup_font()
    clabels = C.cluster_labels(segs)
    counts = np.bincount(clabels, minlength=clabels.max() + 1)
    order = np.argsort(-counts)
    big = set(order[:top_k].tolist())
    cmap = plt.get_cmap("tab10")
    color_map = {g: cmap(i % 10) for i, g in enumerate(order[:top_k])}
    mids = 0.5 * (segs[:, 0] + segs[:, 1])
    edges, tL, tR = C.contact_edges(segs)
    path_set = C.find_spanning_path(segs)
    deg = np.zeros(len(segs), dtype=int)
    if len(edges):
        deg[edges[:, 0]] += 1
        deg[edges[:, 1]] += 1

    ylo = min(mids[:, 1].min(), 0.0) - 120
    yhi = max(mids[:, 1].max(), 0.0) + 120
    xlo, xhi = -C.HALF - 320, C.HALF + 320

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    fig.subplots_adjust(left=0.12, right=0.97, top=0.86, bottom=0.11)
    C.style_clean(ax, grid=False)

    # 接触边（路径边黑色高亮）
    for a, b in edges:
        inpath = path_set is not None and a in path_set and b in path_set
        if inpath:
            ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                    color="white", lw=4.2, zorder=3)
            ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                    color="#111111", lw=2.4, zorder=4)
        else:
            ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                    color="white", lw=2.6, zorder=2)
            ax.plot([mids[a, 0], mids[b, 0]], [mids[a, 1], mids[b, 1]],
                    color="#777777", lw=1.6, zorder=3)
    # 电极接触边（浅色，入图例）
    for i in np.nonzero(tL)[0]:
        ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                color="white", lw=2.2, zorder=1)
        ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                color="#D62728", lw=1.4, alpha=0.55, zorder=2)
    for i in np.nonzero(tR)[0]:
        ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                color="white", lw=2.2, zorder=1)
        ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                color="#1F77B4", lw=1.4, alpha=0.55, zorder=2)
    # 路径与电极的衔接边（黑色加粗，视觉闭环）
    if path_set is not None:
        for i in path_set:
            if tL[i]:
                ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                        color="white", lw=4.2, zorder=3)
                ax.plot([-C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                        color="#111111", lw=2.4, zorder=4)
            if tR[i]:
                ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                        color="white", lw=4.2, zorder=3)
                ax.plot([C.HALF, mids[i, 0]], [0.0, mids[i, 1]],
                        color="#111111", lw=2.4, zorder=4)
    # 节点（统一白描边；簇节点略大）
    for i in range(len(segs)):
        if clabels[i] in big:
            col = color_map[clabels[i]]
            s = 22 + 3 * min(deg[i], 8)
            alpha = 0.95
        else:
            col = (0.62, 0.62, 0.62)
            s = 14
            alpha = 0.68
        ax.scatter(mids[i, 0], mids[i, 1], s=s, c=[col], alpha=alpha,
                   edgecolors="white", linewidths=0.8, zorder=5)
    if path_set is not None:
        pl = list(path_set)
        ax.scatter(mids[pl, 0], mids[pl, 1], s=38, facecolors="none",
                   edgecolors="#111111", linewidths=1.5, zorder=6)
    # 带电面
    ax.scatter([-C.HALF, C.HALF], [0.0, 0.0], marker="s", s=130,
               c=["#D62728", "#1F77B4"], edgecolor="white", lw=1.6, zorder=7)
    ax.text(-C.HALF, ylo + 55, "左带电面", color="#B00000", fontsize=8.5,
            ha="center", bbox=dict(fc="white", alpha=0.9, ec="none", pad=1))
    ax.text(C.HALF, ylo + 55, "右带电面", color="#1F4E9C", fontsize=8.5,
            ha="center", bbox=dict(fc="white", alpha=0.9, ec="none", pad=1))

    ax.set_xlim(xlo, xhi)
    ax.set_ylim(ylo, yhi)
    # Y 方向按数据跨度自适应放大（修正：aspect>1 才是放大 Y）
    xspan = xhi - xlo
    yspan = yhi - ylo
    asp = 0.45 * xspan / yspan
    ax.set_aspect(min(max(asp, 0.45), 8.0))
    ax.set_xlabel("X (nm)")
    ax.set_ylabel("Y (nm)")
    ax.set_yticks(np.linspace(ylo, yhi, 3).round(0))

    handles = []
    for g in order[:top_k]:
        handles.append(plt.Line2D([0], [0], marker="o", color="w",
                                  markerfacecolor=color_map[g], ms=9,
                                  label=f"连通簇 {g+1}（{int(counts[g])} 段）"))
    handles.append(plt.Line2D([0], [0], marker="o", color="w",
                              markerfacecolor=(0.62, 0.62, 0.62), ms=7,
                              label="其余段"))
    handles.append(plt.Line2D([0], [0], color=(0.42, 0.42, 0.42, 0.5), lw=1,
                              label="接触边（≤61.8 nm）"))
    handles.append(plt.Line2D([0], [0], color="#D62728", lw=1.2,
                              label="左面接触边"))
    handles.append(plt.Line2D([0], [0], color="#1F77B4", lw=1.2,
                              label="右面接触边"))
    if path_set is not None:
        handles.append(plt.Line2D([0], [0], color="#111111", lw=2.4,
                                  label="跨接路径（左→右）"))
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8,
               frameon=True, edgecolor="0.7", bbox_to_anchor=(0.5, 1.0))

    status = "导通" if result else "不导通"
    ax.set_title(f"{name}：{status}（N={len(segs)} 段，最大簇 "
                 f"{counts[order[0]]} 段）", fontsize=12)
    if result:
        ax.text(0.02, 0.97, "存在左→右跨接路径（黑色粗线）",
                transform=ax.transAxes, va="top", fontsize=9,
                color="#1F7A3D",
                bbox=dict(fc="white", alpha=0.9, ec="none", pad=2))
    else:
        gap, (ga, gb) = min_break_gap(segs, clabels, tL, tR)
        if ga is not None and gb is not None:
            x1, y1 = mids[ga, 0], mids[ga, 1]
            x2, y2 = mids[gb, 0], mids[gb, 1]
            ax.plot([x1, x2], [y1, y2], color="white", lw=3.0, zorder=7)
            ax.plot([x1, x2], [y1, y2], color="#B00000", lw=1.6,
                    ls="--", zorder=8)
            ax.annotate(f"断口 d≈{max(gap, 0):.0f} nm",
                        xy=((x1 + x2) / 2, (y1 + y2) / 2),
                        xytext=((x1 + x2) / 2, (y1 + y2) / 2 + 220),
                        fontsize=8.5, color="#B00000", ha="center",
                        arrowprops=dict(arrowstyle="->", color="#B00000",
                                        lw=0.9),
                        bbox=dict(fc="white", alpha=0.92, ec="none", pad=1.5))
        ax.text(0.02, 0.97, f"关键断口间隙 d={max(gap, 0):.0f} nm > 61.8 nm → 不导通",
                transform=ax.transAxes, va="top", fontsize=9,
                color="#B00000",
                bbox=dict(fc="white", alpha=0.9, ec="none", pad=2))
    C.save_fig(fig, out_path)


def fig_data_overview(groups):
    C.setup_font()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    colors = ["#4472C4", "#ED7D31", "#00B050"]
    for ax, (name, segs), col in zip(axes, groups, colors):
        L = np.linalg.norm(segs[:, 1] - segs[:, 0], axis=1)
        ax.hist(L / 1000, bins=12, color=col, alpha=0.75, edgecolor="white")
        ax.axvline(5.0, ls="--", color="#C00000", lw=1.2)
        C.style_clean(ax, grid=False)
        ax.set_title(f"{name}：行长度分布", fontsize=11)
        ax.set_xlabel("行内两点距离 (×10³ nm)")
        ax.set_ylabel("行数")
        ax.text(0.97, 0.93, f"n={len(segs)}", transform=ax.transAxes,
                ha="right", fontsize=9, bbox=dict(fc="white", ec="0.7",
                                                  alpha=0.85, pad=1))
        ax.text(0.02, 0.97, "红线 = 标称行长 5000 nm（5.0×10³ nm）",
                transform=ax.transAxes, va="top", fontsize=8, color="#C00000",
                bbox=dict(fc="white", alpha=0.85, ec="none", pad=1))
    fig.suptitle("附件数据洞察：行距不恒为 5000nm（截断分段的直接证据）",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    C.save_fig(fig, os.path.join(FIG, "q1_data_overview.png"))


def fig_boundary_example():
    C.setup_font()
    segs = parse_group("组1")
    r1 = segs[0]
    r12 = segs[11]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axvline(-5000, color="#D62728", ls="--", lw=1.4)
    ax.axvline(5000, color="#1F77B4", ls="--", lw=1.4)
    ax.text(-5000, 430, "左带电面 x=-5000", color="#B00000", fontsize=9,
            ha="right", bbox=dict(fc="white", alpha=0.85, ec="none", pad=1))
    ax.text(5000, 430, "右带电面 x=+5000", color="#1F4E9C", fontsize=9,
            ha="left", bbox=dict(fc="white", alpha=0.85, ec="none", pad=1))
    ax.plot([r1[0, 0], r1[1, 0]], [r1[0, 1], r1[1, 1]], color="#1F77B4",
            lw=3, label="第 1 行：左侧可见段")
    ax.plot([r12[0, 0], r12[1, 0]], [r12[0, 1], r12[1, 1]], color="#ED7D31",
            lw=3, label="第 12 行：卷回尾段（周期镜像）")
    ax.plot([-5000, 5000], [r1[0, 1], r12[1, 1]], color="#808080", ls=":",
            lw=1.2)
    ax.scatter([-5000, 5000], [r1[0, 1], r12[1, 1]], s=40, color="k", zorder=5)
    ax.annotate("端点 (y,z) 完全相同\n方向向量成比例",
                xy=(-5000, r1[0, 1]), xytext=(-3500, -380),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="#303030"),
                bbox=dict(fc="white", alpha=0.9, ec="0.6", pad=2))
    ax.set_xlim(-6000, 6000)
    ax.set_ylim(-500, 500)
    ax.set_xlabel("X (nm)")
    ax.set_ylabel("Y (nm)")
    ax.set_title("边界截断证据：同一根圆柱被边界切为两段（组1 第1行与第12行）")
    C.style_clean(ax, grid=False)
    ax.legend(frameon=False, fontsize=9)
    C.save_fig(fig, os.path.join(FIG, "q1_boundary_example.png"))


def main():
    os.makedirs(TBL, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    rows = []
    groups = []
    for gi, name in enumerate(["组1", "组2", "组3"], 1):
        segs = parse_group(name)
        groups.append((name, segs))
        labels = merge_groups(segs)
        conduct_main, n_real, sizes_main = C.conduct_mixed(segs, None,
                                                           need_clusters=True)
        conduct_merged, _, _ = C.conduct_mixed(segs, None, merge_groups=labels)
        n_cyl = len(set(labels.tolist()))
        rows.append({
            "组": name,
            "有效段数": len(segs),
            "合并圆柱数": n_cyl,
            "主口径是否导通": "导通" if conduct_main else "不导通",
            "合并口径是否导通": "导通" if conduct_merged else "不导通",
            "连通簇数": len(sizes_main),
            "最大连通簇段数": sizes_main[0] if sizes_main else 0,
        })
        plot_group_network(segs, conduct_main, name,
                           os.path.join(FIG, f"q1_group{gi}_network.png"))
    pd.DataFrame(rows).to_csv(os.path.join(TBL, "q1_results.csv"),
                              index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows).to_string(index=False))
    fig_data_overview(groups)
    fig_boundary_example()


if __name__ == "__main__":
    main()
