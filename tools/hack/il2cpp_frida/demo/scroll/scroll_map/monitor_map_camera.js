// monitor_map_camera.js

// --- Addresses (Decimal) ---
var addr_set_orthographicSize = 16452928; // UnityEngine.Camera$$set_orthographicSize
var addr_set_fieldOfView = 16451536;      // UnityEngine.Camera$$set_fieldOfView
var addr_get_name = 16605904;             // UnityEngine.Object$$get_name

// --- Helpers ---
function readIl2CppString(ptr) {
    if (ptr.isNull()) return "(null)";
    try {
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) { return "(error)"; }
}

function setup_camera_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found, retrying...");
        setTimeout(setup_camera_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_orthographicSize = base.add(addr_set_orthographicSize);
    var ptr_set_fieldOfView = base.add(addr_set_fieldOfView);
    var ptr_get_name = base.add(addr_get_name);

    // 定义 get_name 用于获取对象名称
    // String get_name(Object* this, MethodInfo* method)
    var native_get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] Map Camera Monitor Attached. Try zooming the map now...");

    // =========================================================
    // 1. Monitor set_orthographicSize (2D Zoom - 最可能的)
    // =========================================================
    // void set_orthographicSize(Camera* this, float value, MethodInfo* method)
    
    var native_set_ortho = new NativeFunction(ptr_set_orthographicSize, 'void', ['pointer', 'float', 'pointer']);

    Interceptor.replace(ptr_set_orthographicSize, new NativeCallback(function(camPtr, size, method) {
        
        // 1. 获取名字
        var namePtr = native_get_name(camPtr, NULL);
        var name = readIl2CppString(namePtr);

        // 2. 打印日志
        // 过滤：为了防止某些初始化逻辑刷屏，你可以只关注特定的名字
        // 但第一次运行建议全部打印
        console.log(`[Camera 2D] set_orthographicSize called!`);
        console.log(`    -> Object: "${name}"`);
        console.log(`    -> Value:  ${size}`);
        
        // 3. 执行原函数
        native_set_ortho(camPtr, size, method);

    }, 'void', ['pointer', 'float', 'pointer']));


    // =========================================================
    // 2. Monitor set_fieldOfView (3D Zoom - 备选)
    // =========================================================
    
    var native_set_fov = new NativeFunction(ptr_set_fieldOfView, 'void', ['pointer', 'float', 'pointer']);

    Interceptor.replace(ptr_set_fieldOfView, new NativeCallback(function(camPtr, fov, method) {
        
        var namePtr = native_get_name(camPtr, NULL);
        var name = readIl2CppString(namePtr);

        console.log(`[Camera 3D] set_fieldOfView called!`);
        console.log(`    -> Object: "${name}"`);
        console.log(`    -> Value:  ${fov}`);
        
        native_set_fov(camPtr, fov, method);

    }, 'void', ['pointer', 'float', 'pointer']));
}

setup_camera_monitor();