import frida
import sys
import threading
import time
import ctypes
from ctypes import wintypes

# ================= Windows API =================
user32 = ctypes.windll.user32

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

def get_window_handle(process_name):
    hwnd = user32.FindWindowW(None, "Girls' Frontline") 
    if not hwnd:
        hwnd = user32.FindWindowW(None, "少女前线")
    return hwnd

def send_click_message(hwnd, x, y):
    if not hwnd:
        print("[!] Error: Window handle not found. Cannot send click.")
        return
    
    # Construct lParam (high bits are Y, low bits are X)
    lParam = (y << 16) | (x & 0xFFFF)
    
    # Send press and release messages via **PostMessage**
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
    # Click Delay
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lParam)
    print(f"[*] Sent click message to HWND {hwnd} at ({x}, {y})")

# ================= Frida =================

def on_message(message, data):
    if message['type'] == 'send':
        print(message['payload'])
    elif message['type'] == 'error':
        print(f"[!] Error: {message['stack']}")

def main():
    target_process = "GrilsFrontLine.exe"
    
    # Load JS
    try:
        with open("hook.js", "r", encoding="utf-8") as f:
            jscode = f.read()
    except FileNotFoundError:
        print("Error: hook_v7_debug.js not found.")
        return

    try:
        print(f"[*] Attaching to {target_process}...")
        session = frida.attach(target_process)
    except Exception as e:
        print(f"[!] Failed to attach: {e}")
        print("Ensure the game is running and you have Administrator privileges.")
        return

    script = session.create_script(jscode)
    script.on('message', on_message)
    script.load()

    print("[*] Hook loaded. Try clicking in the game window.")
    print("[*] Commands:")
    print("    fake x y      -> Set internal fake coordinates")
    print("    click x y     -> Set fake coords AND send background click")
    print("    mode monitor  -> Watch real mouse")
    print("    mode inject   -> Override mouse position")
    print("    hwnd          -> Try to find Window Handle (Debug)")

    # Get HWND
    game_hwnd = get_window_handle(target_process)
    if game_hwnd:
        print(f"[+] Found Game Window Handle: {hex(game_hwnd)}")
    else:
        print("[!] Warning: Could not find game window automatically.")

    while True:
        try:
            cmd = input().strip()
            if cmd == 'exit':
                break
            
            parts = cmd.split()
            if not parts: continue

            if parts[0] == 'mode':
                script.post({'type': 'SET_MODE', 'mode': parts[1]})
            
            elif parts[0] == 'fake':
                if len(parts) == 3:
                    x, y = int(parts[1]), int(parts[2])
                    script.post({'type': 'SIMULATE_CLICK', 'x': x, 'y': y})
                else:
                    print("Usage: fake x y")

            elif parts[0] == 'click':
                if len(parts) == 3:
                    x, y = int(parts[1]), int(parts[2])
                    
                    # 1. Tell Frida to modify the in-game coordinates
                    script.post({'type': 'SET_MODE', 'mode': 'inject'})
                    script.post({'type': 'SIMULATE_CLICK', 'x': x, 'y': y})
                    
                    # 2. Wait a short while for the Hook to take effect.
                    time.sleep(0.02)
                    
                    # 3. Send physical click message
                    if not game_hwnd:
                        game_hwnd = get_window_handle(target_process)
                    send_click_message(game_hwnd, x, y)
                else:
                    print("Usage: click x y")
            
            elif parts[0] == 'hwnd':
                game_hwnd = get_window_handle(target_process)
                print(f"Current HWND: {game_hwnd}")

        except Exception as e:
            print(f"[!] Input Error: {e}")

    session.detach()

if __name__ == '__main__':
    main()