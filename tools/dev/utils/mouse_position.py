import tkinter as tk
from tkinter import ttk
import pyautogui
import pygetwindow as gw
import threading
import time

# pip install pyautogui pillow pygetwindow psutil

class MouseCoordinateTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("鼠标坐标获取工具 - MaaFramework ROI Helper (带偏置修正)")
        self.root.geometry("600x400")
        self.root.attributes("-topmost", True)
        
        # 变量
        self.tracking = False
        self.selected_window = None
        self.offset_x = 0
        self.offset_y = 0
        
        self.setup_ui()
        self.update_coordinates()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 窗口选择区域
        ttk.Label(main_frame, text="目标窗口:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(main_frame, textvariable=self.window_var, width=50)
        self.window_combo.grid(row=0, column=1, columnspan=2, pady=5, padx=(10,0))
        
        ttk.Button(main_frame, text="刷新窗口列表", command=self.refresh_windows).grid(row=1, column=0, pady=5)
        ttk.Button(main_frame, text="自动选择焦点窗口", command=self.auto_select_window).grid(row=1, column=1, pady=5, padx=(10,0))
        
        # 偏置修正区域
        offset_frame = ttk.LabelFrame(main_frame, text="偏置修正设置", padding="10")
        offset_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 实际分辨率输入
        ttk.Label(offset_frame, text="游戏实际分辨率:").grid(row=0, column=0, sticky=tk.W)
        resolution_frame = ttk.Frame(offset_frame)
        resolution_frame.grid(row=0, column=1, sticky=tk.W, padx=(10,0))
        
        self.actual_width_var = tk.StringVar(value="1280")
        self.actual_height_var = tk.StringVar(value="720")
        
        ttk.Entry(resolution_frame, textvariable=self.actual_width_var, width=8).grid(row=0, column=0)
        ttk.Label(resolution_frame, text=" x ").grid(row=0, column=1)
        ttk.Entry(resolution_frame, textvariable=self.actual_height_var, width=8).grid(row=0, column=2)
        
        ttk.Button(offset_frame, text="自动计算偏移", command=self.auto_calculate_offset).grid(row=0, column=2, padx=(10,0))
        
        # 手动偏移设置
        ttk.Label(offset_frame, text="手动偏移 X:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.offset_x_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.offset_x_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10,0))
        
        ttk.Label(offset_frame, text="Y:").grid(row=1, column=2, sticky=tk.W, padx=(10,0))
        self.offset_y_var = tk.StringVar(value="0")
        ttk.Entry(offset_frame, textvariable=self.offset_y_var, width=10).grid(row=1, column=3, sticky=tk.W, padx=(5,0))
        
        ttk.Button(offset_frame, text="应用偏移", command=self.apply_offset).grid(row=1, column=4, padx=(10,0))
        
        # 预设偏移按钮
        preset_frame = ttk.Frame(offset_frame)
        preset_frame.grid(row=2, column=0, columnspan=5, sticky=tk.W, pady=5)
        
        ttk.Label(preset_frame, text="常用预设:").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(preset_frame, text="无边框(-8,-31)", command=lambda: self.set_preset(-8, -31)).grid(row=0, column=1, padx=(10,5))
        ttk.Button(preset_frame, text="标准边框(-8,-39)", command=lambda: self.set_preset(-8, -39)).grid(row=0, column=2, padx=5)
        ttk.Button(preset_frame, text="重置(0,0)", command=lambda: self.set_preset(0, 0)).grid(row=0, column=3, padx=5)
        
        # 当前偏移显示
        self.current_offset_label = ttk.Label(offset_frame, text="当前偏移: (0, 0)", foreground="green")
        self.current_offset_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 坐标显示区域
        coord_frame = ttk.LabelFrame(main_frame, text="坐标信息", padding="10")
        coord_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 屏幕绝对坐标
        ttk.Label(coord_frame, text="屏幕坐标:").grid(row=0, column=0, sticky=tk.W)
        self.screen_coord_label = ttk.Label(coord_frame, text="(0, 0)", font=("Consolas", 12))
        self.screen_coord_label.grid(row=0, column=1, sticky=tk.W, padx=(10,0))
        
        # 窗口原始相对坐标
        ttk.Label(coord_frame, text="原始窗口坐标:").grid(row=1, column=0, sticky=tk.W)
        self.original_coord_label = ttk.Label(coord_frame, text="(0, 0)", font=("Consolas", 12), foreground="gray")
        self.original_coord_label.grid(row=1, column=1, sticky=tk.W, padx=(10,0))
        
        # 修正后的窗口相对坐标
        ttk.Label(coord_frame, text="修正后坐标:").grid(row=2, column=0, sticky=tk.W)
        self.relative_coord_label = ttk.Label(coord_frame, text="(0, 0)", font=("Consolas", 12), foreground="blue")
        self.relative_coord_label.grid(row=2, column=1, sticky=tk.W, padx=(10,0))
        
        # 窗口信息
        ttk.Label(coord_frame, text="窗口信息:").grid(row=3, column=0, sticky=tk.W)
        self.window_info_label = ttk.Label(coord_frame, text="未选择窗口", font=("Consolas", 10))
        self.window_info_label.grid(row=3, column=1, sticky=tk.W, padx=(10,0))
        
        # ROI辅助区域
        roi_frame = ttk.LabelFrame(main_frame, text="ROI辅助", padding="10")
        roi_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(roi_frame, text="点击保存坐标点:").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(roi_frame, text="保存为起始点", command=self.save_start_point).grid(row=0, column=1, padx=(10,0))
        ttk.Button(roi_frame, text="保存为结束点", command=self.save_end_point).grid(row=0, column=2, padx=(5,0))
        
        self.start_point_label = ttk.Label(roi_frame, text="起始点: 未设置")
        self.start_point_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.end_point_label = ttk.Label(roi_frame, text="结束点: 未设置")
        self.end_point_label.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        self.roi_result_label = ttk.Label(roi_frame, text="ROI: 未计算", font=("Consolas", 12), foreground="red")
        self.roi_result_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        ttk.Button(roi_frame, text="复制ROI到剪贴板", command=self.copy_roi).grid(row=4, column=0, pady=5)
        ttk.Button(roi_frame, text="清除保存点", command=self.clear_points).grid(row=4, column=1, padx=(10,0), pady=5)
        
        # 初始化变量
        self.start_point = None
        self.end_point = None
        
        # 刷新窗口列表
        self.refresh_windows()
    
    def refresh_windows(self):
        """刷新可用窗口列表"""
        windows = gw.getAllWindows()
        window_titles = []
        self.windows_dict = {}
        
        for window in windows:
            if window.title and window.title.strip() and window.visible:
                display_name = f"{window.title[:50]}{'...' if len(window.title) > 50 else ''}"
                window_titles.append(display_name)
                self.windows_dict[display_name] = window
        
        self.window_combo['values'] = window_titles
        if window_titles:
            self.window_combo.set(window_titles[0])
            self.selected_window = self.windows_dict[window_titles[0]]
    
    def auto_select_window(self):
        """自动选择当前焦点窗口"""
        try:
            active_window = gw.getActiveWindow()
            if active_window and active_window.title:
                # 在下拉列表中查找匹配的窗口
                for display_name, window in self.windows_dict.items():
                    if window.title == active_window.title:
                        self.window_combo.set(display_name)
                        self.selected_window = window
                        break
        except:
            pass
    
    def auto_calculate_offset(self):
        """自动计算偏移量"""
        try:
            if not self.selected_window:
                tk.messagebox.showwarning("警告", "请先选择目标窗口")
                return
                
            actual_width = int(self.actual_width_var.get())
            actual_height = int(self.actual_height_var.get())
            
            detected_width = self.selected_window.width
            detected_height = self.selected_window.height
            
            # 计算偏移（通常边框在左侧和顶部）
            offset_x = (detected_width - actual_width) // 2
            offset_y = detected_height - actual_height - offset_x
            
            self.offset_x_var.set(str(-offset_x))
            self.offset_y_var.set(str(-offset_y))
            
            self.apply_offset()
            
            # 显示计算结果
            info = f"检测: {detected_width}x{detected_height}, 实际: {actual_width}x{actual_height}\n计算偏移: ({-offset_x}, {-offset_y})"
            tk.messagebox.showinfo("自动计算结果", info)
            
        except ValueError:
            tk.messagebox.showerror("错误", "请输入有效的分辨率数值")
        except Exception as e:
            tk.messagebox.showerror("错误", f"计算失败: {str(e)}")
    
    def set_preset(self, x, y):
        """设置预设偏移值"""
        self.offset_x_var.set(str(x))
        self.offset_y_var.set(str(y))
        self.apply_offset()
    
    def apply_offset(self):
        """应用偏移设置"""
        try:
            self.offset_x = int(self.offset_x_var.get())
            self.offset_y = int(self.offset_y_var.get())
            self.current_offset_label.config(text=f"当前偏移: ({self.offset_x}, {self.offset_y})")
        except ValueError:
            self.offset_x = 0
            self.offset_y = 0
            self.current_offset_label.config(text="当前偏移: (0, 0) - 输入无效")
    
    def update_coordinates(self):
        """更新坐标显示"""
        try:
            # 获取鼠标屏幕坐标
            mouse_x, mouse_y = pyautogui.position()
            self.screen_coord_label.config(text=f"({mouse_x}, {mouse_y})")
            
            # 获取选中窗口的相对坐标
            selected_display_name = self.window_var.get()
            if selected_display_name and selected_display_name in self.windows_dict:
                self.selected_window = self.windows_dict[selected_display_name]
                
                try:
                    # 计算原始相对坐标
                    original_rel_x = mouse_x - self.selected_window.left
                    original_rel_y = mouse_y - self.selected_window.top
                    
                    # 应用偏移修正
                    corrected_rel_x = original_rel_x + self.offset_x
                    corrected_rel_y = original_rel_y + self.offset_y
                    
                    self.original_coord_label.config(text=f"({original_rel_x}, {original_rel_y})")
                    self.relative_coord_label.config(text=f"({corrected_rel_x}, {corrected_rel_y})")
                    self.window_info_label.config(
                        text=f"位置: ({self.selected_window.left}, {self.selected_window.top}) "
                             f"大小: {self.selected_window.width}x{self.selected_window.height}"
                    )
                except:
                    self.original_coord_label.config(text="窗口无效")
                    self.relative_coord_label.config(text="窗口无效")
                    self.window_info_label.config(text="无法获取窗口信息")
            else:
                self.original_coord_label.config(text="未选择窗口")
                self.relative_coord_label.config(text="未选择窗口")
                self.window_info_label.config(text="请选择目标窗口")
                
        except Exception as e:
            self.screen_coord_label.config(text="获取失败")
            self.original_coord_label.config(text="获取失败")
            self.relative_coord_label.config(text="获取失败")
        
        # 每100ms更新一次
        self.root.after(100, self.update_coordinates)
    
    def save_start_point(self):
        """保存起始点（使用修正后的坐标）"""
        try:
            mouse_x, mouse_y = pyautogui.position()
            if self.selected_window:
                original_rel_x = mouse_x - self.selected_window.left
                original_rel_y = mouse_y - self.selected_window.top
                corrected_rel_x = original_rel_x + self.offset_x
                corrected_rel_y = original_rel_y + self.offset_y
                
                self.start_point = (corrected_rel_x, corrected_rel_y)
                self.start_point_label.config(text=f"起始点: ({corrected_rel_x}, {corrected_rel_y})")
                self.calculate_roi()
        except:
            pass
    
    def save_end_point(self):
        """保存结束点（使用修正后的坐标）"""
        try:
            mouse_x, mouse_y = pyautogui.position()
            if self.selected_window:
                original_rel_x = mouse_x - self.selected_window.left
                original_rel_y = mouse_y - self.selected_window.top
                corrected_rel_x = original_rel_x + self.offset_x
                corrected_rel_y = original_rel_y + self.offset_y
                
                self.end_point = (corrected_rel_x, corrected_rel_y)
                self.end_point_label.config(text=f"结束点: ({corrected_rel_x}, {corrected_rel_y})")
                self.calculate_roi()
        except:
            pass
    
    def calculate_roi(self):
        """计算ROI"""
        if self.start_point and self.end_point:
            x1, y1 = self.start_point
            x2, y2 = self.end_point
            
            # 确保左上角为起始点
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            roi_text = f"[{left}, {top}, {width}, {height}]"
            self.roi_result_label.config(text=f"ROI: {roi_text}")
            self.current_roi = roi_text
        else:
            self.roi_result_label.config(text="ROI: 需要设置起始点和结束点")
            self.current_roi = None
    
    def copy_roi(self):
        """复制ROI到剪贴板"""
        if hasattr(self, 'current_roi') and self.current_roi:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_roi)
            # 临时显示复制成功
            original_text = self.roi_result_label.cget("text")
            self.roi_result_label.config(text=f"{original_text} (已复制!)")
            self.root.after(2000, lambda: self.roi_result_label.config(text=original_text))
    
    def clear_points(self):
        """清除保存的点"""
        self.start_point = None
        self.end_point = None
        self.start_point_label.config(text="起始点: 未设置")
        self.end_point_label.config(text="结束点: 未设置")
        self.roi_result_label.config(text="ROI: 未计算")

def main():
    root = tk.Tk()
    app = MouseCoordinateTracker(root)
    root.mainloop()

if __name__ == "__main__":
    main()