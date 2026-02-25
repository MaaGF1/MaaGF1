// tools/hack/reward_gun_trimmer/hook_mitm.js

var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip

// Helper function: Read C# byte array
function getCSharpByteArray(ptr) {
    if (ptr.isNull()) return null;
    try {
        var len = ptr.add(0x18).readU32();
        var dataPtr = ptr.add(0x20);
        return dataPtr.readByteArray(len);
    } catch (e) {
        return null;
    }
}

// Helper function: Overwrite C# byte array
function writeCSharpByteArray(ptr, newData) {
    if (ptr.isNull()) return false;
    
    // Get original array capacity (assume current length is capacity)
    var originalLen = ptr.add(0x18).readU32();
    var newLen = newData.byteLength;
    
    // Safety check: If new data is larger than original space, we cannot write directly
    if (newLen > originalLen) {
        console.log("[JS Danger] New data length (" + newLen + ") exceeds original array capacity (" + originalLen + ")!");
        console.log("[JS Danger] Aborting modification to prevent game crash.");
        return false;
    }

    try {
        // 1. Update array length field
        ptr.add(0x18).writeU32(newLen);
        
        // 2. Write new data
        var dataPtr = ptr.add(0x20);
        dataPtr.writeByteArray(newData);
        
        // 3. (Optional) Clear remaining old data, usually not needed after updating length, but keeps it clean
        if (newLen < originalLen) {
            // Fill with 0
            // dataPtr.add(newLen).writeByteArray(new ArrayBuffer(originalLen - newLen));
        }
        
        return true;
    } catch (e) {
        console.log("[JS Error] Write failed: " + e.message);
        return false;
    }
}

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) return;

    var targetAddr = gameAssembly.add(addr_DecodeWithGzip);

    Interceptor.attach(targetAddr, {
        onEnter: function(args) {
            this.is_target = true; 
        },
        onLeave: function(retval) {
            if (this.is_target) {
                var originalData = getCSharpByteArray(retval);
                
                if (originalData) {
                    // 1. Send request to Python
                    send({ id: "req_modify" }, originalData);
                    
                    // 2. Synchronously wait for Python's reply
                    // recv().wait() will block the game thread until Python sends a message back
                    var received = recv('resp_modify', function(msg, data) {
                        
                        if (msg.payload === 'modified' && data) {
                            console.log("[JS] Received modified data, preparing to overwrite memory...");
                            
                            // 3. Overwrite memory
                            var success = writeCSharpByteArray(retval, data);
                            if (success) {
                                console.log("[JS] Memory overwrite successful! user_exp modified.");
                            }
                        } else {
                            console.log("[JS] Keeping original data.");
                        }
                    });
                    
                    // Block here
                    received.wait();
                }
            }
        }
    });

    console.log("[JS] Hook ready (Sync blocking mode)");
}

setTimeout(hook, 1000);