// hook_dual.js

// Addresses from your list
var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip
var addr_Encode = 21054608;         // AC.AuthCode$$Encode

// Helper: Read C# Byte Array (System.Byte[])
function getCSharpByteArray(ptr) {
    if (ptr.isNull()) return null;
    try {
        // Il2CppArray Structure (64-bit usually):
        // 0x00: Class Pointer
        // 0x18: Length (int32)
        // 0x20: Data Start
        var len = ptr.add(0x18).readU32();
        var dataPtr = ptr.add(0x20);
        
        if (len === 0) return null;
        
        // Read memory as ArrayBuffer
        var bytes = dataPtr.readByteArray(len);
        return bytes;

    } catch (e) {
        console.log("[JS Error] Failed to read byte array: " + e.message);
        return null;
    }
}

// Helper: Read C# String (System.String)
function getCSharpString(ptr) {
    if (ptr.isNull()) return null;
    try {
        // Il2CppString Structure (64-bit usually):
        // 0x10: Length (int32)
        // 0x14: First Character (UTF-16)
        var len = ptr.add(0x10).readU32();
        if (len === 0) return "";
        
        // Read UTF-16 string
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) {
        console.log("[JS Error] Failed to read string: " + e.message);
        return null;
    }
}

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) {
        console.log("[!] GameAssembly.dll not found. Retrying...");
        setTimeout(hook, 1000);
        return;
    }

    // --- Hook S2C (Server To Client) ---
    var targetS2C = gameAssembly.add(addr_DecodeWithGzip);
    Interceptor.attach(targetS2C, {
        onEnter: function(args) {
            this.is_target = true; 
        },
        onLeave: function(retval) {
            if (this.is_target) {
                // retval is byte[] (Gzipped)
                var data = getCSharpByteArray(retval);
                if (data) {
                    send({ id: "S2C" }, data);
                }
            }
        }
    });

    // --- Hook C2S (Client To Server) ---
    var targetC2S = gameAssembly.add(addr_Encode);
    Interceptor.attach(targetC2S, {
        onEnter: function(args) {
            // args[0] is source string (Raw JSON)
            // args[1] is key string
            var strContent = getCSharpString(args[0]);
            var strKey = getCSharpString(args[1]);
            
            if (strContent && strContent.length > 0) {
                console.log("[C2S] Key used: " + strKey);

                // If the string looks like JSON (starts with { or [), send it
                if (strContent.trim().charAt(0) === '{' || strContent.trim().charAt(0) === '[') {
                    send({ id: "C2S", content: strContent });
                }
            }
        },
        onLeave: function(retval) {
            // We don't need the result of Encode (it is encrypted)
        }
    });

    console.log("[JS] Hooks installed. Listening for S2C and C2S data...");
}

setTimeout(hook, 1000);