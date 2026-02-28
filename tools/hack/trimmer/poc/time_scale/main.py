# tools/hack/trimmer/ts/main.py

import frida
import sys
import os
import time
import threading

class UnitySpeedController:
    def __init__(self, process_name="GrilsFrontLine.exe"):
        self.process_name = process_name
        self.session = None
        self.script = None
        self.exit_event = threading.Event()

    def on_message(self, message, data):
        if message['type'] == 'send':
            payload = message.get('payload', {})
            msg_type = payload.get('type')
            msg_text = payload.get('payload')
            
            if msg_type == 'error':
                print(f"\n[Engine Error] {msg_text}")
            elif msg_type == 'info':
                pass # Silent internal infos unless needed
            else:
                print(f"\n[Engine Raw] {message}")
        else:
            print(f"\n[System] {message}")

    def attach_and_load(self, js_path="hook.js"):
        print(f"[*] Locating Process: {self.process_name} ...")
        
        for i in range(3):
            try:
                self.session = frida.attach(self.process_name)
                break
            except Exception as e:
                print(f"Retry {i+1} failed: {e}")
                time.sleep(1)
        
        if not self.session:
            print("[Error] Could not attach. Game not running or permission denied.")
            return False

        if not os.path.exists(js_path):
            print(f"[Error] Hook script missing: {js_path}")
            return False

        with open(js_path, "r", encoding="utf-8") as f:
            script_code = f.read()

        self.script = self.session.create_script(script_code)
        self.script.on('message', self.on_message)
        self.script.load()
        
        # Wait a moment for JS to initialize and replace memory
        time.sleep(1.5)
        return True

    def set_speed(self, speed):
        if not self.script:
            return False
        try:
            # Call the exported JS function via RPC
            success = self.script.exports.setspeed(float(speed))
            return success
        except Exception as e:
            print(f"[Error] RPC Call failed: {e}")
            return False

    def interactive_loop(self):
        print("\n" + "="*50)
        print("Unity Internal Engine Speedhack Console")
        print("Commands:")
        print("  q - Quit and safely detach")
        print("  s - Set new timescale multiplier")
        print("  r - Reset timescale to 1.0x")
        print("  i - Print current status")
        print("="*50)
        
        while not self.exit_event.is_set():
            try:
                user_input = input("\nCmd (q/s/r/i)> ").strip().lower()
                
                if user_input == 'q':
                    print("Exiting and resetting engine speed...")
                    self.set_speed(1.0)
                    self.exit_event.set()
                    break
                    
                elif user_input == 's':
                    try:
                        new_speed = float(input("Enter new multiplier (e.g., 3.0): "))
                        if new_speed >= 0:
                            if self.set_speed(new_speed):
                                print(f"-> Speed applied successfully: {new_speed}x")
                            else:
                                print("-> Failed to apply speed.")
                        else:
                            print("-> Speed must be positive.")
                    except ValueError:
                        print("-> Invalid number.")
                        
                elif user_input == 'r':
                    if self.set_speed(1.0):
                        print("-> Speed reset to normal (1.0x)")
                        
                elif user_input == 'i':
                    if self.script:
                        current = self.script.exports.getspeed()
                        print(f"-> Current Internal TimeScale: {current}x")
                        
            except (EOFError, KeyboardInterrupt):
                print("\nInterrupt received. Resetting and exiting...")
                self.set_speed(1.0)
                self.exit_event.set()
                break

    def cleanup(self):
        if self.session:
            self.session.detach()
        print("Detached safely.")

def main():
    controller = UnitySpeedController("GrilsFrontLine.exe")
    
    # Assuming script is run from the same directory as hook.js
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook.js")
    
    if controller.attach_and_load(js_path=script_path):
        # Default start at 3x speed for automation pipeline
        controller.set_speed(3.0)
        print("\n[*] Native Unity Engine Speedhack ACTIVE (Initial: 3.0x)")
        controller.interactive_loop()
        controller.cleanup()

if __name__ == "__main__":
    main()