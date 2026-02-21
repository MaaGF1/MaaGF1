import frida
import sys
import os

# 排队枪毙环节的Cam
JS_FILE = "monitor_battle_cam.js"

def on_message(message, data):
    if message['type'] == 'send':
        print(message['payload'])
    elif message['type'] == 'error':
        print(f"[!] Error: {message['stack']}")
    else:
        print(message)

def main():
    process_name = "GrilsFrontLine.exe" 
    
    print(f"[*] Attaching to {process_name}...")
    try:
        session = frida.attach(process_name)
    except Exception as e:
        print(f"[!] Failed to attach: {e}")
        return

    with open(JS_FILE, "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("==================================================")
    print("1. Please enter the BATTLE SCENE.")
    print("2. Scroll the mouse wheel to ZOOM.")
    print("3. Watch the console for [BattleCam] logs.")
    print("==================================================")
    
    # 测试获取实例
    print("\n[*] Testing get_Instance()...")
    res = script.exports_sync.test_call()
    print(f"[*] Result: {res}\n")

    sys.stdin.read()

if __name__ == '__main__':
    main()