// tools/hack/reward_gun_trimmer/hook_mitm.js

var addr_InitGunInfo = 5437312; // CommonGetNewGunController$$InitGunInfo
var addr_Close       = 5435456; // CommonGetNewGunController$$Close
var addr_CanClose    = 5435216; // CommonGetNewGunController$$CanClose

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) {
        send({ type: "error", payload: "GameAssembly.dll not found." });
        return;
    }

    var ptr_InitGunInfo = gameAssembly.add(addr_InitGunInfo);
    var ptr_Close       = gameAssembly.add(addr_Close);
    var ptr_CanClose    = gameAssembly.add(addr_CanClose);

    // 1. 【安全锁】强制 CanClose 永远返回 True (1)，为后续的销毁做准备
    try {
        Memory.protect(ptr_CanClose, 3, 'rwx');
        ptr_CanClose.writeByteArray([0xB0, 0x01, 0xC3]); 
    } catch (e) {
        send({ type: "error", payload: "Failed to patch CanClose: " + e.message });
    }

    var callClose = new NativeFunction(ptr_Close, 'void', ['pointer', 'pointer']);

    // 2. 【核心】彻底替换 InitGunInfo，剥夺原函数的执行权
    Interceptor.replace(ptr_InitGunInfo, new NativeCallback(function(__this, gun, action, method) {
        send({ type: "info", payload: "[JS] Bypassing UI Initialization entirely..." });

        // 第一步：向事件队列伪造“动画已播完”的完成信号
        if (!action.isNull()) {
            // 解析 IL2CPP Delegate 的底层结构
            var invoke_impl = action.add(0x18).readPointer();
            var target      = action.add(0x20).readPointer();
            
            // 构造并直接调用回调函数
            var actionInvoke = new NativeFunction(invoke_impl, 'void', ['pointer']);
            actionInvoke(target);
            
            send({ type: "info", payload: "[JS] Faked 'True' return to Event Queue via Action.Invoke()." });
        }

        // 第二步：瞬间销毁刚刚被 Lua 压入屏幕、但还未来得及渲染的 UI 空壳
        try {
            callClose(__this, ptr(0));
            send({ type: "info", payload: "[JS] UI Container shredded. Event completely bypassed." });
        } catch (e) {
            // 忽略销毁可能产生的异常，以防 UI 已经被底层回收
        }

    }, 'void', ['pointer', 'pointer', 'pointer', 'pointer']));

    send({ type: "info", payload: "[JS] Control Flow Hijacker is ACTIVE." });
}

setTimeout(hook, 1000);