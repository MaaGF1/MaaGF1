import frida
import sys
import os

JS_FILE = "monitor_rect.js"

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[*] {message['payload']}")
    elif message['type'] == 'error':
        print(f"[!] Error: {message['stack']}")
    else:
        if 'payload' in message:
            print(message['payload'])
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
    
    print("[*] Monitoring RectTransform... Please DRAG the map in-game.")
    sys.stdin.read()

if __name__ == '__main__':
    main()