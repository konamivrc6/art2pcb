import os
import json
import cv2
import numpy as np


def hex_to_BGR(hex_color):
    """ '#RRGGBB' → BGR numpy array """
    hex_color = hex_color.lstrip('#')
    bgr_color = np.array([int(hex_color[i:i + 2], 16) for i in (4, 2, 0)])
    return bgr_color


# ============================================================
# 固定颜色（不随预设变化）
# ============================================================
FIXED = {
    "DGreen":  "#193522",
    "LYellow": "#F9E195",
    "Black":   "#061008",
    "White":   "#E6EAEB",
}

# ============================================================
# 从 colorPresets.json 加载阻焊预设
# ============================================================
def load_presets(path="colorPresets.json"):
    """读取预设文件，返回 {id: {name, DSolder, LSolder}} 字典。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {item["id"]: {"name": item["name"], "DSolder": item["DSolder"], "LSolder": item["LSolder"]} for item in raw}


PRESETS = load_presets()


# ============================================================
# 交互式选择
# ============================================================
def choose_colors():
    print("=" * 50)
    print("  阻焊颜色预设")
    print("=" * 50)
    print("  0 — 自行输入阻焊颜色")
    for k, v in PRESETS.items():
        print(f"  {k} — {v['name']}")
    print("=" * 50)

    while True:
        choice = input("请选择 (0-7): ").strip()
        if choice in [str(i) for i in range(8)]:
            break
        print("[错误] 请输入 0-7 之间的数字")

    choice = int(choice)

    if choice == 0:
        print("\n请输入阻焊颜色的十六进制值（如 #a64951）：")
        solder = {}
        for label, key in [("DSolder", "DSolder"), ("LSolder", "LSolder")]:
            while True:
                val = input(f"  {key}: ").strip()
                if val and not val.startswith("#"):
                    val = "#" + val
                if len(val) == 7 and val.startswith("#"):
                    solder[key] = val
                    break
                print("    [格式错误] 请输入 #RRGGBB 格式")
        return {**FIXED, **solder}

    else:
        preset = PRESETS[choice]
        if not preset["DSolder"] or not preset["LSolder"]:
            print(f"\n[警告] 预设「{preset['name']}」尚未填写。请编辑 PRESETS 字典补全后重试。")
            exit(1)

        print(f"\n已选择预设: {preset['name']}")
        return {**FIXED, "DSolder": preset["DSolder"], "LSolder": preset["LSolder"]}


# ============================================================
# 主流程
# ============================================================
def main():
    hexColors = choose_colors()

    print("\n当前颜色配置:")
    for ck, cv_ in hexColors.items():
        print(f"  {ck:10s} → {cv_}")

    # 保存调色板到 01/ 供后续脚本读取
    os.makedirs("./01", exist_ok=True)
    with open("./01/palette.json", "w", encoding="utf-8") as f:
        json.dump(hexColors, f, indent=2, ensure_ascii=False)
    print("\n调色板已保存: ./01/palette.json")

    colors = {color: hex_to_BGR(value) for color, value in hexColors.items()}

    # 读取图像
    image = cv2.imread("origin.png")
    if image is None:
        print("\n[错误] 找不到 origin.png，请将原图放在当前目录下。")
        return

    print(f"\n处理中... (图像尺寸: {image.shape[1]} x {image.shape[0]})")

    # 遍历图像的每个像素
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            pixel = image[i, j]

            # 计算像素颜色与定义的颜色值的欧氏距离
            distances = {color: np.linalg.norm(pixel - value) for color, value in colors.items()}

            # 找到最小距离对应的颜色，并将像素设置为该颜色
            min_distance_color = min(distances, key=distances.get)
            image[i, j] = colors[min_distance_color]

    # 显示处理后的图像
    cv2.namedWindow("Processed Image", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Processed Image", 600, 400)

    cv2.imshow("Processed Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # 保存图像到固定路径
    os.makedirs("./01", exist_ok=True)
    output_path = "./01/01.png"
    cv2.imwrite(output_path, image)
    print(f"已保存: {output_path}")


if __name__ == "__main__":
    main()
