// monitor_map_pos.js

// --- Addresses (Decimal) ---
var addr_set_localPosition_Inj = 17600768; // Transform.set_localPosition_Injected
var addr_get_gameObject = 16465776;        // Component.get_gameObject
var addr_get_name = 16605904;              // Object.get_name

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
// 用于存储 Transform指针 -> 名字 的映射，防止游戏卡死
var ptrCache = {}; 
var relevantCache = {}; // 只存储我们感兴趣的对象，加速查找

function setup_pos_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_pos_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_pos_inj = base.add(addr_set_localPosition_Inj);
    var ptr_get_go = base.add(addr_get_gameObject);
    var ptr_get_name = base.add(addr_get_name);

    // Native Functions
    var get_gameObject = new NativeFunction(ptr_get_go, 'pointer', ['pointer', 'pointer']);
    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] Position Monitor Attached with Caching System.");
    console.log("[*] Please ZOOM the map via Scroll Wheel now...");

    // Hook: void set_localPosition_Injected(Transform* this, Vector3* val, MethodInfo* m)
    Interceptor.attach(ptr_set_pos_inj, {
        onEnter: function(args) {
            var transPtr = args[0];
            var vecPtr = args[1]; // Vector3*

            // 1. 快速缓存检查
            // 将指针转换为字符串作为 Key
            var ptrKey = transPtr.toString();
            var name = ptrCache[ptrKey];

            // 2. 如果缓存中没有，获取名字并缓存
            if (name === undefined) {
                try {
                    var goPtr = get_gameObject(transPtr, NULL);
                    var namePtr = get_name(goPtr, NULL);
                    name = readIl2CppString(namePtr);
                } catch(e) {
                    name = "unknown";
                }
                ptrCache[ptrKey] = name;
                
                // 标记是否相关 (过滤掉无关对象以提升性能)
                // 我们只关心名字里带 "Camera" 且不是 "Shadow" 或 "Message" 的对象
                if (name.indexOf("Camera") !== -1 && 
                    name.indexOf("Shadow") === -1 && 
                    name.indexOf("Message") === -1) {
                    relevantCache[ptrKey] = true;
                    console.log(`[New Target Found] Tracking position for: "${name}"`);
                } else {
                    relevantCache[ptrKey] = false;
                }
            }

            // 3. 只有相关对象才读取并打印坐标
            if (relevantCache[ptrKey]) {
                var x = vecPtr.readFloat();
                var y = vecPtr.add(4).readFloat();
                var z = vecPtr.add(8).readFloat();

                // 打印格式：[名字] X, Y, Z
                // 注意：由于 set_localPosition 调用频率极高，这里可能会刷屏
                // 建议在战役地图里手动滚轮时观察数值变化
                console.log(`[Pos] ${name} -> X:${x.toFixed(2)}, Y:${y.toFixed(2)}, Z:${z.toFixed(2)}`);
            }
        }
    });
}

setup_pos_monitor();