# tools/hack/trimmer/reward_gun/main.py

import frida
import sys
import os
import time

def on_message(message, data):
    """
    Receive control flow hijacking reports from the JS.
    """
    if message['type'] == 'send':
        payload = message.get('payload', {})
        msg_type = payload.get('type')
        msg_text = payload.get('payload')
        
        if msg_type == 'error':
            print(f"[Frida Error] {msg_text}")
        elif msg_type == 'info':
            print(f"[Frida] {msg_text}")
        else:
            print(f"[Frida Raw] {message}")
    else:
        print(f"[Frida System] {message}")

def main():
    process_name = "GrilsFrontLine.exe" 
    print(f"[*] Attaching to process: {process_name} ...")
    
    session = None
    for i in range(3):
        try:
            session = frida.attach(process_name)
            break
        except Exception as e:
            print(f"Retry {i+1}: {e}")
            time.sleep(1)
    
    if not session:
        print("[Error] Attach failed. Is the game running?")
        return

    if not os.path.exists("hook_mitm.js"):
        print("[Error] hook_mitm.js missing")
        return

    with open("hook_mitm.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] Settlement Accelerator Running (Control Flow Hijacked)...")
    print("[*] Waiting for UI trigger events...")
    sys.stdin.read()

if __name__ == '__main__':
    main()