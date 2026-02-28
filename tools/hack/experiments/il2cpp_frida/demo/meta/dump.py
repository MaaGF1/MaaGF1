import pymem
import pymem.process
import pymem.pattern
import os
import sys

class MetadataDumper:
    def __init__(self, process_name: str, target_size_bytes: int):
        self.process_name = process_name
        # 依然读取 原始大小 + 1MB，防止溢出
        self.dump_size = target_size_bytes + (1 * 1024 * 1024) 
        self.pm = None

    def attach(self):
        try:
            self.pm = pymem.Pymem(self.process_name)
            print(f"[+] 成功挂载到进程: {self.process_name} (PID: {self.pm.process_id})")
        except Exception as e:
            print(f"[-] 无法找到或挂载进程 '{self.process_name}'。请确认游戏已运行。")
            sys.exit(1)

    def scan_and_dump_all(self):
        print("[*] 开始扫描内存中 *所有* 的 global-metadata 特征码...")
        
        # 特征码：魔数
        signature = b'\xAF\x1B\xB1\xFA'
        
        try:
            # 关键修改：return_multiple=True，寻找所有匹配项
            results = pymem.pattern.pattern_scan_all(self.pm.process_handle, signature, return_multiple=True)
            
            if not results:
                print("[-] 未能在内存中找到任何特征码。可能头部被抹除或加密方式改变。")
                return

            print(f"[!] 找到 {len(results)} 个潜在地址。开始逐个提取...")

            for index, address in enumerate(results):
                print(f"\n--- 处理第 {index + 1} 个地址: {hex(address)} ---")
                self.dump_to_file(address, index)

        except Exception as e:
            print(f"[-] 扫描过程中出错: {e}")

    def dump_to_file(self, address, index):
        try:
            # 尝试直接读取
            data = self.pm.read_bytes(address, self.dump_size)
            self._save(data, index, address)
            
        except pymem.exception.MemoryReadError:
            print(f"[-] 地址 {hex(address)} 读取失败 (Error 299)，尝试安全读取...")
            self._safe_dump(address, index)
        except Exception as e:
            print(f"[-] 未知错误: {e}")

    def _safe_dump(self, start_address, index):
        buffer = bytearray()
        chunk_size = 1024 
        current_addr = start_address
        bytes_read = 0
        
        while bytes_read < self.dump_size:
            try:
                chunk = self.pm.read_bytes(current_addr, chunk_size)
                buffer.extend(chunk)
                current_addr += chunk_size
                bytes_read += chunk_size
            except Exception:
                break
        
        if len(buffer) > 1024 * 1024: 
            self._save(buffer, index, start_address)
        else:
            print("[-] 数据过少，跳过保存。")

    def _save(self, data, index, address):
        # 文件名带上地址，方便区分
        filename = f"dump_{index}_{hex(address)}.dat"
        with open(filename, "wb") as f:
            f.write(data)
        print(f"[+] 已保存: {filename} (大小: {len(data)} bytes)")
        self._check_if_decrypted(data)

    def _check_if_decrypted(self, data):
        """
        简单的启发式检查：查看是否包含常见明文字符串
        """
        # 检查数据中是否包含 "UnityEngine" 或 "System" 这种常见的类名
        # 解密后的 Metadata 应该能看到大量的明文类名
        sample = data[:1024*1024] # 只检查前1MB
        if b'UnityEngine' in sample or b'm_scor' in sample or b'System.String' in sample:
            print(f"    [★] 提示: 这个文件看起来像是解密后的！(发现了明文字符串)")
        else:
            print(f"    [!] 提示: 这个文件看起来依然是加密的/乱码。")

if __name__ == "__main__":
    TARGET_PROCESS = "GrilsFrontLine.exe" 
    # 你的文件原始大小
    ORIGINAL_FILE_SIZE = 32880320 
    
    dumper = MetadataDumper(TARGET_PROCESS, ORIGINAL_FILE_SIZE)
    dumper.attach()
    dumper.scan_and_dump_all()