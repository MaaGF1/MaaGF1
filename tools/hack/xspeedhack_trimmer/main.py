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
    Strategy 2.0: Keep data structure, clean high-load fields
    """
    trimmed = False
    
    # === 1. Safe delete: Logs and plain text info ===
    # These usually do not involve logic state transitions
    keys_to_delete = ["mica_client_log", "died_this_section", "mission_control"]
    
    # Recursively find and delete mica_client_log (might be in root or win_result)
    if "mica_client_log" in json_obj:
        del json_obj["mica_client_log"]
        trimmed = True
        
    if "mission_win_result" in json_obj and isinstance(json_obj["mission_win_result"], dict):
        if "mica_client_log" in json_obj["mission_win_result"]:
            del json_obj["mission_win_result"]["mica_client_log"]
            trimmed = True

    # === 2. Deep clean spot_act_info (Key to fix freezing issues) ===
    # Do not delete the list! Iterate and set "enemy_team_id" etc. to "0"
    if "spot_act_info" in json_obj and isinstance(json_obj["spot_act_info"], list):
        # Only process if list is not empty, avoid meaningless iteration
        if len(json_obj["spot_act_info"]) > 0:
            print(f"[Python] Cleaning spot_act_info (Items: {len(json_obj['spot_act_info'])})")
            
            for item in json_obj["spot_act_info"]:
                # Must keep: spot_id, belong, seed
                # These fields are usually for map logic positioning, changing them easily causes Crash
                
                # === Erase enemies ===
                # Change enemy ID to 0 or empty string, game won't load hundreds of MBs of sprites and models
                if "enemy_team_id" in item and item["enemy_team_id"] != "0":
                    item["enemy_team_id"] = "0"
                    trimmed = True
                
                if "enemy_instance_id" in item and item["enemy_instance_id"] != "0":
                    item["enemy_instance_id"] = "0"
                    trimmed = True
                
                if "sangvis_team_id" in item and item["sangvis_team_id"] != "0": # Sangvis units
                    item["sangvis_team_id"] = "0"
                    trimmed = True
                
                # === Erase Boss info ===
                if "boss_hp" in item and item["boss_hp"] != "0":
                    item["boss_hp"] = "0"
                    trimmed = True
                
                # === Erase hostages ===
                if "hostage_id" in item and item["hostage_id"] != "0":
                    item["hostage_id"] = "0"
                    trimmed = True
                
                # === Critical: If this is an ally echelon, should we keep it? ===
                # Suggestion: Keep squad_instance_ids, because camera might need to focus on ally echelon.
                # If deleted, camera might point to the void causing logic errors.
                # pass 
                
            print("[Python] spot_act_info clean complete")

    # === 3. Clear animation related lists ===
    # These are usually action commands, if enemy IDs above are 0,
    # battle and move commands here can likely be safely cleared.
    # If game freezes after clearing, it means game is waiting for command execution callback.
    # Strategy: Try clearing first, if it freezes, keep structure but change content to empty steps.
    
    # Try to clear battle replays (Huge time consumer)
    if "ally_battle" in json_obj and json_obj["ally_battle"]:
        json_obj["ally_battle"] = []
        trimmed = True
        print("[Python] Cleared ally_battle")
        
    # Try to clear enemy movement (Since enemy IDs are gone, movement is meaningless)
    if "enemy_move" in json_obj and json_obj["enemy_move"]:
        json_obj["enemy_move"] = []
        trimmed = True
        print("[Python] Cleared enemy_move")

    # === 4. Process target_moved_step (File 0002) ===
    # This is a nested dict describing movement steps.
    # Suggestion: empty it directly, let client think "no movement needed"
    if "target_moved_step" in json_obj:
        # If it is not empty
        if json_obj["target_moved_step"]: 
            # Strategy A: Directly provide empty dict
            json_obj["target_moved_step"] = {}
            trimmed = True
            print("[Python] Cleared target_moved_step")
            
            # Strategy B (if A freezes): Keep Key, empty Value (more complex, try A first)

    return trimmed, json_obj
    """
    Core trimming logic: Delete unimportant, time-consuming lists and logs
    """
    trimmed = False
    
    # === 1. Delete client logs (useless and huge) ===
    # Appears inside mission_win_result or root node
    if "mica_client_log" in json_obj:
        del json_obj["mica_client_log"]
        trimmed = True

    if "mission_win_result" in json_obj and isinstance(json_obj["mission_win_result"], dict):
        if "mica_client_log" in json_obj["mission_win_result"]:
            del json_obj["mission_win_result"]["mica_client_log"]
            trimmed = True
            print("[Python] Deleted mica_client_log from mission_win_result")

    # === 2. Remove map unit instantiation data (Huge time consumer) ===
    # spot_act_info contains detailed info of nodes and enemies.
    # If in settlement phase, or just for fast clearing, emptying this list will clear the map, stopping instantiation lag.
    if "spot_act_info" in json_obj and isinstance(json_obj["spot_act_info"], list):
        if len(json_obj["spot_act_info"]) > 0:
            print(f"[Python] Cleared spot_act_info (Original length: {len(json_obj['spot_act_info'])})")
            json_obj["spot_act_info"] = [] 
            trimmed = True

    # === 3. Remove movement and battle animation data ===
    # These fields control enemy movement steps and battle replays
    keys_to_purge = [
        "enemy_move",           # Enemy movement trajectory
        "ally_move",            # Ally movement trajectory
        "ally_battle",          # Battle events
        "target_moved_step",    # Target movement steps (Large in File 0002)
        "died_this_section"     # Death statistics
    ]

    for key in keys_to_purge:
        if key in json_obj:
            # If it's a list or dict and not empty, then clear it
            if (isinstance(json_obj[key], list) and len(json_obj[key]) > 0) or \
               (isinstance(json_obj[key], dict) and len(json_obj[key]) > 0):
                print(f"[Python] Cleared {key}")
                # Maintain type consistency, give empty dict if originally dict, empty list if originally list
                json_obj[key] = type(json_obj[key])() 
                trimmed = True

    return trimmed, json_obj

def on_message(message, data):
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'req_modify':
            original_len = len(data)
            # print(f"\n[Python] Captured packet, original size: {original_len} bytes")
            
            try:
                # 1. Decompress
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                json_obj = json.loads(json_str)
                
                is_modified = False
                
                # 2. Execute trim (Traffic Shaping)
                is_trimmed, json_obj = trim_game_payload(json_obj)
                if is_trimmed:
                    is_modified = True

                # 3. Execute your value modifications (Keeping your previous logic)
                if "mission_win_result" in json_obj:
                    # You can save obtained gun info to MaaGlobalContext here
                    if "reward_gun" in json_obj["mission_win_result"]:
                        print(f"[Python] Got T-Doll: {json_obj['mission_win_result']['reward_gun']}")
                    
                    # Modify experience points etc.
                    # json_obj["mission_win_result"]["user_exp"] = "255"
                    # is_modified = True
                    pass

                if is_modified:
                    # 4. Reserialize (remove spaces with separators to further reduce size)
                    new_json_str = json.dumps(json_obj, separators=(',', ':'), ensure_ascii=False)
                    
                    # 5. Recompress
                    new_gzip_data = gzip.compress(new_json_str.encode('utf-8'), compresslevel=9)
                    new_len = len(new_gzip_data)
                    
                    print(f"[Python] Rebuild complete: {original_len} -> {new_len} bytes (Reduced by {original_len - new_len} bytes)")

                    # 6. Safety check: Absolutely cannot exceed original Buffer size
                    if new_len <= original_len:
                        script.post({
                            'type': 'resp_modify',
                            'payload': 'modified'
                        }, new_gzip_data)
                    else:
                        print(f"[Python] Warning: Size increased after trimming (possibly due to compression dict reset), aborting.")
                        script.post({'type': 'resp_modify', 'payload': 'original'})
                else:
                    # No modification needed, notify JS to continue
                    script.post({'type': 'resp_modify', 'payload': 'original'})

            except Exception as e:
                print(f"[Python] Exception: {e}")
                # Must let it pass when error occurs, otherwise game will freeze
                script.post({'type': 'resp_modify', 'payload': 'original'})
                
    if message['type'] == 'send':
        payload = message['payload']
        
        if payload.get('id') == 'req_modify':
            original_len = len(data)
            print(f"\n[Python] Captured packet, original size: {original_len} bytes")
            
            # 1. Dump original packet first, in case analysis is needed
            # save_dump(data, "original")

            try:
                # 2. Decompress
                decompressed_data = gzip.decompress(data)
                json_str = decompressed_data.decode('utf-8')
                json_obj = json.loads(json_str)
                
                modified = False
                
                # 3. Type check: Ensure it is a dictionary structure
                if isinstance(json_obj, dict):
                    
                    # Check if it contains settlement info
                    if "mission_win_result" in json_obj:
                        print("[Python] Target hit: mission_win_result")
                        
                        win_result = json_obj["mission_win_result"]
                        
                        # === Modify values ===
                        old_exp = win_result.get("user_exp", "N/A")
                        win_result["user_exp"] = "255"
                        print(f"[Python] Modifying user_exp: {old_exp} -> 255")
                        
                        # === [Critical] Delete junk data to free up space ===
                        # mica_client_log usually contains a lot of stats, deleting it is safe and reduces size significantly
                        if "mica_client_log" in win_result:
                            print("[Python] Deleting mica_client_log to reduce size...")
                            del win_result["mica_client_log"]
                        
                        modified = True
                    else:
                        print("[Python] Not a settlement packet, skipping.")
                else:
                    print(f"[Python] Data structure is {type(json_obj)}, skipping.")

                if modified:
                    # 4. Reserialize (remove spaces)
                    new_json_str = json.dumps(json_obj, separators=(',', ':'), ensure_ascii=False)
                    
                    # 5. Recompress (Level 9 highest compression rate)
                    new_gzip_data = gzip.compress(new_json_str.encode('utf-8'), compresslevel=9)
                    new_len = len(new_gzip_data)
                    
                    print(f"[Python] Recompressing: {original_len} -> {new_len} bytes")

                    # 6. Final size check
                    if new_len <= original_len:
                        print(f"[Python] Size check passed (Remaining space: {original_len - new_len} bytes)")
                        
                        # Save modified packet for inspection
                        # save_dump(new_gzip_data, "modified", "_SUCCESS")
                        
                        script.post({
                            'type': 'resp_modify',
                            'payload': 'modified'
                        }, new_gzip_data)
                    else:
                        print(f"[Python] Warning: Modified size ({new_len}) still larger than original ({original_len})!")
                        print("[Python] Aborting send to prevent game crash. Suggest finding more fields to delete.")
                        # save_dump(new_gzip_data, "modified", "_TOO_LARGE")
                        script.post({'type': 'resp_modify', 'payload': 'original'})
                    
                else:
                    script.post({'type': 'resp_modify', 'payload': 'original'})

            except Exception as e:
                print(f"[Python] Processing Exception: {e}")
                import traceback
                traceback.print_exc()
                script.post({'type': 'resp_modify', 'payload': 'original'})

def main():
    process_name = "GrilsFrontLine.exe"
    print(f"[*] Attaching to process: {process_name} ...")
    try:
        session = frida.attach(process_name)
    except Exception as e:
        print(f"Failed to attach: {e}")
        return

    # Read previous JS file (hook_mitm.js)
    if not os.path.exists("hook_mitm.js"):
        print("Error: hook_mitm.js not found")
        return

    with open("hook_mitm.js", "r", encoding="utf-8") as f:
        script_code = f.read()

    global script
    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    
    print("[*] Script loaded, data processing active...")
    sys.stdin.read()

if __name__ == '__main__':
    main()