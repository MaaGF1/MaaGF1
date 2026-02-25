# tools/hack/reward_gun_trimmer/main.py

import frida
import sys
import gzip
import json
import os
import time

# ================= Configuration =================
OUTPUT_DIR = "debug_dumps"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
# =================================================

def save_dump(data, prefix, tag=""):
    """Helper function: Save binary data to file"""
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{prefix}{tag}.gz"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(data)
    return filename

def trim_game_payload(json_obj):
    """
    Reverted map/movement modifications to prevent game freeze.
    """
    trimmed = False
    
    # Ensure root is a dict
    if not isinstance(json_obj, dict):
        return False, json_obj

    # =======================================================
    # Target 1: Settlement Animation
    # =======================================================
    if "mission_win_result" in json_obj:
        win_result = json_obj["mission_win_result"]
        if isinstance(win_result, dict):
            # 1. Remove T-Doll Drop (Prevents loading sprites/playing animation)
            if "reward_gun" in win_result:
                print(f"[Python] [Record] Drop: {win_result['reward_gun']}")
                del win_result["reward_gun"] 
                trimmed = True
                print("[Python] Removed reward_gun (Fast Settle)")

            # 2. Remove Logs inside result
            if "mica_client_log" in win_result:
                del win_result["mica_client_log"]
                trimmed = True
    
    # =======================================================
    # Target 2: Payload Size Reduction
    # =======================================================
    
    # 1. Remove Root Logs
    if "mica_client_log" in json_obj:
        del json_obj["mica_client_log"]
        trimmed = True

    # 2. Remove Death Stats
    if "died_this_section" in json_obj:
        died = json_obj["died_this_section"]
        if isinstance(died, dict):
            if died.get("enemy") or died.get("ally"):
                json_obj["died_this_section"] = {"enemy": [], "ally": []}
                trimmed = True
                print("[Python] Cleared died_this_section")

    # 3. Remove Protocol Overhead Fields
    keys_to_delete = ["mission_control", "building_info", "mission_lose_result"]
    for key in keys_to_delete:
        if key in json_obj:
            del json_obj[key]
            trimmed = True

    # =======================================================
    # Warning: Map & Movement
    # Reasons: Caused game logic freeze / infinite wait.
    # DO NOT modify 'spot_act_info', 'target_moved_step', etc.
    # =======================================================

    return trimmed, json_obj

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'req_modify':
            original_len = len(data)
            
            try:
                # 1. Decompress
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                json_obj = json.loads(json_str)
                
                # 2. Execute Optimization
                is_modified, json_obj = trim_game_payload(json_obj)

                if is_modified:
                    # 3. Reserialize (Compact)
                    new_json_str = json.dumps(json_obj, separators=(',', ':'), ensure_ascii=False)
                    
                    # 4. Recompress
                    # Level 6 is balanced for speed/size. 
                    # Ensure size < original to pass memory write check.
                    new_gzip_data = gzip.compress(new_json_str.encode('utf-8'), compresslevel=6)
                    new_len = len(new_gzip_data)
                    
                    # 5. Safety Check
                    if new_len <= original_len:
                        # print(f"[Python] Optimized: {original_len} -> {new_len} bytes")
                        script.post({'type': 'resp_modify', 'payload': 'modified'}, new_gzip_data)
                    else:
                        print(f"[Python] Warning: Size increased ({new_len} > {original_len}). Skipped.")
                        script.post({'type': 'resp_modify', 'payload': 'original'})
                else:
                    # Nothing to trim, just pass through
                    script.post({'type': 'resp_modify', 'payload': 'original'})

            except Exception as e:
                print(f"[Python] Critical Error: {e}")
                # Don't crash the script, keep running
                script.post({'type': 'resp_modify', 'payload': 'original'})

def main():
    # Note: Grils for Steam, Girls for Epic
    process_name = "GrilsFrontLine.exe" 
    print(f"[*] Attaching to process: {process_name} ...")
    
    session = None
    for i in range(3):
        try:
            session = frida.attach(process_name)
            break
        except Exception as e:
            print(f"Retry {i+1}: {e}")
            time.sleep(1)
    
    if not session:
        print("[Error] Attach failed.")
        return

    if not os.path.exists("hook_mitm.js"):
        print("[Error] hook_mitm.js missing")
        return

    with open("hook_mitm.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    global script
    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] Settlement Accelerator Running (Map Logic Preserved)...")
    sys.stdin.read()

if __name__ == '__main__':
    main()