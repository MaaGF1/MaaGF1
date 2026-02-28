// tools/hack/trimmer/ts/hook.js

var TARGET_SPEED = 1.0;
var IS_ENABLED = false;

var gameAssembly = null;
var originalSetTimeScale = null;

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function initEngineSpeedhack() {
    gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) {
        send({ type: "error", payload: "GameAssembly.dll not found." });
        return false;
    }

    // Addresses from script.json
    var addr_SetTimeScale = gameAssembly.add(17581328); 
    
    // Create callable native function
    originalSetTimeScale = new NativeFunction(addr_SetTimeScale, 'void', ['float', 'pointer']);

    // Replace the function to prevent the game from resetting our speed back to 1.0
    // e.g., when entering/exiting combat, games often call Time.timeScale = 1.0f
    Interceptor.replace(addr_SetTimeScale, new NativeCallback(function(value, method) {
        if (IS_ENABLED) {
            // If the game tries to pause (0.0), we allow it to avoid breaking UI logic
            if (value === 0.0) {
                originalSetTimeScale(0.0, method);
            } 
            // If the game tries to set it to 1.0 (normal), we override it with our target
            else if (value === 1.0) {
                originalSetTimeScale(TARGET_SPEED, method);
            }
            // Other dynamic timescale changes (like bullet time) can be scaled or passed
            else {
                originalSetTimeScale(value * TARGET_SPEED, method);
            }
        } else {
            originalSetTimeScale(value, method);
        }
    }, 'void', ['float', 'pointer']));

    send({ type: "info", payload: "[JS] Unity Engine TimeScale Hijacked Successfully." });
    return true;
}

// Export RPC methods for Python to call
rpc.exports = {
    setspeed: function(speed) {
        if (!originalSetTimeScale) return false;
        
        TARGET_SPEED = speed;
        IS_ENABLED = (speed !== 1.0);
        
        try {
            // Force apply the new speed immediately
            originalSetTimeScale(TARGET_SPEED, NULL);
            send({ type: "info", payload: "[JS] Applied Engine TimeScale: " + TARGET_SPEED + "x" });
            return true;
        } catch (e) {
            send({ type: "error", payload: "[JS] Failed to apply TimeScale: " + e.message });
            return false;
        }
    },
    getspeed: function() {
        return TARGET_SPEED;
    }
};

setTimeout(initEngineSpeedhack, 1000);