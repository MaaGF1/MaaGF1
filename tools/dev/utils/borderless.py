import tkinter as tk
from tkinter import ttk, messagebox
import pygetwindow as gw
import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes
import time

class WindowOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("GFL Borderless")
        self.root.geometry("600x700")
        self.root.attributes("-topmost", True)
        
        self.selected_window = None
        self.original_style = None
        self.original_ex_style = None
        self.original_rect = None
        self.calculated_size = None
        
        self.setup_ui()
        self.refresh_windows()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 窗口选择
        window_frame = ttk.LabelFrame(main_frame, text="窗口选择", padding="10")
        window_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(window_frame, text="目标窗口:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(window_frame, textvariable=self.window_var, width=50)
        self.window_combo.grid(row=0, column=1, columnspan=2, pady=5, padx=(10,0))
        self.window_combo.bind('<<ComboboxSelected>>', self.on_window_selected)
        
        ttk.Button(window_frame, text="刷新窗口列表", command=self.refresh_windows).grid(row=1, column=0, pady=5)
        ttk.Button(window_frame, text="自动选择焦点窗口", command=self.auto_select_window).grid(row=1, column=1, pady=5, padx=(10,0))
        
        # DPI和分辨率
        dpi_frame = ttk.LabelFrame(main_frame, text="DPI和分辨率", padding="10")
        dpi_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(dpi_frame, text="分析DPI设置", command=self.analyze_dpi).grid(row=0, column=0, pady=5)
        ttk.Button(dpi_frame, text="检测游戏分辨率", command=self.detect_game_resolution).grid(row=0, column=1, padx=(10,0), pady=5)
        
        self.dpi_info_label = ttk.Label(dpi_frame, text="DPI信息: 未检测", foreground="blue")
        self.dpi_info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 分辨率设置
        resolution_frame = ttk.LabelFrame(main_frame, text="分辨率设置", padding="10")
        resolution_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        target_frame = ttk.Frame(resolution_frame)
        target_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Label(target_frame, text="目标游戏分辨率:").grid(row=0, column=0, sticky=tk.W)
        self.target_width_var = tk.StringVar(value="1280")
        self.target_height_var = tk.StringVar(value="720")
        
        ttk.Entry(target_frame, textvariable=self.target_width_var, width=8).grid(row=0, column=1, padx=(10,0))
        ttk.Label(target_frame, text=" x ").grid(row=0, column=2)
        ttk.Entry(target_frame, textvariable=self.target_height_var, width=8).grid(row=0, column=3)
        
        # DPI设置
        dpi_aware_frame = ttk.Frame(resolution_frame)
        dpi_aware_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        self.dpi_aware_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dpi_aware_frame, text="启用DPI感知", 
                       variable=self.dpi_aware_var).grid(row=0, column=0, sticky=tk.W)
        
        self.force_dpi_var = tk.StringVar(value="96")
        ttk.Label(dpi_aware_frame, text="强制DPI:").grid(row=0, column=1, padx=(20,5), sticky=tk.W)
        ttk.Entry(dpi_aware_frame, textvariable=self.force_dpi_var, width=8).grid(row=0, column=2)
        
        # 优化操作
        optimize_frame = ttk.LabelFrame(main_frame, text="窗口优化", padding="10")
        optimize_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        button_frame = ttk.Frame(optimize_frame)
        button_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Button(button_frame, text="执行优化", command=self.execute_optimization, 
                  style="Accent.TButton").grid(row=0, column=0, padx=(0,10))
        ttk.Button(button_frame, text="还原窗口", command=self.restore_original_state).grid(row=0, column=1, padx=(0,10))
        ttk.Button(button_frame, text="验证结果", command=self.verify_result).grid(row=0, column=2, padx=(0,10))
        
        # 高级选项
        advanced_frame = ttk.LabelFrame(main_frame, text="高级选项", padding="10")
        advanced_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.disable_dwm_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="禁用DWM效果", 
                       variable=self.disable_dwm_var).grid(row=0, column=0, sticky=tk.W)
        
        self.topmost_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(advanced_frame, text="窗口置顶", 
                       variable=self.topmost_var).grid(row=1, column=0, sticky=tk.W)
        
        self.precise_positioning_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(advanced_frame, text="精确定位", 
                       variable=self.precise_positioning_var).grid(row=2, column=0, sticky=tk.W)
        
        # 状态显示
        self.status_label = ttk.Label(main_frame, text="就绪", foreground="green")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.calculation_label = ttk.Label(main_frame, text="", foreground="blue", font=("Consolas", 9))
        self.calculation_label.grid(row=6, column=0, columnspan=2, pady=5)
    
    def refresh_windows(self):
        windows = gw.getAllWindows()
        window_titles = []
        self.windows_dict = {}
        
        for window in windows:
            if window.title and window.title.strip() and window.visible:
                title = window.title
                if any(keyword in title.lower() for keyword in ['少女前线', 'girls', 'frontline', 'game']):
                    display_name = f"[游戏] {title[:40]}{'...' if len(title) > 40 else ''}"
                else:
                    display_name = f"{title[:45]}{'...' if len(title) > 45 else ''}"
                    
                window_titles.append(display_name)
                self.windows_dict[display_name] = window
        
        self.window_combo['values'] = window_titles
        if window_titles:
            game_windows = [w for w in window_titles if w.startswith('[游戏]')]
            if game_windows:
                self.window_combo.set(game_windows[0])
            else:
                self.window_combo.set(window_titles[0])
    
    def auto_select_window(self):
        try:
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                for display_name, window in self.windows_dict.items():
                    if window.title == active_window.title:
                        self.window_combo.set(display_name)
                        self.on_window_selected()
                        break
        except Exception as e:
            self.update_status(f"自动选择失败: {str(e)}", "error")
    
    def on_window_selected(self, event=None):
        selected_display_name = self.window_var.get()
        if selected_display_name and selected_display_name in self.windows_dict:
            self.selected_window = self.windows_dict[selected_display_name]
            self.analyze_dpi()
    
    def analyze_dpi(self):
        if not self.selected_window:
            return
        
        try:
            hwnd = self.selected_window._hWnd
            
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            
            try:
                dpi = user32.GetDpiForWindow(hwnd)
            except:
                dpi = 96
            
            dc = user32.GetDC(0)
            system_dpi_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
            system_dpi_y = ctypes.windll.gdi32.GetDeviceCaps(dc, 90)
            user32.ReleaseDC(0, dc)
            
            scale_factor = dpi / 96.0
            
            self.dpi_info_label.config(
                text=f"窗口DPI: {dpi}, 系统DPI: {system_dpi_x}x{system_dpi_y}, 缩放: {scale_factor:.2f}x"
            )
            
            return dpi, scale_factor
            
        except Exception as e:
            self.dpi_info_label.config(text=f"DPI检测失败: {str(e)}")
            return 96, 1.0
    
    def detect_game_resolution(self):
        if not self.selected_window:
            messagebox.showwarning("警告", "请先选择目标窗口")
            return
        
        try:
            hwnd = self.selected_window._hWnd
            
            client_rect = win32gui.GetClientRect(hwnd)
            client_width = client_rect[2]
            client_height = client_rect[3]
            
            window_rect = win32gui.GetWindowRect(hwnd)
            window_width = window_rect[2] - window_rect[0]
            window_height = window_rect[3] - window_rect[1]
            
            border_width = (window_width - client_width) // 2
            border_height = window_height - client_height - border_width
            
            common_ratios = [
                (1280, 720),
                (1920, 1080),
                (1366, 768),
                (1600, 900),
                (1440, 810),
            ]
            
            client_ratio = client_width / client_height if client_height > 0 else 0
            best_match = None
            min_diff = float('inf')
            
            for w, h in common_ratios:
                ratio = w / h
                diff = abs(ratio - client_ratio)
                if diff < min_diff:
                    min_diff = diff
                    best_match = (w, h)
            
            info = f"""检测结果:
客户区域: {client_width} x {client_height}
窗口总尺寸: {window_width} x {window_height}
边框估算: 左右各{border_width}px, 顶部{border_height}px
当前比例: {client_ratio:.3f}
推荐分辨率: {best_match[0]} x {best_match[1]}"""
            
            messagebox.showinfo("分辨率检测", info)
            
            if best_match:
                self.target_width_var.set(str(best_match[0]))
                self.target_height_var.set(str(best_match[1]))
            
        except Exception as e:
            messagebox.showerror("错误", f"检测失败: {str(e)}")
    
    def save_original_state(self):
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            self.original_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            self.original_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            self.original_rect = win32gui.GetWindowRect(hwnd)
            return True
        except Exception as e:
            self.update_status(f"保存状态失败: {str(e)}", "error")
            return False
    
    def set_dpi_awareness(self):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except:
                pass
            return True
        except Exception as e:
            self.update_status(f"设置DPI感知失败: {str(e)}", "error")
            return False
    
    def remove_window_decorations(self):
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            
            current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            current_ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            
            new_style = current_style
            new_style &= ~win32con.WS_CAPTION
            new_style &= ~win32con.WS_THICKFRAME
            new_style &= ~win32con.WS_BORDER
            new_style &= ~win32con.WS_DLGFRAME
            new_style &= ~win32con.WS_SYSMENU
            new_style &= ~win32con.WS_MINIMIZEBOX
            new_style &= ~win32con.WS_MAXIMIZEBOX
            
            new_ex_style = current_ex_style
            new_ex_style &= ~win32con.WS_EX_DLGMODALFRAME
            new_ex_style &= ~win32con.WS_EX_CLIENTEDGE
            new_ex_style &= ~win32con.WS_EX_STATICEDGE
            new_ex_style &= ~win32con.WS_EX_WINDOWEDGE
            
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
            
            if self.disable_dwm_var.get():
                self.disable_dwm_effects(hwnd)
            
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | 
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            
            return True
        except Exception as e:
            self.update_status(f"移除装饰失败: {str(e)}", "error")
            return False
    
    def calculate_correct_size(self):
        if not self.selected_window:
            return False
        
        try:
            target_width = int(self.target_width_var.get())
            target_height = int(self.target_height_var.get())
            
            # 重新分析DPI（移除边框后可能发生变化）
            dpi, scale_factor = self.analyze_dpi()
            
            if self.dpi_aware_var.get():
                if self.force_dpi_var.get():
                    force_dpi = int(self.force_dpi_var.get())
                    dpi_scale = force_dpi / 96.0
                else:
                    dpi_scale = scale_factor
                
                actual_width = int(target_width / dpi_scale)
                actual_height = int(target_height / dpi_scale)
            else:
                actual_width = target_width
                actual_height = target_height
            
            self.calculated_size = (actual_width, actual_height)
            
            calculation_info = f"计算结果: 目标{target_width}x{target_height} → 实际设置{actual_width}x{actual_height} (DPI缩放: {scale_factor:.2f})"
            self.calculation_label.config(text=calculation_info)
            
            return True
            
        except ValueError:
            self.update_status("请输入有效的分辨率数值", "error")
            return False
        except Exception as e:
            self.update_status(f"计算尺寸失败: {str(e)}", "error")
            return False
    
    def apply_final_size(self):
        if not hasattr(self, 'calculated_size') or not self.calculated_size:
            return False
        
        if not self.selected_window:
            return False
        
        try:
            hwnd = self.selected_window._hWnd
            width, height = self.calculated_size
            
            current_rect = win32gui.GetWindowRect(hwnd)
            current_x = current_rect[0]
            current_y = current_rect[1]
            
            if self.precise_positioning_var.get():
                screen_width = win32api.GetSystemMetrics(0)
                screen_height = win32api.GetSystemMetrics(1)
                
                if current_x + width > screen_width:
                    current_x = screen_width - width
                if current_y + height > screen_height:
                    current_y = screen_height - height
                if current_x < 0:
                    current_x = 0
                if current_y < 0:
                    current_y = 0
            
            win32gui.SetWindowPos(hwnd, 0, current_x, current_y, width, height, 
                                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
            
            if self.topmost_var.get():
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            
            return True
        except Exception as e:
            self.update_status(f"应用尺寸失败: {str(e)}", "error")
            return False
    
    def execute_optimization(self):
        if not self.selected_window:
            messagebox.showwarning("警告", "请先选择目标窗口")
            return
        
        try:
            self.update_status("开始优化...", "info")
            
            # 步骤1: 保存原始状态
            if not self.save_original_state():
                return
            time.sleep(0.2)
            
            # 步骤2: 设置DPI感知
            if not self.set_dpi_awareness():
                return
            time.sleep(0.2)
            
            # 步骤3: 移除边框
            if not self.remove_window_decorations():
                return
            time.sleep(0.5)  # 重要：等待边框移除完成
            
            # 步骤4: 计算正确尺寸（移除边框后重新计算）
            if not self.calculate_correct_size():
                return
            time.sleep(0.2)
            
            # 步骤5: 应用最终尺寸
            if not self.apply_final_size():
                return
            time.sleep(0.5)  # 重要：等待尺寸应用完成
            
            self.update_status("优化完成", "success")
            
        except Exception as e:
            self.update_status(f"优化失败: {str(e)}", "error")
    
    def disable_dwm_effects(self, hwnd):
        try:
            dwmapi = ctypes.windll.dwmapi
            
            try:
                corner_preference = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_preference), 4)
            except:
                pass
            
            try:
                no_shadow = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(no_shadow), 4)
            except:
                pass
            
        except Exception as e:
            print(f"禁用DWM效果失败: {str(e)}")
    
    def verify_result(self):
        if not self.selected_window:
            messagebox.showwarning("警告", "请先选择目标窗口")
            return
        
        try:
            hwnd = self.selected_window._hWnd
            
            window_rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)
            
            window_width = window_rect[2] - window_rect[0]
            window_height = window_rect[3] - window_rect[1]
            client_width = client_rect[2]
            client_height = client_rect[3]
            
            target_width = int(self.target_width_var.get())
            target_height = int(self.target_height_var.get())
            
            result = f"""验证结果:
目标分辨率: {target_width} x {target_height}
当前窗口尺寸: {window_width} x {window_height}
当前客户区: {client_width} x {client_height}

匹配度:
- 宽度: {'完全匹配' if abs(client_width - target_width) <= 2 else f'差异 {abs(client_width - target_width)}px'}
- 高度: {'完全匹配' if abs(client_height - target_height) <= 2 else f'差异 {abs(client_height - target_height)}px'}

边框状态: {'无边框' if window_width == client_width and window_height == client_height else '仍有边框'}

状态: {'已优化完成' if abs(client_width - target_width) <= 2 and abs(client_height - target_height) <= 2 else '需要重新优化'}"""
            
            messagebox.showinfo("验证结果", result)
            
        except Exception as e:
            messagebox.showerror("错误", f"验证失败: {str(e)}")
    
    def restore_original_state(self):
        if not self.selected_window or not self.original_style:
            messagebox.showwarning("警告", "没有保存的原始状态")
            return
        
        try:
            hwnd = self.selected_window._hWnd
            
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, self.original_style)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, self.original_ex_style)
            
            if self.original_rect:
                x, y, right, bottom = self.original_rect
                width = right - x
                height = bottom - y
                win32gui.SetWindowPos(hwnd, 0, x, y, width, height, win32con.SWP_NOZORDER)
            
            win32gui.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 
                                win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | 
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
            
            self.update_status("已还原", "success")
            
        except Exception as e:
            self.update_status(f"还原失败: {str(e)}", "error")
    
    def update_status(self, message, status_type="info"):
        colors = {
            "success": "green",
            "error": "red", 
            "warning": "orange",
            "info": "blue"
        }
        
        self.status_label.config(text=message, foreground=colors.get(status_type, "black"))
        self.root.update()

def main():
    try:
        import win32gui
        import win32con
        import win32api
    except ImportError:
        messagebox.showerror("错误", "缺少必要的库，请安装：\npip install pywin32")
        return
    
    root = tk.Tk()
    app = WindowOptimizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()