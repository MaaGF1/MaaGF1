// hook_ui_scroll.js

// --- Addresses (Decimal) ---
var addr_OnScroll = 15990704; // UnityEngine.UI.ScrollRect$$OnScroll

// Global State
var State = {
    capturedRect: null,      // 保存当前的滚动区域对象
    capturedEvent: null,     // 保存一个有效的事件数据包
    deltaOffset: -1,         // 自动寻找 scrollDelta 的内存偏移
    native_OnScroll: null
};

function setup_ui_hook() {
    var gameAssembly = Process.findModuleByName("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found, retrying...");
        setTimeout(setup_ui_hook, 1000);
        return;
    }
    var base = gameAssembly.base;
    var ptr_OnScroll = base.add(addr_OnScroll);

    // void OnScroll(ScrollRect* this, PointerEventData* data, MethodInfo* method)
    State.native_OnScroll = new NativeFunction(ptr_OnScroll, 'void', ['pointer', 'pointer', 'pointer']);

    console.log("[*] Hooking UI ScrollRect at " + ptr_OnScroll);

    Interceptor.attach(ptr_OnScroll, {
        onEnter: function(args) {
            var thisRect = args[0];
            var eventData = args[1];

            // 1. 捕获对象
            State.capturedRect = thisRect;
            State.capturedEvent = eventData;

            // 2. 尝试寻找 scrollDelta 的偏移量 (Heuristic Scan)
            if (State.deltaOffset === -1) {
                console.log("[Analyze] Scanning PointerEventData for scrollDelta...");
                for (var i = 0x10; i < 0x200; i += 4) {
                    try {
                        var val = eventData.add(i).readFloat();
                        var prevVal = eventData.add(i - 4).readFloat();
                        
                        if (Math.abs(val) > 0.1 && prevVal === 0.0) {
                            console.log(`[Analyze] Found candidate at offset +${i} (Value: ${val})`);
                            State.deltaOffset = i; 
                            break;
                        }
                    } catch (e) {}
                }
            }

            console.log(`[UI] ScrollRect Active! Instance: ${thisRect}, EventData: ${eventData}`);
        }
    });

    send({ type: 'ready', msg: "UI Scroll Hook Installed. Please perform ONE manual scroll to capture the instance." });
}

// --- RPC Exports ---
rpc.exports = {
    // Delta: 1.0 (Up) or -1.0 (Down) - 或者是 120 / -120
    scroll: function(delta) {
        if (State.capturedRect === null || State.capturedEvent === null) {
            return "ERROR: No ScrollRect captured yet. Please scroll manually once.";
        }
        if (State.deltaOffset === -1) {
            return "ERROR: Offset not found. Please scroll manually again.";
        }

        try {
            // 1. 修改 EventData 中的 scrollDelta
            var ptrY = State.capturedEvent.add(State.deltaOffset);
            var ptrX = State.capturedEvent.add(State.deltaOffset - 4);
            
            ptrX.writeFloat(0.0);
            ptrY.writeFloat(float(delta));

            // 2. 主动调用 OnScroll
            State.native_OnScroll(State.capturedRect, State.capturedEvent, NULL);

            return "OK: Injected scroll delta " + delta;
        } catch (e) {
            return "EXCEPTION: " + e.message;
        }
    }
};

// JS Helper for float casting
function float(num) {
    return num; // JS handles numbers dynamically, but writing memory handles type
}

setup_ui_hook();