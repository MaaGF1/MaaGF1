// monitor_motion.js

// --- Addresses (Decimal) ---
var addr_get_position_Inj = 17598368;  // Transform.get_position_Injected
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

// --- Cache ---
var ptrCache = {};     // 指针 -> 名字
var posCache = {};     // 指针 -> {x, y, z} (上一次的坐标)
var lastPrintTime = 0;

function setup_motion_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_motion_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    var ptr_get_pos_inj = base.add(addr_get_position_Inj);
    var ptr_get_go = base.add(addr_get_gameObject);
    var ptr_get_name = base.add(addr_get_name);

    var get_gameObject = new NativeFunction(ptr_get_go, 'pointer', ['pointer', 'pointer']);
    var get_name = new NativeFunction(ptr_get_name, 'pointer', ['pointer', 'pointer']);

    console.log("[*] Motion Sensor Active.");
    console.log("[*] Please DRAG or ZOOM the map continuously...");

    // Hook: void get_position_Injected(Transform* this, Vector3* ret, MethodInfo* m)
    Interceptor.attach(ptr_get_pos_inj, {
        onEnter: function(args) {
            this.transPtr = args[0];
            this.retPtr = args[1]; // 返回值写入这里
        },
        onLeave: function(retval) {
            var ptr = this.transPtr;
            var ret = this.retPtr;
            
            // 读取当前坐标
            var x = ret.readFloat();
            var y = ret.add(4).readFloat();
            var z = ret.add(8).readFloat();

            var key = ptr.toString();
            
            // 1. 检查坐标是否发生显著变化
            var last = posCache[key];
            if (last) {
                // 计算曼哈顿距离或者简单的差值
                var diff = Math.abs(x - last.x) + Math.abs(y - last.y) + Math.abs(z - last.z);
                
                // 阈值：只有移动超过 0.1 单位才认为是有效移动 (过滤浮点漂移)
                if (diff > 0.1) {
                    
                    // 2. 获取名字 (Lazy Load)
                    var name = ptrCache[key];
                    if (name === undefined) {
                        try {
                            var go = get_gameObject(ptr, NULL);
                            var n = get_name(go, NULL);
                            name = readIl2CppString(n);
                        } catch(e) { name = "unknown"; }
                        ptrCache[key] = name;
                    }

                    // 3. 过滤逻辑
                    // 忽略 UI, 忽略特效, 忽略人形模型
                    // 我们只关心可能的摄像机父节点
                    if (isValidTarget(name)) {
                        console.log(`[Motion] "${name}" -> X:${x.toFixed(1)}, Y:${y.toFixed(1)}, Z:${z.toFixed(1)}`);
                    }
                }
            }

            // 更新缓存
            posCache[key] = {x: x, y: y, z: z};
        }
    });
}

function isValidTarget(name) {
    // 排除列表 (根据经验)
    if (name === "null" || name === "unknown") return false;
    if (name.indexOf("Text") !== -1) return false;
    if (name.indexOf("Image") !== -1) return false;
    if (name.indexOf("Clone") !== -1) return false; // 通常是子弹或特效
    if (name.indexOf("Spine") !== -1) return false; // 2D 骨骼动画
    if (name.indexOf("UI") !== -1) return false;
    
    // 必须包含的关键词 (宽泛一点)
    // 我们找: Camera, Map, Root, Holder, Rig, Container, Content
    var whitelist = ["Camera", "Map", "Root", "Holder", "Rig", "Content", "Container", "Battle", "Scaler"];
    
    for (var i = 0; i < whitelist.length; i++) {
        if (name.indexOf(whitelist[i]) !== -1) return true;
    }
    return false;
}

setup_motion_monitor();