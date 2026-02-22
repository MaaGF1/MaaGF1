// monitor_cinemachine.js

// --- Addresses (Decimal) ---
var addr_OnPositionDragged = 44197808; // CinemachineVirtualCamera.OnPositionDragged
var addr_AdjustCamera = 12290800;      // CinemachineFramingTransposer.AdjustCameraDepthAndLensForGroupFraming
var addr_MutateCameraState = 12293616; // CinemachineFramingTransposer.MutateCameraState
var addr_get_gameObject = 16465776;    // Component.get_gameObject
var addr_get_name = 16605904;          // Object.get_name

// --- Helpers ---
function readIl2CppString(ptr) {
    if (ptr.isNull()) return "null";
    try {
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) { return "error"; }
}

var nameCache = {};

function getVirtualCameraName(vcamPtr) {
    var key = vcamPtr.toString();
    if (nameCache[key]) return nameCache[key];
    try {
        var get_go = new NativeFunction(ptr_get_gameObject, 'pointer', ['pointer', 'pointer']);
        var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);
        var go = get_go(vcamPtr, NULL);
        var namePtr = get_name(go, NULL);
        var name = readIl2CppString(namePtr);
        nameCache[key] = name;
        return name;
    } catch(e) {
        return "Unknown_VCam";
    }
}

var ptr_get_gameObject, ptr_get_name;

function setup_cinemachine_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_cinemachine_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    ptr_get_gameObject = base.add(addr_get_gameObject);
    ptr_get_name = base.add(addr_get_name);

    console.log("[*] Cinemachine Monitor Attached!");
    console.log("[*] Please DRAG and ZOOM the Campaign/SLG Map now...");

    // ========================================================================
    // 1. 监听拖拽事件 (OnPositionDragged)
    // ========================================================================
    // void OnPositionDragged(CinemachineVirtualCamera* this, Vector3 delta, MethodInfo*)
    Interceptor.attach(base.add(addr_OnPositionDragged), {
        onEnter: function(args) {
            var vcamPtr = args[0];
            var deltaPtr = args[1]; // Vector3*
            
            var name = getVirtualCameraName(vcamPtr);
            
            var dx = deltaPtr.readFloat();
            var dy = deltaPtr.add(4).readFloat();
            var dz = deltaPtr.add(8).readFloat();
            
            console.log(`[Cinemachine Drag] VCam: "${name}" -> Delta: (${dx.toFixed(2)}, ${dy.toFixed(2)}, ${dz.toFixed(2)})`);
        }
    });

    // ========================================================================
    // 2. 监听动态缩放调整 (AdjustCameraDepthAndLensForGroupFraming)
    // ========================================================================
    // 通常用于自动缩放以包含多个目标，有时也会被手动缩放逻辑复用
    var lastAdjustTime = 0;
    Interceptor.attach(base.add(addr_AdjustCamera), {
        onEnter: function(args) {
            var now = Date.now();
            if (now - lastAdjustTime > 500) { // 防止刷屏
                console.log(`[Cinemachine Zoom] AdjustCameraDepthAndLens triggered!`);
                lastAdjustTime = now;
            }
        }
    });

    // ========================================================================
    // 3. 监听状态突变 (心跳包：证明 Cinemachine 正在控制画面)
    // ========================================================================
    var lastMutateTime = 0;
    Interceptor.attach(base.add(addr_MutateCameraState), {
        onEnter: function(args) {
            var now = Date.now();
            if (now - lastMutateTime > 3000) { 
                console.log(`[Cinemachine Active] Transposer is mutating camera state (Heartbeat)`);
                lastMutateTime = now;
            }
        }
    });
}

setup_cinemachine_monitor();