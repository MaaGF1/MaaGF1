// tools/hack/trimmer/turn_end/hook_mitm.js

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

setTimeout(hook, 1000);