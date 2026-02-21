import frida
import sys
import os

JS_FILE = "monitor_cinemachine.js"

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
    print("1. Enter the SLG / Campaign Map.")
    print("2. DRAG the map with your mouse.")
    print("3. SCROLL the wheel to ZOOM.")
    print("==================================================")
    sys.stdin.read()

if __name__ == '__main__':
    main()