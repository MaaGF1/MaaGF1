// monitor_material.js

// --- Addresses (Decimal) ---
var addr_set_mainTextureOffset = 16565504; // Material.set_mainTextureOffset
var addr_SetVector_Str = 16562816;         // Material.SetVector(string name, Vector4 value)
var addr_SetFloat_Str = 16558656;          // Material.SetFloat(string name, float value)
var addr_get_name = 16605904;              // Object.get_name (用于获取材质名)

// --- Helpers ---
function readIl2CppString(ptr) {
    if (ptr.isNull()) return "null";
    try {
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) { return ""; }
}

function setup_material_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_material_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_set_offset = base.add(addr_set_mainTextureOffset);
    var ptr_set_vector = base.add(addr_SetVector_Str);
    var ptr_set_float = base.add(addr_SetFloat_Str);
    var ptr_get_name = base.add(addr_get_name);

    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] Material/Shader Monitor Attached.");
    console.log("[*] Warning: This might be noisy. Drag the map NOW.");

    // =========================================================
    // 1. Monitor mainTextureOffset (最经典的 2D 滚动方式)
    // =========================================================
    Interceptor.attach(ptr_set_offset, {
        onEnter: function(args) {
            var matPtr = args[0];
            var vecPtr = args[1]; // Vector2* (injected structs are usually ptrs)

            // 读取 X, Y
            // 注意：这里假设 Vector2 是作为指针传递的 (IL2CPP常见)
            // 如果读出来是天文数字，可能是寄存器传递，需要改 readFloat
            try {
                var x = vecPtr.readFloat();
                var y = vecPtr.add(4).readFloat();

                // 只有当 Offset 不为 0 时打印，或者是变化的
                if (Math.abs(x) > 0.001 || Math.abs(y) > 0.001) {
                    var matName = readIl2CppString(get_name(matPtr, NULL));
                    console.log(`[TexOffset] Material: "${matName}" -> X:${x.toFixed(3)}, Y:${y.toFixed(3)}`);
                }
            } catch(e) {}
        }
    });

    // =========================================================
    // 2. Monitor SetVector (自定义 Shader 偏移)
    // =========================================================
    Interceptor.attach(ptr_set_vector, {
        onEnter: function(args) {
            var namePtr = args[1];
            var vecPtr = args[2]; // Vector4*

            var propName = readIl2CppString(namePtr);
            
            // 过滤器：只关心看起来像 偏移/缩放 的属性
            if (isInterestingProperty(propName)) {
                try {
                    var x = vecPtr.readFloat();
                    var y = vecPtr.add(4).readFloat();
                    var z = vecPtr.add(8).readFloat();
                    var w = vecPtr.add(12).readFloat();
                    
                    // var matName = readIl2CppString(get_name(args[0], NULL)); // 获取材质名太慢，先省略
                    console.log(`[SetVector] Prop: "${propName}" -> [${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)}, ${w.toFixed(2)}]`);
                } catch(e) {}
            }
        }
    });

    // =========================================================
    // 3. Monitor SetFloat (自定义 Shader 缩放)
    // =========================================================
    Interceptor.attach(ptr_set_float, {
        onEnter: function(args) {
            var namePtr = args[1];
            // float 是值传递还是指针传递？在 x64 下 float 参数通常在 XMM 寄存器
            // 但 IL2CPP 有时会生成 float value 作为参数。
            // args[2] 是 float 值 (需要在 onEnter 里读很难，因为它是寄存器值)
            // 简单起见，我们假设它是通过 stack 或者我们需要用 NativeCallback 替换
        }
    });
    
    // 为了正确读取 float，我们对 SetFloat 使用 Replace
    var native_set_float = new NativeFunction(ptr_set_float, 'void', ['pointer', 'pointer', 'float', 'pointer']);
    Interceptor.replace(ptr_set_float, new NativeCallback(function(mat, namePtr, val, method) {
        var propName = readIl2CppString(namePtr);
        if (isInterestingProperty(propName)) {
             console.log(`[SetFloat] Prop: "${propName}" -> ${val}`);
        }
        native_set_float(mat, namePtr, val, method);
    }, 'void', ['pointer', 'pointer', 'float', 'pointer']));
}

function isInterestingProperty(name) {
    if (!name || name.length < 2) return false;
    var lower = name.toLowerCase();
    
    // 关键词白名单
    if (lower.indexOf("pos") !== -1) return true;    // Position
    if (lower.indexOf("offset") !== -1) return true; // Offset
    if (lower.indexOf("pan") !== -1) return true;    // Pan
    if (lower.indexOf("zoom") !== -1) return true;   // Zoom
    if (lower.indexOf("scale") !== -1) return true;  // Scale
    if (lower.indexOf("tiling") !== -1) return true; // Tiling (_MainTex_ST)
    if (lower.indexOf("center") !== -1) return true;
    
    return false;
}

setup_material_monitor();