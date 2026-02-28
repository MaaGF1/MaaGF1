import frida
import sys
import gzip
import os
import json
import time

# Configuration
OUTPUT_DIR = "traffic_dumps"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Global counter to keep files in order
packet_counter = 1

def save_json(content_obj, tag):
    """Helper to save JSON content to file"""
    global packet_counter
    
    timestamp = int(time.time())
    filename = f"{packet_counter:04d}_{tag}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content_obj, f, indent=4, ensure_ascii=False)
        print(f"[+] Saved: {filename}")
        packet_counter += 1
    except Exception as e:
        print(f"[!] Error saving file: {e}")

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        msg_id = payload.get('id')

        # --- Handle Server to Client (S2C) ---
        if msg_id == 'S2C':
            print(f"\n[<-- S2C] Received Gzip Data: {len(data)} bytes")
            try:
                # 1. Decompress
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                
                # 2. Parse and Save
                json_obj = json.loads(json_str)
                save_json(json_obj, "S2C")
                
            except Exception as e:
                print(f"[!] S2C Decompression/Parse Error: {e}")
                # Save raw if failed
                with open(os.path.join(OUTPUT_DIR, f"error_s2c_{packet_counter}.gz"), "wb") as f:
                    f.write(data)

        # --- Handle Client to Server (C2S) ---
        elif msg_id == 'C2S':
            content = payload.get('content')
            print(f"\n[--> C2S] Captured Request: {len(content)} chars")
            try:
                # 1. Parse (it is already a string)
                json_obj = json.loads(content)
                save_json(json_obj, "C2S")
                
            except Exception as e:
                print(f"[!] C2S Parse Error: {e}")
                print(f"[!] Raw Content: {content[:50]}...")

def main():
    process_name = "GrilsFrontLine.exe"
    
    print(f"[*] Attaching to process: {process_name} ...")
    try:
        session = frida.attach(process_name)
    except Exception as e:
        print(f"[!] Failed to attach: {e}")
        print("[!] Please ensure the game is running.")
        return

    # Load JS file
    if not os.path.exists("hook_dual.js"):
        print("[!] Error: hook_dual.js not found.")
        return

    with open("hook_dual.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] Script loaded. Monitoring traffic (S2C & C2S)...")
    print("[*] Press Ctrl+C to stop.")
    sys.stdin.read()

if __name__ == '__main__':
    main()