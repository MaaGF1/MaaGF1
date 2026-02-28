// hook.js

var State = {
    mode: "monitor",
    fakePos: { x: 0, y: 0 },
    hwnd: null
};

function debug_hook() {
    console.log("========================================");
    console.log("[*] Diagnostic Info:");
    console.log("    Frida Version: " + Frida.version);
    console.log("    Process Arch:  " + Process.arch);
    console.log("    Platform:      " + Process.platform);
    console.log("========================================");

    // 1. Explicitly find User32.dll module
    // Windows filenames are usually case-insensitive, but try both for safety
    var user32 = Process.findModuleByName("user32.dll");
    if (!user32) {
        user32 = Process.findModuleByName("User32.dll");
    }

    if (!user32) {
        console.log("[!] CRITICAL: Could not find user32.dll in the process memory!");
        console.log("[*] Listing first 5 modules to check naming:");
        Process.enumerateModules({
            onMatch: function(m) { console.log("    - " + m.name); },
            onComplete: function() {}
        });
        return; // Cannot continue
    }

    console.log("[+] Found user32.dll at: " + user32.base);

    // 2. Find exported functions from module (not using global search)
    function resolve_export(mod, name) {
        var ptr = mod.findExportByName(name);
        if (!ptr) {
            console.log("[!] Warning: " + name + " not found in user32.dll");
            return null;
        }
        console.log("[+] Found API " + name + " at: " + ptr);
        return ptr;
    }

    var ptr_ScreenToClient = resolve_export(user32, "ScreenToClient");
    var ptr_GetCursorPos = resolve_export(user32, "GetCursorPos");

    // 3. Execute Hook
    if (ptr_ScreenToClient) {
        Interceptor.attach(ptr_ScreenToClient, {
            onEnter: function(args) {
                this.hwnd = args[0];
                this.lpPoint = args[1];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                try {
                    if (State.hwnd === null) State.hwnd = this.hwnd;
                    
                    // Read original values
                    var x = this.lpPoint.readS32();
                    var y = this.lpPoint.add(4).readS32();

                    if (State.mode === "monitor") {
                        // console.log("[ScreenToClient] x=" + x + " y=" + y);
                    } else if (State.mode === "inject") {
                        this.lpPoint.writeS32(parseInt(State.fakePos.x));
                        this.lpPoint.add(4).writeS32(parseInt(State.fakePos.y));
                    }
                } catch (e) {}
            }
        });
        console.log("[*] Hooked ScreenToClient");
    }

    if (ptr_GetCursorPos) {
        Interceptor.attach(ptr_GetCursorPos, {
            onEnter: function(args) {
                this.lpPoint = args[0];
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) return;
                try {
                    var x = this.lpPoint.readS32();
                    var y = this.lpPoint.add(4).readS32();
                    if (State.mode === "monitor") {
                        // console.log("[GetCursorPos] ScreenX=" + x + " ScreenY=" + y);
                    }
                } catch (e) {}
            }
        });
        console.log("[*] Hooked GetCursorPos");
    }
}

// ================= Message Processing =================
recv(function onMessage(message) {
    if (message.type === "SIMULATE_CLICK") {
        State.fakePos.x = message.x;
        State.fakePos.y = message.y;
        console.log("[Control] Target set to: " + State.fakePos.x + ", " + State.fakePos.y);
    }
    else if (message.type === "SET_MODE") {
        State.mode = message.mode;
        console.log("[Control] Mode switched to: " + State.mode);
    }
    recv(onMessage);
});

// Add try-catch to prevent main logic crash
try {
    debug_hook();
} catch (e) {
    console.log("[!] Script Crash: " + e.message);
}