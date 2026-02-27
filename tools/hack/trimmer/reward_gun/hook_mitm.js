// tools/hack/trimmer/reward_gun/hook_mitm.js

// --- Game Logic API ---
var addr_InitGunInfo    = 5437312;  // CommonGetNewGunController$$InitGunInfo

// --- Unity Engine API ---
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

setTimeout(hook, 1000);