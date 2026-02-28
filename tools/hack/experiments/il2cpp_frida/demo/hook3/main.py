import frida
import sys
import gzip
import json
import os
import time

# ================= 配置区域 =================
OUTPUT_DIR = "debug_dumps"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
# ===========================================

def save_dump(data, prefix, tag=""):
    """辅助函数：保存二进制数据到文件"""
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{prefix}{tag}.gz"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    return filename

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'req_modify':
            original_len = len(data)
            print(f"\n[Python] ⚡ 捕获数据包，原始大小: {original_len} bytes")
            
            # 1. 先把原始包 Dump 下来，万一有问题可以分析
            save_dump(data, "original")

            try:
                # 2. 解压
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                json_obj = json.loads(json_str)
                
                modified = False
                
                # 3. 类型检查：确保是字典结构
                if isinstance(json_obj, dict):
                    
                    # 检查是否包含结算信息
                    if "mission_win_result" in json_obj:
                        print("[Python] 🎯 命中目标：mission_win_result")
                        
                        win_result = json_obj["mission_win_result"]
                        
                        # === 修改数值 ===
                        old_exp = win_result.get("user_exp", "N/A")
                        win_result["user_exp"] = "255"
                        print(f"[Python] 🛠️  修改 user_exp: {old_exp} -> 255")
                        
                        # === 【关键步骤】删除垃圾数据以腾出空间 ===
                        # mica_client_log 通常包含大量统计信息，删除它非常安全且能大幅减小体积
                        if "mica_client_log" in win_result:
                            print("[Python] 🗑️  删除 mica_client_log 以缩减体积...")
                            del win_result["mica_client_log"]
                        
                        modified = True
                    else:
                        print("[Python] ℹ️  非结算包，跳过修改。")
                else:
                    print(f"[Python] ℹ️  数据结构为 {type(json_obj)}，跳过。")

                if modified:
                    # 4. 重新序列化 (去除空格)
                    new_json_str = json.dumps(json_obj, separators=(',', ':'), ensure_ascii=False)
                    
                    # 5. 重新压缩 (Level 9 最高压缩率)
                    new_gzip_data = gzip.compress(new_json_str.encode('utf-8'), compresslevel=9)
                    new_len = len(new_gzip_data)
                    
                    print(f"[Python] 📦 重新压缩: {original_len} -> {new_len} bytes")

                    # 6. 最终体积检查
                    if new_len <= original_len:
                        print(f"[Python] ✅ 体积检查通过 (剩余空间: {original_len - new_len} bytes)")
                        
                        # 保存修改后的包以供检查
                        save_dump(new_gzip_data, "modified", "_SUCCESS")
                        
                        script.post({
                            'type': 'resp_modify',
                            'payload': 'modified'
                        }, new_gzip_data)
                    else:
                        print(f"[Python] ⚠️ 警告：修改后体积 ({new_len}) 仍大于原始体积 ({original_len})！")
                        print("[Python] ❌ 放弃发送，防止游戏崩溃。建议寻找更多可删除字段。")
                        save_dump(new_gzip_data, "modified", "_TOO_LARGE")
                        script.post({'type': 'resp_modify', 'payload': 'original'})
                    
                else:
                    script.post({'type': 'resp_modify', 'payload': 'original'})

            except Exception as e:
                print(f"[Python] ❌ 处理异常: {e}")
                import traceback
                traceback.print_exc()
                script.post({'type': 'resp_modify', 'payload': 'original'})

def main():
    process_name = "GrilsFrontLine.exe"
    print(f"[*] 正在附加到进程: {process_name} ...")
    try:
        session = frida.attach(process_name)
    except Exception as e:
        print(f"无法附加: {e}")
        return

    # 读取之前的 JS 文件 (hook_mitm.js)
    if not os.path.exists("hook_mitm.js"):
        print("错误：找不到 hook_mitm.js 文件")
        return

    with open("hook_mitm.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    global script
    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] 脚本已加载，数据包将自动保存到 debug_dumps 目录...")
    sys.stdin.read()

if __name__ == '__main__':
    main()