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
    Radical optimization strategy 3.0: Ghost settlement + Map castration
    """
    trimmed = False
    
    # =======================================================
    # 1. Settlement interface optimization (Core to fix 2.5s ~ 3s lag)
    # =======================================================
    if "mission_win_result" in json_obj:
        win_result = json_obj["mission_win_result"]
        
        # [Key Optimization] Record and remove dropped T-Doll
        # This step prevents the client from loading the drop T-Doll sprite and playing the acquisition animation
        if "reward_gun" in win_result:
            print(f"[Python] [Record] Actual T-Doll obtained: {win_result['reward_gun']}")
            # Delete it! Make the client think there is no drop, thus skipping resource loading
            del win_result["reward_gun"] 
            trimmed = True
            print("[Python] Removed reward_gun field (Accelerate settlement animation)")

        # Remove client logs (Huge volume)
        if "mica_client_log" in win_result:
            del win_result["mica_client_log"]
            trimmed = True

        # [Optional] Remove MVP info or user_exp changes to prevent exp bar rolling animation
        # Note: Deleting user_exp might cause errors, suggest leaving it or setting to current value (no growth)
        # Here demonstrates removing MVP voice related fields (if any)

    # Delete logs in root node
    if "mica_client_log" in json_obj:
        del json_obj["mica_client_log"]
        trimmed = True

    # =======================================================
    # 2. Battle and Map optimization (Fix map lag)
    # =======================================================
    
    # Clear death statistics (Prevent playing death effects)
    if "died_this_section" in json_obj:
         # This is an object containing enemy and ally lists
        died = json_obj["died_this_section"]
        if died.get("enemy") or died.get("ally"):
            json_obj["died_this_section"] = {"enemy": [], "ally": []}
            trimmed = True
            print("[Python] Cleared died_this_section")

    # Deep clean spot_act_info (Keep structure, erase content)
    if "spot_act_info" in json_obj and isinstance(json_obj["spot_act_info"], list):
        if len(json_obj["spot_act_info"]) > 0:
            count = 0
            for item in json_obj["spot_act_info"]:
                # Zero out all unit IDs to prevent Prefab instantiation
                keys_to_zero = [
                    "enemy_team_id", "enemy_instance_id", "sangvis_team_id", 
                    "boss_hp", "hostage_id"
                ]
                for k in keys_to_zero:
                    if item.get(k, "0") != "0":
                        item[k] = "0"
                        count += 1
            
            if count > 0:
                print(f"[Python] Stripped {count} map unit attributes")
                trimmed = True

    # Brutally clear animation lists
    keys_to_empty_list = ["ally_battle", "enemy_move", "ally_move", "mission_lose_result"]
    for key in keys_to_empty_list:
        if json_obj.get(key): # If not empty
            json_obj[key] = []
            trimmed = True
            print(f"[Python] Cleared list: {key}")

    # Clear movement steps
    if json_obj.get("target_moved_step"):
        json_obj["target_moved_step"] = {}
        trimmed = True
        print("[Python] Cleared target_moved_step")

    return trimmed, json_obj

def on_message(message, data):
    # Retaining your dual-branch logic structure from previous code
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'req_modify':
            original_len = len(data)
            
            try:
                # 1. Decompress
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                json_obj = json.loads(json_str)
                
                # 2. Execute radical optimization
                is_modified, json_obj = trim_game_payload(json_obj)

                # 3. Individual value modifications (Incremental addition from original code)
                if "mission_win_result" in json_obj:
                    # Modify user_exp
                    old_exp = json_obj["mission_win_result"].get("user_exp", "N/A")
                    json_obj["mission_win_result"]["user_exp"] = "255"
                    print(f"[Python] Modified user_exp: {old_exp} -> 255")
                    is_modified = True

                if is_modified:
                    # 4. Reserialize (remove spaces to compress volume)
                    new_json_str = json.dumps(json_obj, separators=(',', ':'), ensure_ascii=False)
                    
                    # 5. Recompress (Level 1 for max speed, volume is already small enough)
                    new_gzip_data = gzip.compress(new_json_str.encode('utf-8'), compresslevel=1)
                    new_len = len(new_gzip_data)
                    
                    # print(f"[Python] Optimization complete: {original_len} -> {new_len} bytes")

                    # 6. Safety check
                    if new_len <= original_len:
                        script.post({'type': 'resp_modify', 'payload': 'modified'}, new_gzip_data)
                    else:
                        print(f"[Python] Warning: Modified size increased ({new_len} > {original_len}), aborting.")
                        script.post({'type': 'resp_modify', 'payload': 'original'})
                else:
                    script.post({'type': 'resp_modify', 'payload': 'original'})

            except Exception as e:
                print(f"[Python] Exception: {e}")
                # Must release thread on error
                script.post({'type': 'resp_modify', 'payload': 'original'})

def main():
    process_name = "GrilsFrontLine.exe" # Check spelling, Steam version might be "Girls Frontline.exe"
    print(f"[*] Attaching to process: {process_name} ...")
    
    # Simple retry mechanism
    session = None
    for i in range(3):
        try:
            session = frida.attach(process_name)
            break
        except Exception as e:
            print(f"Attempt {i+1}: Cannot attach ({e})")
            time.sleep(1)
    
    if not session:
        print("[Error] Attach failed, please ensure the game is running.")
        return

    if not os.path.exists("hook_mitm.js"):
        print("[Error] hook_mitm.js file not found")
        return

    with open("hook_mitm.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    global script
    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] Ghost settlement system started. Waiting for packets...")
    sys.stdin.read()

if __name__ == '__main__':
    main()