import frida
import time
import os
import sys
from ipc import NamedPipeServer

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class LunaService:
    def __init__(self, target_process, pipe_name):
        self.target_process = target_process
        self.pipe_name = pipe_name
        self.server = None
        self.session = None
        self.global_script = None
        self.running = False
        self.script_path = get_resource_path("hook.js")

    def _on_frida_message(self, message, data):
        if message['type'] == 'send':
            payload = message['payload']
            if isinstance(payload, dict) and payload.get('type') == 'error':
                 print(f"[!] Hook Error: {payload.get('stack')}")
            else:
                 print(f"[*] Frida: {payload}")
        elif message['type'] == 'error':
            print(f"[!] Frida Error: {message['stack']}")

    def _pipe_handler(self, msg):
        if not self.global_script:
            return "ERR_NO_SCRIPT"

        try:
            parts = msg.split()
            if not parts:
                return "ERR_EMPTY"

            cmd = parts[0]
            if cmd == 'MOVE' and len(parts) == 3:
                x, y = int(parts[1]), int(parts[2])
                self.global_script.post({'type': 'UPDATE_POS', 'x': x, 'y': y})
                return "OK"
                
            elif cmd == 'WHEEL' and len(parts) >= 4:
                delta = int(parts[1])
                x = int(parts[2])
                y = int(parts[3])
                self.global_script.post({'type': 'UPDATE_POS', 'x': x, 'y': y})
                self.global_script.post({'type': 'SIMULATE_WHEEL', 'delta': delta})
                return "OK"

            else:
                return "ERR_INVALID_CMD"
        except Exception as e:
            print(f"[!] Handler Exception: {e}")
            return "ERR_EXCEPTION"

    def start(self):
        print(f"[*] Luna Service Starting...")
        print(f"[*] Target Process: {self.target_process}")
        
        self.server = NamedPipeServer(self.pipe_name, self._pipe_handler)
        self.server.start()

        self.running = True
        retry_count = 0
        
        while self.running:
            try:
                self.session = frida.attach(self.target_process)
                print(f"[+] Attached to {self.target_process}")
                break
            except Exception as e:
                retry_count += 1
                print(f"[.] Waiting for process... ({e})")
                time.sleep(2)
                if retry_count > 10:
                    print("[!] Process not found after retries.")
                    self.stop()
                    return False

        if not self.running:
            return False

        try:
            with open(self.script_path, "r", encoding="utf-8") as f:
                jscode = f.read()
                
            self.global_script = self.session.create_script(jscode)
            self.global_script.on('message', self._on_frida_message)
            self.global_script.load()
            print(f"[+] Hook loaded. Pipe '\\\\.\\pipe\\{self.pipe_name}' ready.")
            return True
        except Exception as e:
            print(f"[!] Error loading script: {e}")
            self.stop()
            return False

    def stop(self):
        print("[*] Stopping Luna Service...")
        self.running = False
        if self.server:
            self.server.stop()
        if self.session:
            try:
                self.session.detach()
            except Exception:
                pass
        self.global_script = None
        print("[*] Service Stopped.")