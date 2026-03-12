import xspeedhack as xsh
import time
import psutil
import logging
import threading
from typing import Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('speedhack.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class GameSpeedController:
    def __init__(self, process_name: str = "GrilsFrontLine.exe", arch: str = "x64"):
        self.process_name = process_name
        self.arch = arch
        self.client: Optional[xsh.Client] = None
        self.current_speed = 1.0
        self.is_connected = False
        
        # 线程控制
        self.is_running = False
        self.exit_event = threading.Event()
        self.log_thread = None
        self.input_thread = None
        
    def find_and_connect(self) -> bool:
        """查找并连接到游戏进程"""
        try:
            self.client = xsh.Client(self.process_name, arch=self.arch)
            self.is_connected = True
            logging.info(f"成功连接到进程: {self.process_name}")
            return True
            
        except Exception as e:
            try:
                pid = self._find_process_pid()
                if pid:
                    self.client = xsh.Client(process_id=pid, arch=self.arch)
                    self.is_connected = True
                    logging.info(f"成功连接到进程PID: {pid}")
                    return True
            except Exception as e2:
                logging.error(f"连接失败: {e2}")
                
        self.is_connected = False
        return False
    
    def _find_process_pid(self) -> Optional[int]:
        """查找游戏进程PID"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == self.process_name.lower():
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def set_speed(self, speed: float) -> bool:
        """设置游戏速度"""
        if not self.is_connected or not self.client:
            logging.warning("未连接到游戏进程")
            return False
            
        try:
            self.client.set_speed(speed)
            self.current_speed = speed
            logging.info(f"游戏速度已设置为: {speed}x")
            return True
        except Exception as e:
            logging.error(f"设置速度失败: {e}")
            self.is_connected = False
            return False
    
    def reset_speed(self) -> bool:
        """重置游戏速度为正常"""
        return self.set_speed(1.0)
    
    def is_process_running(self) -> bool:
        """检查游戏进程是否仍在运行"""
        return self._find_process_pid() is not None
    
    def _status_log_loop(self, interval: int = 10):
        """定时打印状态日志的线程函数"""
        start_time = datetime.now()
        
        while not self.exit_event.is_set():
            if self.exit_event.wait(timeout=interval):
                break
                
            # 计算运行时间
            elapsed = datetime.now() - start_time
            # 去掉微秒
            elapsed_str = str(elapsed).split('.')[0]
            
            # 检查进程状态
            process_status = "运行中" if self.is_process_running() else "未找到"
            connection_status = "已连接" if self.is_connected else "未连接"
            
            # 打印状态信息
            status_msg = (
                f"[状态报告] 运行时间: {elapsed_str} | "
                f"进程状态: {process_status} | "
                f"连接状态: {connection_status} | "
                f"当前速度: {self.current_speed}x"
            )
            
            print(f"\033[92m{status_msg}\033[0m")
            
            # 如果进程不存在但仍显示连接，尝试重新连接
            if not self.is_process_running() and self.is_connected:
                logging.warning("检测到游戏进程已结束")
                self.is_connected = False
    
    def _input_monitor_loop(self):
        """监听用户输入的线程函数"""
        print("\n" + "="*50)
        print("输入命令:")
        print("   q - 退出程序并重置速度")
        print("   s - 设置新的速度倍数")
        print("   r - 重置速度为1.0x")
        print("   i - 显示当前状态信息")
        print("="*50)
        
        while not self.exit_event.is_set():
            try:
                user_input = input("请输入命令 (q/s/r/i): ").strip().lower()
                
                if user_input == 'q':
                    print("正在退出程序...")
                    self.exit_event.set()
                    break
                elif user_input == 's':
                    try:
                        new_speed = float(input("请输入新的速度倍数: "))
                        if new_speed > 0:
                            if self.set_speed(new_speed):
                                print(f"速度已设置为: {new_speed}x")
                            else:
                                print("设置速度失败")
                        else:
                            print("速度必须大于0")
                    except ValueError:
                        print("请输入有效的数字")
                elif user_input == 'r':
                    if self.reset_speed():
                        print("速度已重置为正常 (1.0x)")
                    else:
                        print("重置速度失败")
                elif user_input == 'i':
                    self._print_status_info()
                elif user_input == '':
                    continue
                else:
                    print("未知命令，请输入 q/s/r/i")
                    
            except (EOFError, KeyboardInterrupt):
                print("\n检测到中断信号，正在退出...")
                self.exit_event.set()
                break
            except Exception as e:
                logging.error(f"输入处理错误: {e}")
    
    def _print_status_info(self):
        """打印详细状态信息"""
        pid = self._find_process_pid()
        print("\n" + "="*40)
        print("当前状态信息:")
        print(f"   进程名称: {self.process_name}")
        print(f"   进程ID: {pid if pid else '未找到'}")
        print(f"   架构: {self.arch}")
        print(f"   连接状态: {'已连接' if self.is_connected else '未连接'}")
        print(f"   当前速度: {self.current_speed}x")
        print(f"   进程运行: {'是' if self.is_process_running() else '否'}")
        print("="*40 + "\n")
    
    def start_interactive_mode(self, initial_speed: float = 10.0, log_interval: int = 10):
        """启动交互式模式"""
        # 首先尝试连接
        if not self.find_and_connect():
            print("无法连接到游戏进程，请确保游戏正在运行")
            return False
        
        # 设置初始速度
        if not self.set_speed(initial_speed):
            print("设置初始速度失败")
            return False
        
        print(f"已连接到游戏进程，当前速度: {initial_speed}x")
        
        # 启动监控线程
        self.is_running = True
        self.log_thread = threading.Thread(target=self._status_log_loop, args=(log_interval,), daemon=True)
        self.input_thread = threading.Thread(target=self._input_monitor_loop, daemon=True)
        
        self.log_thread.start()
        self.input_thread.start()
        
        # 等待退出信号
        try:
            self.exit_event.wait()
        except KeyboardInterrupt:
            print("\n收到键盘中断信号")
            self.exit_event.set()
        
        # 清理工作
        self._cleanup()
        return True
    
    def _cleanup(self):
        """清理资源"""
        print("正在进行清理工作...")
        
        # 重置游戏速度
        if self.is_connected:
            if self.reset_speed():
                print("游戏速度已重置为正常")
            else:
                print("重置游戏速度失败，请手动检查")
        
        # 等待线程结束
        self.is_running = False
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=2)
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=2)
        
        print("清理完成，程序已安全退出")

def main():
    """主函数"""
    try:
        controller = GameSpeedController("GrilsFrontLine.exe", "x64")
        
        # 启动交互式模式，初始速度10x，每10秒打印一次状态
        success = controller.start_interactive_mode(initial_speed=10.0, log_interval=10)
        
        if not success:
            print("程序启动失败")
            return 1
            
        return 0
        
    except Exception as e:
        logging.error(f"程序运行错误: {e}")
        return 1

if __name__ == "__main__":
    exit(main())