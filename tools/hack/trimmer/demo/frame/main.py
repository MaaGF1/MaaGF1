# tools/hack/trimmer/frame/main.py

import frida
import sys
import os
import time

def on_message(message, data):
    """
    Receive messages from the frame limiter JS hook.
    """
    if message['type'] == 'send':
        payload = message.get('payload', {})
        msg_type = payload.get('type')
        msg_text = payload.get('payload')
        
        if msg_type == 'error':
            print(f"[Frame Limit Error] {msg_text}")
        elif msg_type == 'info':
            print(f"[Frame Limit Info] {msg_text}")
        else:
            print(f"[Frame Limit Raw] {message}")
    else:
        print(f"[Frida System] {message}")

def main():
    # Note: Using the exact process name provided in previous scripts
    process_name = "GrilsFrontLine.exe" 
    print(f"[*] Attaching to process: {process_name} for Frame Limiting...")
    
    session = None
    for i in range(3):
        try:
            session = frida.attach(process_name)
            break
        except Exception as e:
            print(f"Retry {i+1} failed: {e}")
            time.sleep(1)
    
    if not session:
        print("[Error] Attach failed. Is the game running?")
        return

    script_path = "hook.js"
    if not os.path.exists(script_path):
        print(f"[Error] {script_path} missing in current directory.")
        return

    with open(script_path, "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] GPU/CPU Load Optimizer Running (FPS Capped)...")
    print("[*] Waiting for engine events. Press Enter to exit...")
    sys.stdin.read()

if __name__ == '__main__':
    main()