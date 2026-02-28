// hook_respon.js

var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip

function getCSharpByteArray(ptr) {
    if (ptr.isNull()) return null;
    try {
        // C# 数组结构: [ClassPtr][Monitor][Length][Data...]
        // 0x18 偏移通常是 Length (32位整数)
        var len = ptr.add(0x18).readU32();
        
        // 0x20 偏移是数据开始的地方
        var dataPtr = ptr.add(0x20);
        
        // 读取整个字节数组
        var bytes = dataPtr.readByteArray(len);
        return bytes;

    } catch (e) {
        console.log("[JS Error] 读取数组失败: " + e.message);
        return null;
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
                // 读取完整的二进制数据
                var data = getCSharpByteArray(retval);
                
                if (data) {
                    // 发送给 Python 端
                    // 第一个参数是消息对象，第二个参数是二进制数据(ArrayBuffer)
                    send({ id: "gzip_data" }, data);
                }
            }
        }
    });

    console.log("[JS] Hook 就绪，数据将自动发送至 Python 解压...");
}

setTimeout(hook, 1000);