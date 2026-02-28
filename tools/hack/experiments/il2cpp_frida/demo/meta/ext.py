import re
import string

def extract_strings_from_binary(file_path, min_length=4):
    """
    从二进制文件中暴力提取所有 ASCII 和 UTF-8 字符串
    """
    print(f"[*] 正在分析文件: {file_path}")
    
    with open(file_path, 'rb') as f:
        data = f.read()

    # 1. 提取 ASCII 字符串 (包括英文、数字、符号)
    # 正则解释：查找连续 4 个以上可打印字符
    ascii_pattern = re.compile(b'[ -~]{' + str(min_length).encode() + b',}')
    ascii_strings = ascii_pattern.findall(data)

    print(f"[+] 找到 {len(ascii_strings)} 个 ASCII 字符串")
    
    # 保存 ASCII 结果
    with open(file_path + "_strings_ascii.txt", "w", encoding="utf-8") as out:
        for s in ascii_strings:
            try:
                decoded = s.decode('utf-8')
                out.write(decoded + "\n")
            except:
                pass

    # 2. 尝试提取 UTF-8 字符串 (包含中文)
    # 这是一个简单的启发式方法，可能会有一些误报
    print("[*] 正在尝试提取包含中文的 UTF-8 字符串...")
    
    found_utf8 = []
    current_bytes = bytearray()
    
    # 过滤掉控制字符，保留常见文本范围
    def is_valid_byte(b):
        return b == 0x09 or b == 0x0A or b == 0x0D or (0x20 <= b <= 0x7E) or (b >= 0xC2)
    
    for byte in data:
        if is_valid_byte(byte):
            current_bytes.append(byte)
        else:
            if len(current_bytes) >= min_length:
                try:
                    # 尝试解码，如果成功且包含非ASCII字符(通常是中文)，则保留
                    text = current_bytes.decode('utf-8')
                    # 简单的过滤：去除纯乱码
                    if any('\u4e00' <= char <= '\u9fff' for char in text) or len(text) > 8:
                         found_utf8.append(text)
                except:
                    pass
            current_bytes = bytearray()

    print(f"[+] 找到 {len(found_utf8)} 个潜在的 UTF-8/中文 字符串")

    # 保存 UTF-8 结果
    with open(file_path + "_strings_utf8.txt", "w", encoding="utf-8") as out:
        for s in found_utf8:
            out.write(s + "\n")

    print("[*] 提取完成！请查看生成的 .txt 文件。")

if __name__ == "__main__":
    # 将此处替换为你 dump 出来的那个文件名
    DUMPED_FILE = "dump_1_0x18d68eec040.dat" 
    extract_strings_from_binary(DUMPED_FILE)