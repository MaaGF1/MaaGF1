// tools/hack/trimmer/merged/hook_mitm.js

// =============================================================
// GLOBAL HELPER & DEFINITIONS (From Reward Gun Logic)
// =============================================================

// --- Game Logic API (Reward Gun) ---
var addr_InitGunInfo    = 5437312;  // CommonGetNewGunController$$InitGunInfo

// --- Unity Engine API (Reward Gun) ---
var addr_get_gameObject = 16465776; // UnityEngine.Component$$get_gameObject
var addr_SetActive      = 16488416; // UnityEngine.GameObject$$SetActive
var addr_Destroy        = 16599120; // UnityEngine.Object$$Destroy

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) {
        send({ type: "error", payload: "GameAssembly.dll not found." });
        return;
    }

    // Helper definition for compatibility with Script B code style
    var NULL = ptr(0);

    send({ type: "info", payload: "[JS] Injecting MERGED Hooks (Reward Gun + Turn End)..." });

    // =============================================================
    // PART 1: REWARD GUN HOOK (Zero-Frame UI Annihilator)
    // =============================================================
    {
        // Binding function pointers
        var ptr_InitGunInfo    = gameAssembly.add(addr_InitGunInfo);
        var ptr_get_gameObject = gameAssembly.add(addr_get_gameObject);
        var ptr_SetActive      = gameAssembly.add(addr_SetActive);
        var ptr_Destroy        = gameAssembly.add(addr_Destroy);

        // Declare Unity NativeFunction
        var get_gameObject = new NativeFunction(ptr_get_gameObject, 'pointer', ['pointer', 'pointer']);
        // In Frida NativeFunction, bool is usually represented by uint8 (0=false, 1=true)
        var SetActive      = new NativeFunction(ptr_SetActive, 'void', ['pointer', 'uint8', 'pointer']);
        var Destroy        = new NativeFunction(ptr_Destroy, 'void', ['pointer', 'pointer']);

        send({ type: "info", payload: "[JS] Injecting Engine-Level Annihilation Hook..." });

        // Replace InitGunInfo
        Interceptor.replace(ptr_InitGunInfo, new NativeCallback(function(__this, gun, action, method) {
            send({ type: "info", payload: "[JS] >> UI Initialization Intercepted!" });

            // Step 1: Forge a "Animation finished playing" completion signal to the Lua queue manager
            if (!action.isNull()) {
                try {
                    var invoke_impl = action.add(0x18).readPointer();
                    var target      = action.add(0x20).readPointer();
                    var actionInvoke = new NativeFunction(invoke_impl, 'void', ['pointer']);
                    actionInvoke(target);
                    send({ type: "info", payload: "[JS] Faked Callback Invoke sent to Lua Event Queue." });
                } catch (e) {
                    send({ type: "error", payload: "[JS] Callback invoke failed: " + e.message });
                }
            }

            // Step 2: Directly manipulate the Unity engine to eliminate Nodata placeholders.
            try {
                // 1. Get the GameObject entity attached to the Controller (Component)
                var gameObject = get_gameObject(__this, ptr(0));
                
                if (!gameObject.isNull()) {
                    // 2. Make it invisible
                    SetActive(gameObject, 0, ptr(0));
                    
                    // 3. Add it to Unity's GC queue
                    Destroy(gameObject, ptr(0));
                    
                    send({ type: "info", payload: "[JS] << 'Nodata' GameObject vaporized via UnityEngine API." });
                }
            } catch (e) {
                send({ type: "error", payload: "[JS] Engine wipe failed: " + e.message });
            }

        }, 'void', ['pointer', 'pointer', 'pointer', 'pointer']));

        send({ type: "info", payload: "[JS] Zero-Frame UI Annihilator is ACTIVE." });
    }

    // =============================================================
    // PART 2: TURN END HOOK (State-Machine Fast-Forward)
    // =============================================================
    {
        send({ type: "info", payload: "[JS] Injecting State-Machine Fast-Forward Hooks..." });

        // ==========================================
        // Module I : Spot Animation
        // ==========================================
        var addr_Spot_Show   = gameAssembly.add(30831600); // DeploymentSpotController$$ShowTurnEndAnima
        var addr_Spot_Finish1 = gameAssembly.add(30819680); // DeploymentSpotController$$OnFinishAnimation
        var addr_Spot_Finish2 = gameAssembly.add(30819312); // DeploymentSpotController$$OnFinishAnimationEvent
        
        var spotFinish1 = new NativeFunction(addr_Spot_Finish1, 'void', ['pointer', 'pointer']);
        var spotFinish2 = new NativeFunction(addr_Spot_Finish2, 'void', ['pointer', 'pointer']);

        Interceptor.replace(addr_Spot_Show, new NativeCallback(function(__this, method) {
            // Triggering the animation end event instantly, deceiving the state machine
            try {
                spotFinish2(__this, NULL);
                spotFinish1(__this, NULL);
                send({ type: "info", payload: "[JS] Spot Animation skipped & Finish Event faked." });
            } catch (e) {
                send({ type: "error", payload: "[JS] Spot Finish fake failed: " + e.message });
            }
        }, 'void', ['pointer', 'pointer']));


        // ==========================================
        // Module II : Turn Animation
        // ==========================================
        var addr_Turn_PlayEnd = gameAssembly.add(25400800); // DeploymentTurnAnimationController$$PlayChangeTurnEndAnime
        var addr_Turn_ToGK    = gameAssembly.add(25401328); // DeploymentTurnAnimationController$$ToGKTurn
        var addr_Turn_ToSF    = gameAssembly.add(25402080); // DeploymentTurnAnimationController$$ToSFTurn
        var addr_Turn_Disact  = gameAssembly.add(25400320); // DeploymentTurnAnimationController$$DisactiveMain
        var addr_Turn_IsPlay  = gameAssembly.add(25400544); // DeploymentTurnAnimationController$$IsPlaying

        var turnDisactive = new NativeFunction(addr_Turn_Disact, 'void', ['pointer', 'pointer']);

        // IsPlaying always return false (0) to avoid state machine polling stuck
        try {
            Memory.protect(addr_Turn_IsPlay, 3, 'rwx');
            addr_Turn_IsPlay.writeByteArray([0x31, 0xC0, 0xC3]); // xor eax, eax; ret
        } catch (e) {}

        // Hijack callback：stop playback, and DisactiveMain is called instantly
        var turnAnimFastForward = new NativeCallback(function(__this, method) {
            try {
                turnDisactive(__this, NULL);
                send({ type: "info", payload: "[JS] Turn Animation fast-forwarded to DisactiveMain." });
            } catch (e) {
                send({ type: "error", payload: "[JS] Turn fast-forward failed: " + e.message });
            }
        }, 'void', ['pointer', 'pointer']);

        // Replace all entry points that may trigger the large text animation
        Interceptor.replace(addr_Turn_PlayEnd, turnAnimFastForward);
        Interceptor.replace(addr_Turn_ToGK, turnAnimFastForward);
        Interceptor.replace(addr_Turn_ToSF, turnAnimFastForward);


        // ==========================================
        // Module III : Zero-Duration Camera
        // ==========================================
        var addr_MoveCamera = gameAssembly.add(24073760); // DeploymentController$$TriggerMoveCameraEvent
        var original_MoveCamera = new NativeFunction(addr_MoveCamera, 'void', 
            ['pointer', 'uint64', 'uint8', 'float', 'float', 'uint8', 'uint8', 'float', 'pointer', 'pointer']);

        var moveCamCallback = new NativeCallback(function(__this, target, move, duration, delay, recordPos, changescale, setscale, handle, method) {
            try {
                // duration (0.0), delay (0.0)
                original_MoveCamera(__this, target, move, 0.0, 0.0, recordPos, changescale, setscale, handle, method);
            } catch (e) {}
        }, 'void', ['pointer', 'uint64', 'uint8', 'float', 'float', 'uint8', 'uint8', 'float', 'pointer', 'pointer']);
        
        Interceptor.replace(addr_MoveCamera, moveCamCallback);

        send({ type: "info", payload: "[JS] State-Machine Fast-Forward is ACTIVE." });
    }
}

setTimeout(hook, 1000);