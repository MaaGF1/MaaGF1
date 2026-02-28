// tools/hack/trimmer/frame/hook.js

var TARGET_FPS = 10; // Set a low FPS threshold (e.g., 10 or 15)

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hookFrameRate() {
    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) {
        send({ type: "error", payload: "GameAssembly.dll not found." });
        return;
    }

    send({ type: "info", payload: "[JS] Injecting Frame-Rate Limiter Hooks..." });

    // Address from script.json
    var addr_SetTargetFrameRate = gameAssembly.add(16416096); 
    
    // Create a callable native function
    var setTargetFrameRate = new NativeFunction(
        addr_SetTargetFrameRate, 
        'void', 
        ['int', 'pointer']
    );

    // 1. Attach to prevent the game from changing it back to 30/60
    Interceptor.attach(addr_SetTargetFrameRate, {
        onEnter: function(args) {
            var requestedFps = args[0].toInt32();
            
            // If the game tries to set an FPS higher than our target, override it
            if (requestedFps > TARGET_FPS || requestedFps === -1) {
                args[0] = ptr(TARGET_FPS);
                send({ 
                    type: "info", 
                    payload: "[JS] Blocked engine from setting FPS to " + requestedFps + ", forced to " + TARGET_FPS 
                });
            }
        }
    });

    // 2. Force apply our low FPS immediately
    try {
        setTargetFrameRate(TARGET_FPS, NULL);
        send({ type: "info", payload: "[JS] Initial Target FPS forced to " + TARGET_FPS });
    } catch (e) {
        send({ type: "error", payload: "[JS] Failed to force init FPS: " + e.message });
    }
}

setTimeout(hookFrameRate, 1000);