"""
05反相.py
对 04/ 目录下的所有图层 PNG 做反相处理（黑白互换），输出到 05/ 目录。

用途：不同 EDA 对图片的"背景"颜色约定不同——有些以白色为背景，
有些以黑色为背景。此脚本生成反相后的图层，方便在两种 EDA 之间切换。

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
    "invert_value": 255,  # 反相基准值：灰度图用 255 - 原值
}


def invert_image(image):
    """
    对灰度图做反相：白色变黑色，黑色变白色。

    参数:
        image: 灰度图 (h, w)，像素值 0=黑, 255=白

    返回:
        反相后的灰度图 (h, w)
    """
    return CONFIG["invert_value"] - image


def main():
    src_dir = Path("04")
    out_dir = Path("05")

    files = sorted(src_dir.glob("*.png"))
    if not files:
        print(f"[错误] 在 {src_dir}/ 下没有找到 PNG 文件，请先运行 04图片边框.py")
        return

    os.makedirs(out_dir, exist_ok=True)

    print(f"输入: {src_dir}/  输出: {out_dir}/")
    print(f"处理模式: 反相（黑白互换）")
    print()

    for f in files:
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  [跳过] 无法读取: {f}")
            continue

        result = invert_image(img)

        out_path = out_dir / f.name
        cv2.imwrite(str(out_path), result)

        h, w = img.shape
        print(f"  {f.name:16s}  {w}x{h}  反相完成  -> {out_path}")

    print()
    print("完成! 提示：04/ 和 05/ 分别适用于不同背景颜色约定的 EDA。")


if __name__ == "__main__":
    main()
