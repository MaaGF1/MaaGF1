import frida
import time
import argparse
import sys
import os

JS_FILE = "hook_ui_scroll.js"

def on_message(message, data):
    if message['type'] == 'send':
        print(f"[*] {message['payload']}")
    elif message['type'] == 'error':
        print(f"[!] Error: {message['stack']}")
    else:
        print(message)

def main():
    parser = argparse.ArgumentParser(description="UI ScrollRect Injector")
    parser.add_argument("--process", default="GrilsFrontLine.exe", help="Target process name")
    parser.add_argument("--delta", type=float, default=-120.0, help="Scroll Delta") 
    parser.add_argument("--count", type=int, default=5, help="Scroll steps")
    
    args = parser.parse_args()

    # 1. Attach
    try:
        print(f"[*] Attaching to {args.process}...")
        session = frida.attach(args.process)
    except Exception as e:
        print(f"[!] Failed to attach: {e}")
        return

    # 2. Load Script
    with open(JS_FILE, "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()

    print("\n[!!!] IMPORTANT [!!!]")
    print("1. Enter the game and open a scrollable list (e.g., Inventory, Doll List).")
    print("2. Manually scroll the list ONCE using your mouse wheel.")
    print("3. Watch the console for '[Analyze] Found candidate...' message.")
    print("4. Once captured, this script will attempt to auto-scroll.")
    print("---------------------------------------------------------------")

    # Loop to check for capture
    captured = False
    while not captured:
        try:
            res = script.exports_sync.scroll(0) # Dummy call
            if "ERROR" not in str(res):
                captured = True
                print("[+] Capture successful! Starting injection...")
            else:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    # 3. Inject
    for i in range(args.count):
        res = script.exports_sync.scroll(args.delta)
        print(f"    -> {res}")
        time.sleep(0.1) # UI updates need time

    print("[*] Done. Detaching...")
    session.detach()

if __name__ == '__main__':
    main()