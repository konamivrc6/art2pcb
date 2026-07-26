"""
04图片边框.py
对 03/ 目录下的所有图层 PNG 四周各扩展 10px，
扩展区域填充黑白像素交替排列（棋盘格）。输出到 04/ 目录。

双击即可运行，自动处理所有图层。
"""

import os
import cv2
import numpy as np
from pathlib import Path

# ============================================================
# 可配置参数
# ============================================================
CONFIG = {
    "border": 10,  # 四周扩展的像素宽度
}


def add_checkerboard_border(image, border):
    """
    给图像四周各扩展 border 像素，扩展区域用黑白交替的棋盘格填充。

    参数:
        image:  灰度图 (h, w)，像素值 0=黑, 255=白
        border: 扩展宽度 (px)

    返回:
        扩展后的灰度图 (h+2*border, w+2*border)
    """
    h, w = image.shape
    new_h = h + 2 * border
    new_w = w + 2 * border

    # 创建棋盘格背景：用行号+列号的奇偶性决定黑白
    row_indices = np.arange(new_h).reshape(-1, 1)  # (new_h, 1)
    col_indices = np.arange(new_w).reshape(1, -1)  # (1, new_w)
    checker = ((row_indices + col_indices) % 2 == 0).astype(np.uint8) * 255

    # 将原图嵌入棋盘格中央
    result = checker.copy()
    result[border:border + h, border:border + w] = image

    return result


def main():
    src_dir = Path("03")
    out_dir = Path("04")

    files = sorted(src_dir.glob("*.png"))
    if not files:
        print(f"[错误] 在 {src_dir}/ 下没有找到 PNG 文件，请先运行 03颜色合并.py")
        return

    os.makedirs(out_dir, exist_ok=True)

    border = CONFIG["border"]
    print(f"输入: {src_dir}/  输出: {out_dir}/")
    print(f"边框宽度: {border}px，填充模式: 黑白像素交替（棋盘格）")
    print()

    for f in files:
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  [跳过] 无法读取: {f}")
            continue

        result = add_checkerboard_border(img, border)

        out_path = out_dir / f.name
        cv2.imwrite(str(out_path), result)

        h, w = img.shape
        new_h, new_w = result.shape
        print(f"  {f.name:16s}  {w}x{h} -> {new_w}x{new_h}  -> {out_path}")

    print()
    print("完成!")


if __name__ == "__main__":
    main()
