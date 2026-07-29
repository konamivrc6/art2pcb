"""
众数滤波 — 对量化后的 01/01.png 做众数滤波，去除细线杂质。

用法:
    python 工具：众数滤波.py                  # 默认处理 01/01.png
    python 工具：众数滤波.py myimage.png      # 拖放或指定文件

原理:
    对每个像素，用 K×K 邻域内出现次数最多的颜色替换它。
    细线（1-3px）会被周围的主导颜色"投票投掉"，且不会产生新的中间色。

交互操作:
    鼠标左键点击  — 放置矩形选区顶点（点两个对角顶点）
    鼠标右键      — 取消当前选区
    鼠标移动      — 实时预览选区矩形
    A             — 选区设为全图
    0-9           — 输入窗口大小（如 5 = 5×5）
    Enter         — 执行众数滤波
    Tab           — 切换 HUD 显示/隐藏
    R             — 撤销滤波，回到原始图像
    S             — 保存图像（覆盖原文件）
    Esc           — 退出
"""

import os
import sys
import json
import cv2
import numpy as np


def hex_to_BGR(hex_color):
    """ '#RRGGBB' → BGR numpy array """
    hex_color = hex_color.lstrip('#')
    return np.array([int(hex_color[i:i + 2], 16) for i in (4, 2, 0)])


def _mode_filter_core(image, color_dict, kernel_size):
    """
    众数滤波核心：对整张图做 K×K 窗口众数滤波（BORDER_REPLICATE 处理边缘）。

    image:      量化后的 BGR 图像
    color_dict: {name: BGR array}
    kernel_size: 窗口边长（奇数，如 5）
    """
    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("kernel_size 必须为 ≥3 的奇数")

    h, w = image.shape[:2]
    if h < kernel_size or w < kernel_size:
        return image  # 太小，跳过

    color_names = list(color_dict.keys())
    color_bgrs = [color_dict[name] for name in color_names]

    # 每种颜色做二值掩膜 → box filter 统计邻域计数
    counts_stack = []
    for name in color_names:
        bgr = color_dict[name]
        mask = np.all(image == bgr.reshape(1, 1, 3), axis=2).astype(np.float32)
        kernel = np.ones((kernel_size, kernel_size), dtype=np.float32)
        count = cv2.filter2D(mask, -1, kernel, borderType=cv2.BORDER_REPLICATE)
        counts_stack.append(count)

    # (num_colors, h, w) → argmax → (h, w) 索引图
    counts_stack = np.stack(counts_stack, axis=0)
    best_idx = np.argmax(counts_stack, axis=0)

    # 重建图像
    result = np.zeros_like(image)
    for i in range(len(color_names)):
        result[best_idx == i] = color_bgrs[i]

    return result


def mode_filter(image, color_dict, kernel_size, roi=None):
    """
    众数滤波：用 K×K 窗口内出现次数最多的颜色替换每个像素。

    image:      量化后的 BGR 图像
    color_dict: {name: BGR array}
    kernel_size: 窗口边长（奇数，如 5）
    roi:        可选，(x1, y1, x2, y2)，均为 0.0~1.0 的相对坐标。
                指定时仅滤波该矩形区域；区域边界像素会依赖外部像素，
                结果等价于全图滤波后裁出该区域。
    """
    h, w = image.shape[:2]

    if roi is None:
        return _mode_filter_core(image, color_dict, kernel_size)

    x1, y1, x2, y2 = roi
    # 相对坐标 → 像素坐标
    px1 = max(0, int(round(x1 * w)))
    py1 = max(0, int(round(y1 * h)))
    px2 = min(w, int(round(x2 * w)))
    py2 = min(h, int(round(y2 * h)))

    # 确保选区有效
    if px1 >= px2 or py1 >= py2:
        raise ValueError(f"无效 ROI: ({x1},{y1})-({x2},{y2}) → 像素 ({px1},{py1})-({px2},{py2})")

    # 扩展提取区域，使边界像素的邻域窗口能覆盖原图外部像素
    radius = kernel_size // 2
    ex1 = max(0, px1 - radius)
    ey1 = max(0, py1 - radius)
    ex2 = min(w, px2 + radius)
    ey2 = min(h, py2 + radius)

    expanded = image[ey1:ey2, ex1:ex2]
    filtered_expanded = _mode_filter_core(expanded, color_dict, kernel_size)

    # 从扩展结果中裁出原始 ROI 区域
    roi_h = py2 - py1
    roi_w = px2 - px1
    crop_y1 = py1 - ey1
    crop_x1 = px1 - ex1
    filtered_roi = filtered_expanded[crop_y1:crop_y1 + roi_h, crop_x1:crop_x1 + roi_w]

    # 贴回原图
    result = image.copy()
    result[py1:py2, px1:px2] = filtered_roi
    return result


def load_palette(path="./01/palette.json"):
    """读取调色板 JSON，返回 {name: BGR array}。"""
    with open(path, "r", encoding="utf-8") as f:
        hexColors = json.load(f)
    return {name: hex_to_BGR(value) for name, value in hexColors.items()}


# ── GUI 常量 ──────────────────────────────────────────────────────────────
WIN_NAME = "Mode Filter"
DISP_MAX_W = 1200
DISP_MAX_H = 800
OVERLAY_ALPHA = 0.35       # 选区矩形半透明度
OVERLAY_COLOR = (0, 255, 255)  # 黄色预览框
OVERLAY_DONE = (0, 255, 0)     # 绿色已确认选区
HINT_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _draw_hud(disp, scale, pts, kernel_str, status_text, has_filtered):
    """在显示图上叠加 HUD 文字。"""
    hints = [
        "[Click] ROI   [A] Full   [RClick] Clear",
        "[0-9] Size   [Enter] Apply   [Tab] HUD",
        "[R] UndoAll   [Z] Undo   [S] Save   [Esc] Quit",
    ]
    lines = hints + [""]

    if pts:
        lines.append(f"Selection: {pts[0]} -> {pts[1]}" if len(pts) == 2
                      else f"P1: {pts[0]}")
    if kernel_str:
        lines.append(f"Window size: {kernel_str}")
    lines.append(status_text)

    (_, text_h), baseline = cv2.getTextSize("X", HINT_FONT, 0.5, 1)
    line_h = text_h + baseline + 6
    y = line_h
    for line in lines:
        cv2.putText(disp, line, (11, y + 1), HINT_FONT, 0.5, (0, 0, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(disp, line, (10, y), HINT_FONT, 0.5, (255, 255, 255), 1,
                    cv2.LINE_AA)
        y += line_h


def main():
    # --- 确定输入文件 ---
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = "./01/01.png"

    if not os.path.isfile(input_path):
        print(f"[错误] 找不到图片文件: {input_path}")
        return

    print(f"输入文件: {os.path.basename(input_path)}")

    # --- 读取调色板 ---
    palette_dir = os.path.join(os.path.dirname(input_path) or ".", "palette.json")
    if not os.path.isfile(palette_dir):
        palette_dir = "./01/palette.json"

    if not os.path.isfile(palette_dir):
        print(f"[错误] 找不到调色板文件: {palette_dir}")
        print("  请先运行 01颜色简化.py 生成 01/palette.json")
        return

    colors = load_palette(palette_dir)
    print(f"调色板: {', '.join(colors.keys())}")

    # --- 读取图像 ---
    image = cv2.imread(input_path)
    if image is None:
        print(f"[错误] 无法读取图片: {input_path}")
        return

    original = image.copy()
    current = image.copy()
    h, w = image.shape[:2]

    # 显示缩放
    scale = min(DISP_MAX_W / w, DISP_MAX_H / h, 1.0)
    disp_w, disp_h = int(w * scale), int(h * scale)

    # ── 交互状态 ──
    pts = []            # ROI 选区顶点
    kernel_str = ""     # 用户键入的窗口大小字符串
    status = "Click to select ROI, type window size, then Enter"
    show_hud = True     # Tab 切换 HUD 显示
    has_filtered = False
    mouse_xy = (-1, -1)  # 当前鼠标在显示图中的坐标
    undo_stack = []     # Z 键撤销历史（最多 2 步）

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, disp_w, disp_h)

    # ── 鼠标回调 ──
    def on_mouse(event, mx, my, flags, param):
        nonlocal pts, kernel_str
        if event == cv2.EVENT_LBUTTONDOWN:
            # 转回图像像素坐标
            ix = int(round(mx / scale))
            iy = int(round(my / scale))
            ix = max(0, min(w - 1, ix))
            iy = max(0, min(h - 1, iy))
            if len(pts) == 2:
                # 已有选区 → 重新开始，替换第一个点
                pts = [(ix, iy)]
                kernel_str = ""
            else:
                pts.append((ix, iy))
                if len(pts) == 2:
                    kernel_str = ""
        elif event == cv2.EVENT_RBUTTONDOWN:
            pts = []
            kernel_str = ""
        elif event == cv2.EVENT_MOUSEMOVE:
            nonlocal mouse_xy
            mouse_xy = (mx, my)

    cv2.setMouseCallback(WIN_NAME, on_mouse)

    # ── 主循环 ──
    while True:
        # 构建显示图
        disp_small = cv2.resize(current, (disp_w, disp_h), interpolation=cv2.INTER_NEAREST)
        disp = disp_small.copy()

        # 画选区矩形预览
        if len(pts) == 1:
            # 一个点已定，跟随鼠标画矩形
            px1, py1 = pts[0]
            px2 = int(round(mouse_xy[0] / scale))
            py2 = int(round(mouse_xy[1] / scale))
            # 转为显示坐标
            d_x1, d_y1 = int(px1 * scale), int(py1 * scale)
            d_x2, d_y2 = int(px2 * scale), int(py2 * scale)
            overlay = disp.copy()
            cv2.rectangle(overlay, (d_x1, d_y1), (d_x2, d_y2), OVERLAY_COLOR, -1)
            cv2.addWeighted(overlay, OVERLAY_ALPHA, disp, 1 - OVERLAY_ALPHA, 0, disp)
            cv2.rectangle(disp, (d_x1, d_y1), (d_x2, d_y2), OVERLAY_COLOR, 1)
        elif len(pts) == 2:
            px1, py1 = pts[0]
            px2, py2 = pts[1]
            d_x1, d_y1 = int(px1 * scale), int(py1 * scale)
            d_x2, d_y2 = int(px2 * scale), int(py2 * scale)
            overlay = disp.copy()
            cv2.rectangle(overlay, (d_x1, d_y1), (d_x2, d_y2), OVERLAY_DONE, -1)
            cv2.addWeighted(overlay, OVERLAY_ALPHA, disp, 1 - OVERLAY_ALPHA, 0, disp)
            cv2.rectangle(disp, (d_x1, d_y1), (d_x2, d_y2), OVERLAY_DONE, 1)

        # HUD
        if show_hud:
            _draw_hud(disp, scale, pts, kernel_str, status, has_filtered)
        cv2.imshow(WIN_NAME, disp)

        key = cv2.waitKey(30) & 0xFF
        if key == 0xFF:
            key = -1  # 无按键

        # 窗口被关闭（点击 X）→ 直接退出
        if cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

        # ── 按键处理 ──
        if key == 27:  # Esc
            break

        elif key in (ord('s'), ord('S')):  # 保存
            cv2.imwrite(input_path, current)
            status = f"Saved: {os.path.basename(input_path)}"
            has_filtered = False  # 保存后基线更新
            original = current.copy()
            pts = []
            kernel_str = ""
            undo_stack.clear()
            print(f"已保存: {input_path}")

        elif key == 9:  # Tab — 切换 HUD
            show_hud = not show_hud

        elif key in (ord('a'), ord('A')):  # 全选
            pts = [(0, 0), (w - 1, h - 1)]
            kernel_str = ""
            status = "ROI set to full image"

        elif key in (ord('r'), ord('R')):  # 撤销全部
            current = original.copy()
            has_filtered = False
            pts = []
            kernel_str = ""
            undo_stack.clear()
            status = "Reverted to original"

        elif key in (ord('z'), ord('Z')):  # 单步撤销
            if undo_stack:
                current = undo_stack.pop()
                has_filtered = len(undo_stack) > 0
                status = f"Undo ({len(undo_stack)} remaining)"
            else:
                status = "Nothing to undo"

        elif ord('0') <= key <= ord('9'):
            kernel_str += chr(key)
            status = f"Window: {kernel_str} (Enter to apply)"

        elif key == 8 or key == 127:  # Backspace / Delete
            kernel_str = kernel_str[:-1]
            status = f"Window: {kernel_str}" if kernel_str else ""

        elif key == 13:  # Enter — 执行滤波
            if not kernel_str:
                status = "No window size entered"
                continue
            ksize = int(kernel_str)
            if ksize < 3 or ksize % 2 == 0:
                status = f"Invalid: {ksize} (need odd >= 3)"
                continue

            # 保存当前状态到撤销栈（最多 2 步）
            undo_stack.append(current.copy())
            if len(undo_stack) > 2:
                undo_stack.pop(0)

            if len(pts) == 2:
                px1, py1 = pts[0]
                px2, py2 = pts[1]
                rx1 = min(px1, px2) / w
                ry1 = min(py1, py2) / h
                rx2 = max(px1, px2) / w
                ry2 = max(py1, py2) / h
                roi = (rx1, ry1, rx2, ry2)
                current = mode_filter(current, colors, ksize, roi=roi)
                status = f"Applied {ksize}x{ksize} to ROI ({rx1:.3f}, {ry1:.3f})-({rx2:.3f}, {ry2:.3f})"
            else:
                current = mode_filter(current, colors, ksize)
                status = f"Applied {ksize}x{ksize} to full image"

            has_filtered = True
            pts = []
            kernel_str = ""
            print(status)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
