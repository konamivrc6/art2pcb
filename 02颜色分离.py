"""
02颜色分离.py
从 01/palette.json 读取颜色定义，将 01/01.png 中每种颜色分离为独立遮罩。

输出到 02/ 目录:
  white.png         -- 白   (正面丝印层)
  light_solder.png  -- 浅阻焊 (正面有阻焊，有铜皮)
  dark_solder.png   -- 深阻焊 (正面有阻焊，没铜皮)
  black.png         -- 黑   (正面没阻焊，有铜皮)
  deep_green.png    -- 深绿  (正面没阻焊，背面有阻焊)
  light_yellow.png  -- 浅黄  (正面没阻焊，背面没阻焊)
"""

import os
import json
import cv2
import numpy as np


# 颜色名 → 输出文件名的映射
NAME_MAP = {
    "White":   "white.png",
    "LSolder": "light_solder.png",
    "DSolder": "dark_solder.png",
    "Black":   "black.png",
    "DGreen":  "deep_green.png",
    "LYellow": "light_yellow.png",
}


def hex_to_bgr(hex_color):
    """ '#RRGGBB' → BGR numpy array """
    hex_color = hex_color.lstrip('#')
    return np.array([int(hex_color[i:i + 2], 16) for i in (4, 2, 0)])


def load_colors_from_palette(path="01/palette.json"):
    """从 01/palette.json 读取颜色，返回 {颜色名: BGR array}。"""
    with open(path, "r", encoding="utf-8") as f:
        palette = json.load(f)

    colors = {}
    for name, hex_val in palette.items():
        colors[name] = hex_to_bgr(hex_val)
        print(f"  从 palette 读取: {name:8s} → {hex_val} → BGR {colors[name]}")

    return colors


def main():
    # 从 palette 加载颜色
    print("从 01/palette.json 加载颜色定义...")
    colors = load_colors_from_palette()

    # 读取简化图
    src_path = "01/01.png"
    image = cv2.imread(src_path)
    if image is None:
        print(f"[错误] 找不到 {src_path}，请先运行 01颜色简化.py")
        return

    h, w = image.shape[:2]
    print(f"\n读取: {src_path} ({w} x {h})")

    # 创建输出目录
    os.makedirs("02", exist_ok=True)
    print()

    # 为每种颜色创建遮罩并保存
    for color_name, bgr in colors.items():
        filename = NAME_MAP.get(color_name, f"{color_name}.png")

        # 匹配颜色 (精确匹配，因为 01 已做颜色量化)
        mask = np.all(image == bgr, axis=-1)

        # 生成遮罩图像 (匹配区域保留原色，其余为黑色)
        mask_image = np.zeros_like(image)
        mask_image[mask] = [255, 255, 255]

        # 保存
        out_path = f"02/{filename}"
        cv2.imwrite(out_path, mask_image)

        count = np.sum(mask)
        print(f"  {out_path:25s}  {count:>10,d} 像素  ({count/(h*w)*100:5.2f}%)")

    print()
    print("完成! 下一步: 运行 03颜色合并.py")


if __name__ == "__main__":
    main()
