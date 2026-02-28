// hook_multi.js - 批量 Hook 版本

// --- 配置区域：填入 JSON 中的十进制地址 ---
var targets = [
    { name: "AC.AuthCode$$Decode",          offset: 21054480 },
    { name: "AC.AuthCode$$DecodeWithGzip",  offset: 21054368 }, // 重点关注对象
    { name: "AC.AuthCode$$Authcode",        offset: 21050368 }, // 核心底层方法
    { name: "AC.AuthCode$$RC4",             offset: 21055696 }
];

// --- 辅助函数 ---

function readIl2CppString(ptr) {
    if (ptr.isNull()) return "null";
    try {
        var len = ptr.add(0x10).readS32();
        if (len > 10000 || len < 0) return "Invalid Len:" + len;
        return ptr.add(0x14).readUtf16String(len);
    } catch (e) {
        return "Read Error";
    }
}

function getModuleBase(name) {
    var mod = Process.findModuleByName(name);
    if (mod !== null) return mod.base;
    return null;
}

function hook() {
    console.log("==================================================");
    console.log("[Step 1] 开始批量 Hook...");

    var gameAssembly = getModuleBase("GameAssembly.dll");
    if (gameAssembly === null) {
        console.log("[-] 找不到 GameAssembly.dll，请检查进程名。");
        return;
    }
    console.log("[+] GameAssembly 基址: " + gameAssembly);

    // 遍历所有目标进行 Hook
    targets.forEach(function(target) {
        try {
            var func_addr = gameAssembly.add(target.offset);
            
            Interceptor.attach(func_addr, {
                onEnter: function(args) {
                    console.log("\n[!] >>> 捕获调用: " + target.name + " <<<");
                    
                    // 几乎所有 AuthCode 方法的前两个参数都是：
                    // args[0]: source (密文/明文) - String
                    // args[1]: key (密钥) - String
                    
                    try {
                        var arg0 = readIl2CppString(args[0]);
                        var arg1 = readIl2CppString(args[1]);
                        
                        console.log("    [-] 参数1 (Source/Data): " + arg0.substring(0, 100)); // 只打印前100字符防止刷屏
                        console.log("    [-] 参数2 (Key)        : " + arg1);
                        
                        // 如果是 Authcode 核心方法，还有 args[2] (operation)
                        if (target.name.indexOf("Authcode") !== -1) {
                             // operation 通常是 int (0=Encode, 1=Decode)
                             // 但在 x64 调用约定中，前4个参数在寄存器 RCX, RDX, R8, R9
                             // args[2] 对应 R8
                             console.log("    [-] 参数3 (Operation)  : " + args[2].toInt32());
                        }

                    } catch (e) {
                        console.log("    [-] 参数解析异常: " + e.message);
                    }
                },
                onLeave: function(retval) { }
            });
            
            console.log("[+] 已挂载: " + target.name + " @ " + func_addr);
        } catch (e) {
            console.log("[-] 挂载失败 " + target.name + ": " + e.message);
        }
    });
    
    console.log("==================================================");
    console.log("[*] 等待触发中... 请在游戏中进行操作 (登录/点击)");
}

setTimeout(hook, 1000);