// tools/hack/luna/hook.js

var State = {
    mode: "inject", // Default to inject mode for Luna
    fakePos: { x: 0, y: 0 },
    hwnd: null
};

function debug_hook() {
    // 1. Find User32.dll
    var user32 = Process.findModuleByName("user32.dll");
    if (!user32) {
        user32 = Process.findModuleByName("User32.dll");
    }

    if (!user32) {
        send({ type: 'error', stack: "user32.dll not found" });
        return;
    }

    // 2. Resolve Exports
    function resolve_export(mod, name) {
        return mod.findExportByName(name);
    }

    var ptr_ScreenToClient = resolve_export(user32, "ScreenToClient");
    var ptr_GetCursorPos = resolve_export(user32, "GetCursorPos");

    // 3. Hook ScreenToClient
    if (ptr_ScreenToClient) {
        Interceptor.attach(ptr_ScreenToClient, {
            onEnter: function(args) {
                this.hwnd = args[0];
                this.lpPoint = args[1];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                try {
                    if (State.mode === "inject") {
                        this.lpPoint.writeS32(parseInt(State.fakePos.x));
                        this.lpPoint.add(4).writeS32(parseInt(State.fakePos.y));
                    }
                } catch (e) {}
            }
        });
    }

    // 4. Hook GetCursorPos (Backup for some Unity versions)
    if (ptr_GetCursorPos) {
        Interceptor.attach(ptr_GetCursorPos, {
            onEnter: function(args) {
                this.lpPoint = args[0];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                try {
                    if (State.mode === "inject") {
                        this.lpPoint.writeS32(parseInt(State.fakePos.x));
                        this.lpPoint.add(4).writeS32(parseInt(State.fakePos.y));
                    }
                } catch (e) {}
            }
        });
    }
    
    send({ type: 'info', payload: "Hooks installed successfully." });
}

// ================= Message Processing =================
recv(function onMessage(message) {
    if (message.type === "UPDATE_POS") {
        State.fakePos.x = message.x;
        State.fakePos.y = message.y;
        // No log here to keep performance high
    }
    recv(onMessage);
});

try {
    debug_hook();
} catch (e) {
    send({ type: 'error', stack: e.message });
}