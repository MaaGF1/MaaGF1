# tools/hack/il2cpp_frida/demo/hook4/find_ui.py

# 查找可能的 “获取新枪奖励的MessageBox” 函数

# i.e. CommonGetNewGunController

import json

def find_target_functions():
    print("[*] 正在加载 script.json (可能需要几秒钟)...")
    try:
        with open("script.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("[Error] 找不到 script.json，请确保它和本脚本在同一目录。")
        return

    # === 核心修复：适配 IL2CppDumper 的标准结构 ===
    methods = []
    if isinstance(data, dict):
        if "ScriptMethod" in data:
            methods = data["ScriptMethod"]
        else:
            # 如果结构被修改过，尝试自动寻找包含Address的列表
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and "Address" in val[0]:
                    methods = val
                    break
    elif isinstance(data, list):
        methods = data
    
    if not methods:
        print("[Error] 无法解析 script.json 的结构，找不到方法列表。")
        return

    print(f"[*] 成功解析，共加载 {len(methods)} 条函数记录。\n[*] 正在检索接收 T-Doll 数据的 UI 函数...\n")
    
    candidates = []
    for item in methods:
        if not isinstance(item, dict): 
            continue
            
        name = item.get("Name", "")
        sig = item.get("Signature", "")
        
        name_lower = name.lower()
        sig_lower = sig.lower()
        
        # 核心过滤逻辑：
        if "gf_battle_gun" in sig_lower:
            if "controller" in name_lower or "ui" in name_lower or "window" in name_lower or "panel" in name_lower:
                if "init" in name_lower or "show" in name_lower or "setup" in name_lower or "open" in name_lower:
                    candidates.append(item)

    if not candidates:
        print("[-] 没有找到完全匹配的特征，放宽条件检索...")
        for item in methods:
            if not isinstance(item, dict): 
                continue
            name_lower = item.get("Name", "").lower()
            if ("getgun" in name_lower or "rewardgun" in name_lower or "newgun" in name_lower) and "controller" in name_lower:
                candidates.append(item)

    print(f"[*] 检索完毕！找到 {len(candidates)} 个嫌疑函数：\n")
    print("-" * 60)
    for res in candidates[:30]:  # 打印前30个
        print(f"Name: {res.get('Name')}")
        print(f"Address: {res.get('Address')}")
        print(f"Signature: {res.get('Signature')}")
        print("-" * 60)

if __name__ == '__main__':
    find_target_functions()