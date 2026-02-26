// monitor_world_pos.js

// --- Addresses (Decimal) ---
var addr_set_position = 17601760;       // Transform.set_position (World Space)
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

// Global Cache
var ptrCache = {};
var targetFound = false;
var targetPtr = null; // 保存我们找到的主摄像机指针

function setup_world_pos_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_world_pos_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_pos = base.add(addr_set_position);
    var ptr_get_go = base.add(addr_get_gameObject);
    var ptr_get_name = base.add(addr_get_name);

    var get_gameObject = new NativeFunction(ptr_get_go, 'pointer', ['pointer', 'pointer']);
    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] World Position Monitor Attached.");
    console.log("[*] Try dragging/zooming the map. Listening for 'set_position'...");

    // Hook: void set_position(Transform* this, Vector3 value, MethodInfo* m)
    // 注意：在 IL2CPP 中，Vector3 (12 bytes) 有时通过指针传递，有时通过寄存器/栈传递。
    // 我们假设 args[1] 是指向 Vector3 的指针（这是生成的 C++ 包装器的常见做法）。
    
    Interceptor.attach(ptr_set_pos, {
        onEnter: function(args) {
            var transPtr = args[0];
            var vecPtr = args[1]; // 假设这是 Vector3 的指针

            // 缓存检查，避免卡顿
            var ptrKey = transPtr.toString();
            var name = ptrCache[ptrKey];

            if (name === undefined) {
                try {
                    // Transform -> GameObject -> Name
                    // 注意：Transform 也是 Object，有些版本可以直接 get_name(transPtr)
                    // 但为了保险，我们走 get_gameObject 路线
                    var goPtr = get_gameObject(transPtr, NULL);
                    var namePtr = get_name(goPtr, NULL);
                    name = readIl2CppString(namePtr);
                } catch (e) {
                    name = "unknown";
                }
                ptrCache[ptrKey] = name;

                // 筛选逻辑：我们只关心这些名字
                if (name.indexOf("Main Camera") !== -1 || 
                    name.indexOf("Map") !== -1 || 
                    name.indexOf("Battle") !== -1 ||
                    name.indexOf("Camera") !== -1) {
                    
                    if (name.indexOf("Shadow") === -1 && name.indexOf("Message") === -1) {
                        console.log(`[Target Found] Tracking World Position for: "${name}"`);
                        // 甚至我们可以把这个指针打印出来，或者存下来
                        // console.log(`    -> Transform Ptr: ${transPtr}`);
                    }
                }
            }

            // 只打印感兴趣的对象
            if (name && (name.indexOf("Main Camera") !== -1 || name.indexOf("Map") !== -1)) {
                 if (name.indexOf("Shadow") === -1) {
                    try {
                        // 尝试读取坐标
                        var x = vecPtr.readFloat();
                        var y = vecPtr.add(4).readFloat();
                        var z = vecPtr.add(8).readFloat();
                        
                        // 打印坐标 (World Space)
                        console.log(`[Pos] ${name} -> X:${x.toFixed(1)}, Y:${y.toFixed(1)}, Z:${z.toFixed(1)}`);
                    } catch(e) {
                        // 如果读取失败，说明 args[1] 可能不是指针，或者是其他传递方式
                        // console.log(`[Pos] ${name} called, but failed to read Vector3.`);
                    }
                 }
            }
        }
    });
}

setup_world_pos_monitor();