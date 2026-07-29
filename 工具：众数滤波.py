"""
众数滤波 — 对量化后的 01/01.png 做众数滤波，去除细线杂质。

用法:
    python 工具：众数滤波.py                  # 默认处理 01/01.png
    python 工具：众数滤波.py myimage.png      # 拖放或指定文件

原理:
    对每个像素，用 K×K 邻域内出现次数最多的颜色替换它。
    细线（1-3px）会被周围的主导颜色"投票投掉"，且不会产生新的中间色。
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


def mode_filter(image, color_dict, kernel_size):
    """
    众数滤波：用 K×K 窗口内出现次数最多的颜色替换每个像素。

    image:      量化后的 BGR 图像
    color_dict: {name: BGR array}
    kernel_size: 窗口边长（奇数，如 5）
    """
    if kernel_size < 3 or kernel_size % 2 == 0:
        raise ValueError("kernel_size 必须为 ≥3 的奇数")

    h, w = image.shape[:2]
    if h < kernel_size or w < kernel_size:
        print(f"  [跳过滤波] 图像尺寸 ({w}×{h}) < 窗口 ({kernel_size}×{kernel_size})")
        return image

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


def load_palette(path="./01/palette.json"):
    """读取调色板 JSON，返回 {name: BGR array}。"""
    with open(path, "r", encoding="utf-8") as f:
        hexColors = json.load(f)
    return {name: hex_to_BGR(value) for name, value in hexColors.items()}


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
        # 如果图片旁边没有 palette.json，尝试 01/ 目录
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

    h, w = image.shape[:2]
    print(f"图像尺寸: {w} × {h}")

    # --- 交互式选择窗口大小 ---
    print("\n" + "=" * 50)
    print("  众数滤波 — 窗口大小")
    print("=" * 50)
    print("  0      — 退出（不做处理）")
    print("  3      — 3×3 窗口（轻度，去 1px 细线）")
    print("  5      — 5×5 窗口（推荐，去 2-3px 细线）")
    print("  7      — 7×7 窗口（激进）")
    print("  更大奇数 — 更激进")
    print("=" * 50)

    while True:
        choice = input("请选择: ").strip()
        if choice == "" or choice == "0":
            print("已取消")
            return
        if choice.isdigit():
            val = int(choice)
            if val >= 3 and val % 2 == 1:
                kernel_size = val
                break
        print("[错误] 请输入 0 或 ≥3 的奇数")

    # --- 众数滤波 ---
    print(f"\n众数滤波: 窗口 {kernel_size}×{kernel_size} ...")
    filtered = mode_filter(image, colors, kernel_size)

    # --- 预览 ---
    cv2.namedWindow("Mode Filter", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Mode Filter", 600, 400)
    cv2.imshow("Mode Filter", filtered)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # --- 保存（覆盖原图）---
    cv2.imwrite(input_path, filtered)
    print(f"已保存: {input_path}")


if __name__ == "__main__":
    main()
