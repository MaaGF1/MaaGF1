var addr_DecodeWithGzip = 21054368; // AC.AuthCode$$DecodeWithGzip

// 辅助函数：读取 C# 字节数组
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

// 辅助函数：覆写 C# 字节数组
function writeCSharpByteArray(ptr, newData) {
    if (ptr.isNull()) return false;
    
    // 获取原数组容量（这里简化认为当前长度即为容量）
    var originalLen = ptr.add(0x18).readU32();
    var newLen = newData.byteLength;
    
    // 安全检查：如果新数据比原空间大，不能直接写，否则会覆盖后面的内存导致崩溃
    // 除非我们能调用 C# 的 new byte[]，但在纯 JS 裸指针操作下，我们只能利用现有空间。
    // 这就是为什么 Python 端要用最高压缩率的原因。
    if (newLen > originalLen) {
        console.log("[JS Danger] ⚠️ 新数据长度 (" + newLen + ") 超过原数组容量 (" + originalLen + ")！");
        console.log("[JS Danger] ❌ 放弃修改，防止游戏崩溃。");
        return false;
    }

    try {
        // 1. 更新数组长度字段
        ptr.add(0x18).writeU32(newLen);
        
        // 2. 写入新数据
        var dataPtr = ptr.add(0x20);
        dataPtr.writeByteArray(newData);
        
        // 3. (可选) 清除剩余的旧数据，虽然更新了长度通常不需要，但为了干净
        if (newLen < originalLen) {
            // 填充 0
            // dataPtr.add(newLen).writeByteArray(new ArrayBuffer(originalLen - newLen));
        }
        
        return true;
    } catch (e) {
        console.log("[JS Error] 写入失败: " + e.message);
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
                    // 1. 发送请求给 Python
                    send({ id: "req_modify" }, originalData);
                    
                    // 2. 【关键】同步等待 Python 的回复
                    // recv().wait() 会阻塞游戏线程，直到 Python 发回消息
                    var received = recv('resp_modify', function(msg, data) {
                        
                        if (msg.payload === 'modified' && data) {
                            console.log("[JS] 收到修改后的数据，准备覆写内存...");
                            
                            // 3. 覆写内存
                            var success = writeCSharpByteArray(retval, data);
                            if (success) {
                                console.log("[JS] ✅ 内存覆写成功！user_exp 已修改。");
                            }
                        } else {
                            console.log("[JS] 保持原数据。");
                        }
                    });
                    
                    received.wait(); // 阻塞在这里
                }
            }
        }
    });

    console.log("[JS] Hook 就绪 (同步阻塞模式)");
}

setTimeout(hook, 1000);