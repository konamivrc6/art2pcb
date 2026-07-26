"""
00编辑预设.py
管理 colorPresets.json 中的阻焊颜色预设。

功能:
  主菜单: 输入 0 创建新预设, 输入编号编辑已有预设
  编辑菜单: 0=删除, 1=改 DSolder, 2=改 LSolder, 3=改名字
  任意输入框输入 exit/quit 可回退到上一级或退出程序。
"""

import os
import json

PRESETS_PATH = "colorPresets.json"


# ============================================================
# 工具函数
# ============================================================
def load_presets():
    """读取预设 JSON，返回列表 [{id, name, DSolder, LSolder}, ...]。"""
    if not os.path.exists(PRESETS_PATH):
        return []
    with open(PRESETS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_presets(presets):
    """保存预设列表到 JSON 文件。"""
    with open(PRESETS_PATH, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)
    print(f"已保存到 {PRESETS_PATH}\n")


def renumber(presets):
    """按列表顺序重新编号（1 起始）。"""
    for i, p in enumerate(presets):
        p["id"] = i + 1


def input_hex(label):
    """输入十六进制颜色值，返回 '#RRGGBB' 字符串。
       输入 exit/quit 抛出 StopIteration 回到上一级。"""
    while True:
        val = input(f"  {label}: ").strip()
        if val.lower() in ("exit", "quit"):
            raise StopIteration
        if val and not val.startswith("#"):
            val = "#" + val
        if len(val) == 7 and val.startswith("#"):
            return val
        print("    [格式错误] 请输入 #RRGGBB 格式（或输入 exit/quit 返回）")


def input_name():
    """输入预设名称，输入 exit/quit 抛出 StopIteration。"""
    while True:
        val = input("  预设名称: ").strip()
        if val.lower() in ("exit", "quit"):
            raise StopIteration
        if val:
            return val
        print("    [错误] 名称不能为空（或输入 exit/quit 返回）")


def input_choice(prompt, valid_set):
    """通用选项输入，输入 exit/quit 抛出 StopIteration。"""
    while True:
        val = input(prompt).strip()
        if val.lower() in ("exit", "quit"):
            raise StopIteration
        if val in valid_set:
            return val
        print(f"    [错误] 请输入 {', '.join(sorted(valid_set))} 之一（或输入 exit/quit 返回）")


# ============================================================
# 显示
# ============================================================
def show_presets(presets):
    """打印当前所有预设。"""
    print("=" * 50)
    print("  当前阻焊颜色预设")
    print("=" * 50)
    if not presets:
        print("  (无预设)")
    else:
        for p in presets:
            print(f"  {p['id']} — {p['name']:6s}  DSolder={p['DSolder']}  LSolder={p['LSolder']}")
    print("=" * 50)


# ============================================================
# 创建新预设
# ============================================================
def create_preset(presets):
    """交互式创建新预设，参考 01颜色简化.py 的手动输入部分。"""
    print("\n--- 创建新预设 ---")
    print("(任意步骤输入 exit/quit 可取消创建)\n")
    try:
        name = input_name()
        print()
        dsolder = input_hex("DSolder (深阻焊)")
        print()
        lsolder = input_hex("LSolder (浅阻焊)")
    except StopIteration:
        print("  已取消创建。\n")
        return

    new_id = presets[-1]["id"] + 1 if presets else 1
    presets.append({"id": new_id, "name": name, "DSolder": dsolder, "LSolder": lsolder})
    save_presets(presets)
    print(f"已添加预设: {new_id} — {name}  DSolder={dsolder}  LSolder={lsolder}\n")


# ============================================================
# 编辑已有预设
# ============================================================
def edit_preset(presets, idx):
    """编辑单个预设的子菜单。idx 为在列表中的索引。"""
    p = presets[idx]
    while True:
        print(f"\n--- 编辑预设 {p['id']} — {p['name']} ---")
        print(f"  DSolder = {p['DSolder']}")
        print(f"  LSolder = {p['LSolder']}")
        print()
        print("  0 — 删除此预设")
        print("  1 — 修改 DSolder (深阻焊)")
        print("  2 — 修改 LSolder (浅阻焊)")
        print("  3 — 修改预设名称")
        print("  输入 exit/quit 返回主菜单")
        print("-" * 40)

        try:
            choice = input_choice("请选择 (0-3): ", {"0", "1", "2", "3"})
        except StopIteration:
            print("  返回主菜单。\n")
            return False

        try:
            if choice == "0":
                confirm = input(f"  确定删除预设「{p['name']}」? (y/n): ").strip().lower()
                if confirm in ("y", "yes"):
                    del presets[idx]
                    renumber(presets)
                    save_presets(presets)
                    print(f"  已删除，预设已重新编号。\n")
                    return True  # 预设被删除，列表已变

            elif choice == "1":
                print()
                p["DSolder"] = input_hex("新的 DSolder")
                save_presets(presets)
                print(f"  DSolder 已更新为 {p['DSolder']}\n")

            elif choice == "2":
                print()
                p["LSolder"] = input_hex("新的 LSolder")
                save_presets(presets)
                print(f"  LSolder 已更新为 {p['LSolder']}\n")

            elif choice == "3":
                print()
                p["name"] = input_name()
                save_presets(presets)
                print(f"  名称已更新为「{p['name']}」\n")

        except StopIteration:
            print("  已取消操作。")
            continue

    return False


# ============================================================
# 主循环
# ============================================================
def main():
    presets = load_presets()

    while True:
        show_presets(presets)

        # 构建合法选项：0 + 所有预设 id
        valid = {"0"}
        id_to_idx = {}
        for i, p in enumerate(presets):
            valid.add(str(p["id"]))
            id_to_idx[str(p["id"])] = i

        prompt = "输入预设编号以编辑, 0 创建新预设 (exit/quit 退出): "
        try:
            choice = input_choice(prompt, valid)
        except StopIteration:
            print("退出。")
            break

        if choice == "0":
            create_preset(presets)
        else:
            idx = id_to_idx[choice]
            deleted = edit_preset(presets, idx)
            if deleted:
                # 预设列表已变化，刷新
                continue


if __name__ == "__main__":
    main()
