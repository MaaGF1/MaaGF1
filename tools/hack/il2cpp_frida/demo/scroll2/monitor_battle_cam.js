// monitor_battle_cam.js

// --- Addresses (Decimal) ---
var addr_getInstance = 33570896;   // BattleCameraController.get_Instance
var addr_MoveCamaraPos = 33567872; // MoveCamaraPos(Vector2 dragOffset, float scale)
var addr_RescaleCamara = 33569104; // RescaleCamara(float fov, Vector3 parentPos, Vector3 parentEuler)
var addr_OnDrag = 33568608;        // OnDrag(Vector3 startDragPos, Vector3 currentPos)

function setup_battle_cam_monitor() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found...");
        setTimeout(setup_battle_cam_monitor, 1000);
        return;
    }
    var base = gameAssembly.base;

    console.log("[*] Battle Camera Controller Monitor Attached!");
    console.log("[*] Please Drag and Zoom the map in the Battle Scene...");

    // 1. 监听: MoveCamaraPos (极有可能是缩放或拖动的底层实现)
    Interceptor.attach(base.add(addr_MoveCamaraPos), {
        onEnter: function(args) {
            // IL2CPP x64 ABI:
            // arg0: this
            // arg1: Vector2 (8 bytes, usually passed in register as integer/double)
            // arg2: float (scale)
            // arg3: MethodInfo
            
            // 我们不纠结复杂的结构体解析，先确认它是否被调用
            console.log(`[BattleCam] MoveCamaraPos() Triggered!`);
        }
    });

    // 2. 监听: RescaleCamara (名字直接写了 Rescale)
    Interceptor.attach(base.add(addr_RescaleCamara), {
        onEnter: function(args) {
            console.log(`[BattleCam] RescaleCamara() Triggered!`);
            // 尝试读取第一参数 fov (通常在浮点寄存器或栈上，这里我们通过简单的方式尝试读取)
            // 由于 x64 ABI 复杂，我们先仅作调用确认
        }
    });

    // 3. 监听: OnDrag (拖动地图)
    Interceptor.attach(base.add(addr_OnDrag), {
        onEnter: function(args) {
            // console.log(`[BattleCam] OnDrag() Triggered!`);
            // 注释掉防止拖动时刷屏，如果你想确认拖动逻辑可以取消注释
        }
    });
}

// 暴露出一个可以直接调用的接口 (为下一步做准备)
rpc.exports = {
    testCall: function() {
        var base = Process.findModuleByName("GameAssembly.dll").base;
        var get_Instance = new NativeFunction(base.add(addr_getInstance), 'pointer', ['pointer']);
        try {
            var instance = get_Instance(NULL);
            if (!instance.isNull()) {
                return "Success! Found BattleCameraController Instance: " + instance;
            }
            return "Instance is null. Are you in a battle?";
        } catch (e) {
            return "Error calling get_Instance: " + e.message;
        }
    }
};

setup_battle_cam_monitor();