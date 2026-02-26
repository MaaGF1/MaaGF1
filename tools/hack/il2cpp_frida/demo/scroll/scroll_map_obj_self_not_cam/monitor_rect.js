// monitor_rect.js

// --- Addresses (Decimal) ---
var addr_set_anchoredPos_Inj = 17511440; // RectTransform.set_anchoredPosition_Injected
var addr_get_gameObject = 16465776;      // Component.get_gameObject
var addr_get_name = 16605904;            // Object.get_name

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

function setup_rect_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_rect_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_pos_inj = base.add(addr_set_anchoredPos_Inj);
    var ptr_get_go = base.add(addr_get_gameObject);
    var ptr_get_name = base.add(addr_get_name);

    var get_gameObject = new NativeFunction(ptr_get_go, 'pointer', ['pointer', 'pointer']);
    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] RectTransform Monitor Attached.");
    console.log("[*] Please DRAG the map vigorously...");

    // Hook: void set_anchoredPosition_Injected(RectTransform* this, Vector2* val, MethodInfo* m)
    Interceptor.attach(ptr_set_pos_inj, {
        onEnter: function(args) {
            var transPtr = args[0];
            var vecPtr = args[1]; // Vector2*

            var ptrKey = transPtr.toString();
            
            // 1. 缓存与过滤
            if (relevantCache[ptrKey] === undefined) {
                try {
                    var goPtr = get_gameObject(transPtr, NULL);
                    var namePtr = get_name(goPtr, NULL);
                    var name = readIl2CppString(namePtr);
                    
                    // 记录名字
                    ptrCache[ptrKey] = name;

                    // 宽泛过滤：排除明显无关的 UI 小部件
                    if (isValidTarget(name)) {
                        relevantCache[ptrKey] = true;
                        console.log(`[New Target] Tracking Rect: "${name}"`);
                    } else {
                        relevantCache[ptrKey] = false;
                    }
                } catch(e) { 
                    relevantCache[ptrKey] = false;
                }
            }

            // 2. 打印数值
            if (relevantCache[ptrKey]) {
                var x = vecPtr.readFloat();
                var y = vecPtr.add(4).readFloat();
                
                // 打印格式：[名字] X, Y
                console.log(`[Rect] ${ptrCache[ptrKey]} -> X:${x.toFixed(1)}, Y:${y.toFixed(1)}`);
            }
        }
    });
}

function isValidTarget(name) {
    if (!name || name === "null" || name === "unknown") return false;
    
    // 排除列表 (根据经验)
    if (name.indexOf("Text") !== -1) return false;
    if (name.indexOf("Image") !== -1) return false; // 图标移动先不管
    if (name.indexOf("Button") !== -1) return false;
    if (name.indexOf("Bar") !== -1) return false;   // 血条等
    if (name.indexOf("Tip") !== -1) return false;
    if (name.indexOf("Glow") !== -1) return false;
    
    // 我们找的是大块头：Map, Content, Container, Panel, Layer
    return true; 
}

setup_rect_monitor();