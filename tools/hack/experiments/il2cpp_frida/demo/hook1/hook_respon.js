// hook_check_gzip.js - 检查返回值的二进制头

var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip

function readCSharpByteHeader(ptr) {
    if (ptr.isNull()) return "null";
    try {
        // 读取长度
        var len = ptr.add(0x18).readU32();
        
        // 读取数据区的指针
        var dataPtr = ptr.add(0x20);
        
        // 读取前 16 个字节用于分析
        var headerBytes = dataPtr.readByteArray(Math.min(len, 16));
        
        return {
            length: len,
            header: headerBytes
        };

    } catch (e) {
        return { error: e.message };
    }
}

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    return mod ? mod.base : null;
}

function hook() {
    console.log("==================================================");
    console.log("[Step 2] 检查 DecodeWithGzip 返回值的二进制头...");

    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (!gameAssembly) return;

    var targetAddr = gameAssembly.add(addr_DecodeWithGzip);

    Interceptor.attach(targetAddr, {
        onEnter: function(args) {
            this.is_target = true; 
        },
        onLeave: function(retval) {
            if (this.is_target) {
                console.log("\n[!] >>> DecodeWithGzip 返回 <<<");
                
                var result = readCSharpByteHeader(retval);
                
                if (result.error) {
                    console.log("读取错误: " + result.error);
                } else {
                    console.log("数据长度: " + result.length);
                    // 打印 Hex Dump
                    console.log("数据头 (Hex):");
                    console.log(hexdump(result.header, { offset: 0, length: 16, header: false, ansi: false }));
                    
                    // 自动检测 Gzip
                    var view = new Uint8Array(result.header);
                    if (view.length >= 2 && view[0] === 0x1F && view[1] === 0x8B) {
                        console.log("✅ 检测到 Gzip 魔数 (1F 8B)！这是压缩数据。");
                    } else {
                        console.log("❌ 未检测到 Gzip 魔数。可能是其他格式或纯加密数据。");
                    }
                }
                console.log("--------------------------------------------------");
            }
        }
    });

    console.log("[+] Hook 就绪");
}

setTimeout(hook, 1000);