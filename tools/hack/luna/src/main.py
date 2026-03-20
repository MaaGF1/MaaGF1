import frida
import sys
import time
import os
from ipc import NamedPipeServer

# Configuration
TARGET_PROCESS = "GrilsFrontLine.exe"
PIPE_NAME = "MaaLunaPipe"
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "hook.js")

global_script = None

def on_frida_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        if isinstance(payload, dict) and payload.get('type') == 'error':
             print(f"[!] Hook Error: {payload.get('stack')}")
        else:
             print(f"[*] Frida: {payload}")
    elif message['type'] == 'error':
        print(f"[!] Frida Error: {message['stack']}")

def pipe_handler(msg):
    """
    Protocol:
    "MOVE x y"       -> Returns "OK"
    "WHEEL delta x y" -> Returns "OK" (delta usually 120 or -120)
    """
    global global_script

    print(f"[IPC DEBUG] Received raw message: '{msg}'")

    if not global_script:
        print("[IPC DEBUG] Error: Global script is not loaded!")
        return "ERR_NO_SCRIPT"

    try:
        parts = msg.split()
        if not parts:
            return "ERR_EMPTY"

        cmd = parts[0]

        if cmd == 'MOVE' and len(parts) == 3:
            x, y = int(parts[1]), int(parts[2])
            # print(f"[IPC DEBUG] Processing MOVE: {x}, {y}")
            global_script.post({'type': 'UPDATE_POS', 'x': x, 'y': y})
            return "OK"
            
        elif cmd == 'WHEEL' and len(parts) >= 4:
            # Format: WHEEL delta x y
            delta = int(parts[1])
            x = int(parts[2])
            y = int(parts[3])
            
            print(f"[IPC DEBUG] Processing WHEEL >>> Delta: {delta}, Pos: ({x}, {y})")
            
            # Update pos first, then inject wheel
            global_script.post({'type': 'UPDATE_POS', 'x': x, 'y': y})
            global_script.post({'type': 'SIMULATE_WHEEL', 'delta': delta})
            return "OK"

        else:
            print(f"[IPC DEBUG] Warning: Unknown or invalid command format: {msg}")
            return "ERR_INVALID_CMD"

    except Exception as e:
        print(f"[!] Handler Exception: {e}")
        return "ERR_EXCEPTION"

def main():
    global global_script

    print(f"[*] Luna Service Starting...")
    print(f"[*] Target Process: {TARGET_PROCESS}")
    
    # 1. Start Pipe Server
    server = NamedPipeServer(PIPE_NAME, pipe_handler)
    server.start()

    # 2. Attach Frida
    session = None
    while True:
        try:
            session = frida.attach(TARGET_PROCESS)
            print(f"[+] Attached to {TARGET_PROCESS}")
            break
        except Exception as e:
            print(f"[.] Waiting for process... ({e})")
            time.sleep(2)

    try:
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            jscode = f.read()
            
        global_script = session.create_script(jscode)
        global_script.on('message', on_frida_message)
        global_script.load()
        print(f"[+] Hook loaded. Pipe '\\\\.\\pipe\\{PIPE_NAME}' ready.")
        
        # Keep main thread alive
        sys.stdin.read()

    except KeyboardInterrupt:
        print("[*] Stopping...")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        if session:
            session.detach()
        # Pipe server thread will die with process

if __name__ == '__main__':
    main()