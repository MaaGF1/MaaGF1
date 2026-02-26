// monitor_map_final.js

// --- Addresses (Decimal) ---
var addr_set_fieldOfView = 16451536;      // Camera.set_fieldOfView
var addr_set_orthographicSize = 16452928; // Camera.set_orthographicSize (保留它，以防万一)
var addr_set_localPosition_Inj = 17600768;// Transform.set_localPosition_Injected
var addr_get_name = 16605904;             // Object.get_name

// --- Helpers ---
function readIl2CppString(ptr) {
    if (ptr.isNull()) return "null";
    try {
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) { return "error"; }
}

function setup_final_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_final_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_fov = base.add(addr_set_fieldOfView);
    var ptr_set_ortho = base.add(addr_set_orthographicSize);
    var ptr_set_pos_inj = base.add(addr_set_localPosition_Inj);
    var ptr_get_name = base.add(addr_get_name);

    var native_get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);
    
    console.log("[*] Final Monitor Attached. Please ZOOM the map now...");

    // 1. Monitor 3D FOV
    var native_set_fov = new NativeFunction(ptr_set_fov, 'void', ['pointer', 'float', 'pointer']);
    Interceptor.replace(ptr_set_fov, new NativeCallback(function(camPtr, fov, method) {
        var name = readIl2CppString(native_get_name(camPtr, NULL));
        
        // 过滤 Shadow
        if (name.indexOf("Shadow") === -1) {
            console.log(`[3D FOV] Object: "${name}" -> Value: ${fov}`);
        }
        native_set_fov(camPtr, fov, method);
    }, 'void', ['pointer', 'float', 'pointer']));

    // 2. Monitor 2D Size (保留，但过滤 Shadow)
    var native_set_ortho = new NativeFunction(ptr_set_ortho, 'void', ['pointer', 'float', 'pointer']);
    Interceptor.replace(ptr_set_ortho, new NativeCallback(function(camPtr, size, method) {
        var name = readIl2CppString(native_get_name(camPtr, NULL));
        if (name.indexOf("Shadow") === -1) {
            console.log(`[2D Size] Object: "${name}" -> Value: ${size}`);
        }
        native_set_ortho(camPtr, size, method);
    }, 'void', ['pointer', 'float', 'pointer']));

    // 3. Monitor Transform Position (Z-Axis Zoom)
    // void set_localPosition_Injected(Transform* this, Vector3* val, MethodInfo* m)
    Interceptor.attach(ptr_set_pos_inj, {
        onEnter: function(args) {
            this.trans = args[0];
            this.vec3 = args[1];
        },
        onLeave: function(retval) {
            // 这里我们不能每次都调 get_name，性能开销太大
            // 所以我们只读取 Vector3 的 Z 值变化
            var z = this.vec3.add(8).readFloat();
            
            // 简单 heuristic: 
            // 战棋地图的摄像机通常 Z 轴是负数 (例如 -10, -100)
            // 且缩放时 Z 值会平滑变化
            // 我们不打印名字，只打印数值看看有没有对应变化
            // 如果控制台疯狂刷屏 Z 值，且随滚轮变化，说明找对了
            
            // 为了减少刷屏，你可以设置一个阈值或条件
            // 但为了抓取，先全部打印 Z 值看看
            // console.log(`[Pos Z] ${z}`); 
        }
    });
    
    // 如果 Transform 刷屏太快，我们单独对 Transform 做一个带名字检查的 Hook
    // 注意：这会显著降低性能，仅用于定位！
    /*
    var native_set_pos_inj = new NativeFunction(ptr_set_pos_inj, 'void', ['pointer', 'pointer', 'pointer']);
    Interceptor.replace(ptr_set_pos_inj, new NativeCallback(function(transPtr, vecPtr, method) {
        // 先读 Z 值
        var z = vecPtr.add(8).readFloat();
        
        // 如果 Z 值在变动 (你可以记录上一次的值来对比)
        // 获取名字 (昂贵操作)
        // var name = readIl2CppString(native_get_name(transPtr, NULL)); // Transform 没有 get_name，需要获取 gameObject 再 get_name
        
        // 由于 Transform 获取名字比较麻烦 (Transform -> GameObject -> Name)
        // 我们这里暂时只监控 set_fieldOfView 和 set_orthographicSize
        
        native_set_pos_inj(transPtr, vecPtr, method);
    }, 'void', ['pointer', 'pointer', 'pointer']));
    */
}

setup_final_monitor();