// monitor_map_scale.js

// --- Addresses (Decimal) ---
var addr_set_localScale_Inj = 17601216; // Transform.set_localScale_Injected
var addr_get_gameObject = 16465776;     // Component.get_gameObject
var addr_get_name = 16605904;           // Object.get_name

// --- Helpers ---
function readIl2CppString(ptr) {
    if (ptr.isNull()) return "null";
    try {
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) { return "error"; }
}

// --- Cache ---
var ptrCache = {}; 
var relevantCache = {};

function setup_scale_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_scale_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_scale_inj = base.add(addr_set_localScale_Inj);
    var ptr_get_go = base.add(addr_get_gameObject);
    var ptr_get_name = base.add(addr_get_name);

    var get_gameObject = new NativeFunction(ptr_get_go, 'pointer', ['pointer', 'pointer']);
    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] Scale Monitor Attached.");
    console.log("[*] Please ZOOM the map via Scroll Wheel now...");

    // Hook: void set_localScale_Injected(Transform* this, Vector3* val, MethodInfo* m)
    Interceptor.attach(ptr_set_scale_inj, {
        onEnter: function(args) {
            var transPtr = args[0];
            var vecPtr = args[1]; // Vector3*

            // 1. 快速缓存检查
            var ptrKey = transPtr.toString();
            var name = ptrCache[ptrKey];

            if (name === undefined) {
                try {
                    var goPtr = get_gameObject(transPtr, NULL);
                    var namePtr = get_name(goPtr, NULL);
                    name = readIl2CppString(namePtr);
                } catch(e) { name = "unknown"; }
                ptrCache[ptrKey] = name;

                // 2. 智能过滤
                // 排除 UI 文本、图片、特效等干扰项
                // 我们关注：Map, Content, Container, Root, CameraRig, Layer
                if (isValidTarget(name)) {
                    relevantCache[ptrKey] = true;
                    console.log(`[New Target Found] Tracking Scale for: "${name}"`);
                } else {
                    relevantCache[ptrKey] = false;
                }
            }

            // 3. 打印数值
            if (relevantCache[ptrKey]) {
                var x = vecPtr.readFloat();
                var y = vecPtr.add(4).readFloat();
                var z = vecPtr.add(8).readFloat();
                
                // 为了防止刷屏，你可以只打印 X 值 (Scale 通常是 xyz 等比缩放)
                console.log(`[Scale] ${name} -> ${x.toFixed(3)}`);
            }
        }
    });
}

function isValidTarget(name) {
    if (name === "null" || name === "unknown") return false;
    // 排除杂项
    if (name.indexOf("Text") !== -1) return false;
    if (name.indexOf("Image") !== -1) return false;
    if (name.indexOf("Spine") !== -1) return false; // 骨骼动画缩放很常见，排除
    if (name.indexOf("Shadow") !== -1) return false;
    if (name.indexOf("Particle") !== -1) return false;
    
    // 必须是可能的容器名
    // 很多 UGUI 地图的缩放对象叫 "Content", "Map", "Container"
    // 或者直接放行所有非排除项，看看谁在动
    return true; 
}

setup_scale_monitor();