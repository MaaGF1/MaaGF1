import os
import json
import sys

# Configuration
JSON_PATH = "script.json"
IN_FILE = "src/offsets.h.in"
OUT_FILE = "src/offsets.h"

# Mapping: Placeholder -> { "sig": Exact C++ Signature, "val": Default Fallback Address }
TARGET_MAP = {
    "OFFSET_get_gameObject": {
        "sig": "UnityEngine_GameObject_o* UnityEngine_Component__get_gameObject (UnityEngine_Component_o* __this, const MethodInfo* method);",
        "val": 16465776
    },
    "OFFSET_SetActive": {
        "sig": "void UnityEngine_GameObject__SetActive (UnityEngine_GameObject_o* __this, bool value, const MethodInfo* method);",
        "val": 16488416
    },
    "OFFSET_Destroy": {
        "sig": "void UnityEngine_Object__Destroy (UnityEngine_Object_o* obj, const MethodInfo* method);",
        "val": 16599120
    },
    "OFFSET_InitGunInfo": {
        "sig": "void CommonGetNewGunController__InitGunInfo (CommonGetNewGunController_o* __this, GF_Battle_Gun_o* gun, System_Action_o* action, const MethodInfo* method);",
        "val": 5437312
    },
    "OFFSET_Spot_Show": {
        "sig": "void DeploymentSpotController__ShowTurnEndAnima (DeploymentSpotController_o* __this, const MethodInfo* method);",
        "val": 30831600
    },
    "OFFSET_Spot_Finish1": {
        "sig": "void DeploymentSpotController__OnFinishAnimation (DeploymentSpotController_o* __this, const MethodInfo* method);",
        "val": 30819680
    },
    "OFFSET_Spot_Finish2": {
        "sig": "void DeploymentSpotController__OnFinishAnimationEvent (DeploymentSpotController_o* __this, const MethodInfo* method);",
        "val": 30819312
    },
    "OFFSET_Turn_PlayEnd": {
        "sig": "void DeploymentTurnAnimationController__PlayChangeTurnEndAnime (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);",
        "val": 25400800
    },
    "OFFSET_Turn_ToGK": {
        "sig": "void DeploymentTurnAnimationController__ToGKTurn (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);",
        "val": 25401328
    },
    "OFFSET_Turn_ToSF": {
        "sig": "void DeploymentTurnAnimationController__ToSFTurn (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);",
        "val": 25402080
    },
    "OFFSET_Turn_Disact": {
        "sig": "void DeploymentTurnAnimationController__DisactiveMain (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);",
        "val": 25400320
    },
    "OFFSET_Turn_IsPlay": {
        "sig": "bool DeploymentTurnAnimationController__IsPlaying (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);",
        "val": 25400544
    },
    "OFFSET_MoveCamera": {
        "sig": "void DeploymentController__TriggerMoveCameraEvent (UnityEngine_Vector2_o target, bool move, float duration, float delay, bool recordPos, bool changescale, float setscale, System_Action_o* handle, const MethodInfo* method);",
        "val": 24073760
    }
}

def load_json_offsets():
    if not os.path.exists(JSON_PATH):
        print(f"[*] {JSON_PATH} not found. Using default fallback offsets.")
        return {}

    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[-] Failed to parse {JSON_PATH}: {e}. Using default fallback offsets.")
        return {}

    script_methods = data.get("ScriptMethod", [])
    found_map = {}

    for method in script_methods:
        json_sig = method.get("Signature", "")
        # Match EXACT signature to avoid overload ambiguity
        for ph_name, config in TARGET_MAP.items():
            if json_sig == config["sig"]:
                found_map[ph_name] = method.get("Address")
    
    return found_map

def main():
    print("[*] Generating offsets.h via gen_offset.py...")
    
    if not os.path.exists(IN_FILE):
        print(f"[-] Template file {IN_FILE} missing! Aborting generation.")
        sys.exit(1)

    json_offsets = load_json_offsets()
    
    # Read template
    with open(IN_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace placeholders
    for ph_name, config in TARGET_MAP.items():
        val = json_offsets.get(ph_name, config["val"])
        placeholder = f"@{ph_name}@"
        content = content.replace(placeholder, str(val))
        
        status = "JSON" if ph_name in json_offsets else "DEFAULT"
        print(f"    - {ph_name:<25} : {val} ({status})")

    # Write output
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[+] Successfully generated {OUT_FILE}")

if __name__ == "__main__":
    main()