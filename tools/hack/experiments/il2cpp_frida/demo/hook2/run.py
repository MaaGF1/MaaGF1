import frida
import sys
import gzip
import os
import json

# 确保输出目录存在
OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 计数器，用于生成 001.json, 002.json
file_counter = 1

def on_message(message, data):
    global file_counter
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'gzip_data':
            print(f"[Python] 收到数据包，大小: {len(data)} bytes")
            
            try:
                # 1. 解压 Gzip
                decompressed_data = gzip.decompress(data)
                
                # 2. 尝试转为字符串 (UTF-8)
                json_str = decompressed_data.decode('utf-8')
                
                # 3. 格式化 JSON (可选，为了好看)
                try:
                    parsed_json = json.loads(json_str)
                    content_to_save = json.dumps(parsed_json, indent=4, ensure_ascii=False)
                except:
                    # 如果不是标准JSON，就直接保存原始字符串
                    content_to_save = json_str

                # 4. 保存文件
                filename = f"{file_counter:03d}.json"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content_to_save)
                
                print(f"[Python] ✅ 已解压并保存: {filepath}")
                file_counter += 1

            except Exception as e:
                print(f"[Python] ❌ 处理失败: {e}")
                # 如果解压失败，保存原始 Gzip 供分析
                err_filename = f"{file_counter:03d}_error.gz"
                with open(os.path.join(OUTPUT_DIR, err_filename), "wb") as f:
                    f.write(data)
                file_counter += 1

def main():
    process_name = "GrilsFrontLine.exe"
    
    print(f"[*] 正在附加到进程: {process_name} ...")
    try:
        session = frida.attach(process_name)
    except Exception as e:
        print(f"无法附加: {e}")
        print("请确保游戏正在运行。")
        return

    # 读取你的 JS 脚本内容
    with open("hook_respon.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] 脚本已加载，请在游戏中触发网络请求...")
    sys.stdin.read()

if __name__ == '__main__':
    main()