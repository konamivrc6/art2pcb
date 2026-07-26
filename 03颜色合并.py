"""
03颜色合并.py
根据《附录：颜色合成公式.txt》，将 02/ 中的纯白遮罩合成为 PCB 图层。

输入: 02/*.png (纯白=有, 纯黑=无)
输出到 03/ 目录:
  topCu.png       正面铜皮层   (浅阻焊 + 黑)
  topSolder.png   正面阻焊层   (深阻焊+浅阻焊+白+黑, 负片)
  topText.png     正面丝印层   (白)
  bottomCu.png    背面铜皮层   (深绿 + 浅黄)
  bottomSolder.png 背面阻焊层  (深绿, 负片)

注: 阻焊层为负片，白色=开窗(露铜)，黑色=覆盖阻焊。
"""

import os
import cv2
import numpy as np

# ============================================================
# 图层合成公式 (来自《附录：颜色合成公式.txt》)
# invert=True 表示负片输出 (白色=开窗, 黑色=覆盖阻焊)
# ============================================================
LAYERS = {
    "topCu": {
        "parts": ["light_solder", "black"],
        "describe": "正面铜皮层 (浅阻焊+黑)",
        "invert": False,
    },
    "topSolder": {
        "parts": ["dark_solder", "light_solder", "white", "black"],
        "describe": "正面阻焊层 (深阻焊+浅阻焊+白+黑, 负片)",
        "invert": True,
    },
    "topText": {
        "parts": ["white"],
        "describe": "正面丝印层 (白)",
        "invert": False,
    },
    "bottomCu": {
        "parts": ["deep_green", "light_yellow"],
        "describe": "背面铜皮层 (深绿+浅黄)",
        "invert": False,
    },
    "bottomSolder": {
        "parts": ["deep_green"],
        "describe": "背面阻焊层 (深绿, 负片)",
        "invert": True,
    },
}


def load_mask(name, src_dir="02"):
    """读取 02/{name}.png，返回灰度图 (0=黑, 255=白)。"""
    path = f"{src_dir}/{name}.png"
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"找不到 {path}，请先运行 02颜色分离.py")
    return img


def main():
    # 检查输入文件
    required = ["dark_solder", "light_solder", "deep_green", "light_yellow", "black", "white"]
    missing = [n for n in required if not os.path.exists(f"02/{n}.png")]
    if missing:
        print(f"[错误] 02/ 目录缺少以下文件: {missing}")
        print("请先运行 02颜色分离.py")
        return

    # 加载所有遮罩
    print("加载遮罩...")
    masks = {}
    for name in required:
        masks[name] = load_mask(name)
        white_px = np.sum(masks[name] > 0)
        total = masks[name].size
        print(f"  {name:14s}  白像素 {white_px:>10,d} / {total:>10,d}  ({white_px/total*100:5.2f}%)")

    h, w = masks["white"].shape

    # 合成图层
    print("\n合成图层...")
    os.makedirs("03", exist_ok=True)

    for layer_name, info in LAYERS.items():
        # 像素级 OR：任一组件为白即输出白
        combined = np.zeros((h, w), dtype=np.uint8)
        for part in info["parts"]:
            combined = np.maximum(combined, masks[part])

        # 阻焊层负片：黑白翻转
        if info.get("invert"):
            combined = 255 - combined

        out_path = f"03/{layer_name}.png"
        cv2.imwrite(out_path, combined)

        white_px = np.sum(combined > 0)
        print(f"  {out_path:20s}  白像素 {white_px:>10,d}  ({white_px/(h*w)*100:5.2f}%)  -- {info['describe']}")

    print("\n完成! 下一步: 运行 04图片边框.py")
    print()
    print("图层说明:")
    print("  topCu.png       -> 正面铜皮  -> 立创EDA: 顶层铜皮")
    print("  topSolder.png   -> 正面阻焊  -> 立创EDA: 顶层阻焊 (负片: 白=开窗)")
    print("  topText.png     -> 正面丝印  -> 立创EDA: 顶层丝印")
    print("  bottomCu.png    -> 背面铜皮  -> 立创EDA: 底层铜皮")
    print("  bottomSolder.png -> 背面阻焊 -> 立创EDA: 底层阻焊 (负片: 白=开窗)")


if __name__ == "__main__":
    main()
