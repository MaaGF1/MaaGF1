import frida
import time
import ctypes

user32 = ctypes.windll.user32
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

class LunaInjector:
    def __init__(self, process_name, js_path):
        self.process_name = process_name
        self.js_path = js_path
        self.session = None
        self.script = None
        self.hwnd = None
        self.attached = False

    def attach(self):
        try:
            print(f"[*] Attaching to {self.process_name}...")
            self.session = frida.attach(self.process_name)
            with open(self.js_path, "r", encoding="utf-8") as f:
                jscode = f.read()
            self.script = self.session.create_script(jscode)
            self.script.on('message', self._on_frida_message)
            self.script.load()
            self.attached = True
            
            # Init HWND
            self.hwnd = self._find_window()
            if self.hwnd:
                print(f"[+] Found HWND: {hex(self.hwnd)}")
            else:
                print("[!] Warning: HWND not found yet.")
                
        except Exception as e:
            print(f"[!] Attach failed: {e}")
            self.attached = False

    def _find_window(self):
        # Simple finder, can be improved
        hwnd = user32.FindWindowW(None, "Girls' Frontline")
        if not hwnd:
            hwnd = user32.FindWindowW(None, "少女前线")
        if not hwnd:
             # Fallback: try to find by class name if known, or generic Unity
             hwnd = user32.FindWindowW("UnityWndClass", None)
        return hwnd

    def _on_frida_message(self, message, data):
        if message['type'] == 'send':
            # print(f"[Frida] {message['payload']}")
            pass
        elif message['type'] == 'error':
            print(f"[Frida Error] {message['stack']}")

    def detach(self):
        if self.session:
            self.session.detach()

    def handle_command(self, msg_type, x, y):
        if not self.attached:
            return

        # 1 = MOVE, 2 = DOWN, 3 = UP
        
        # Ensure HWND is valid
        if not self.hwnd:
            self.hwnd = self._find_window()
            if not self.hwnd: return

        lParam = (y << 16) | (x & 0xFFFF)

        if msg_type == 1: # MOVE
            # Just update fake coords
            self.script.post({'type': 'SIMULATE_CLICK', 'x': x, 'y': y})
            self.script.post({'type': 'SET_MODE', 'mode': 'inject'})

        elif msg_type == 2: # DOWN
            # Update fake coords
            self.script.post({'type': 'SIMULATE_CLICK', 'x': x, 'y': y})
            self.script.post({'type': 'SET_MODE', 'mode': 'inject'})
            
            # Wait for hook to sync (critical for Unity)
            # time.sleep(0.005) # 5ms is usually enough
            
            user32.PostMessageW(self.hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
            # print(f"[ACT] DOWN at {x},{y}")

        elif msg_type == 3: # UP
            # For UP, we don't strictly need to fake coords if we assume DOWN set them,
            # but keeping them consistent is safer.
            user32.PostMessageW(self.hwnd, WM_LBUTTONUP, 0, lParam)
            # Optional: Disable inject mode after UP to let user use mouse?
            # self.script.post({'type': 'SET_MODE', 'mode': 'monitor'})
            # print(f"[ACT] UP at {x},{y}")