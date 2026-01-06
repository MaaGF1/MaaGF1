import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading

class ImageCropTool:
    def __init__(self, root):
        self.root = root
        self.root.title("图片剪裁工具 - Image Crop Helper")
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True)
        
        # 变量
        self.current_directory = ""
        self.image_files = []
        self.current_image_path = ""
        self.original_image = None
        self.preview_image = None
        self.crop_preview_image = None
        
        # 预览相关
        self.canvas_width = 400
        self.canvas_height = 300
        self.scale_factor = 1.0
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="选择目录", command=self.select_directory).grid(row=0, column=0, sticky=tk.W)
        self.directory_label = ttk.Label(file_frame, text="未选择目录", foreground="gray")
        self.directory_label.grid(row=0, column=1, sticky=tk.W, padx=(10,0))
        
        ttk.Label(file_frame, text="PNG文件:").grid(row=1, column=0, sticky=tk.W, pady=(10,0))
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(file_frame, textvariable=self.file_var, width=50, state="readonly")
        self.file_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10,0), padx=(10,0))
        self.file_combo.bind('<<ComboboxSelected>>', self.on_file_selected)
        
        # 左侧参数设置区域
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0,10))
        
        # 剪裁参数区域
        crop_frame = ttk.LabelFrame(left_frame, text="剪裁参数", padding="10")
        crop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0,10))
        
        # 左上角坐标
        ttk.Label(crop_frame, text="左上角 X:").grid(row=0, column=0, sticky=tk.W)
        self.x_var = tk.StringVar(value="0")
        ttk.Entry(crop_frame, textvariable=self.x_var, width=10).grid(row=0, column=1, padx=(10,0))
        
        ttk.Label(crop_frame, text="Y:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.y_var = tk.StringVar(value="0")
        ttk.Entry(crop_frame, textvariable=self.y_var, width=10).grid(row=0, column=3, padx=(10,0))
        
        # 剪裁尺寸
        ttk.Label(crop_frame, text="宽度:").grid(row=1, column=0, sticky=tk.W, pady=(10,0))
        self.width_var = tk.StringVar(value="100")
        ttk.Entry(crop_frame, textvariable=self.width_var, width=10).grid(row=1, column=1, padx=(10,0), pady=(10,0))
        
        ttk.Label(crop_frame, text="高度:").grid(row=1, column=2, sticky=tk.W, padx=(10,0), pady=(10,0))
        self.height_var = tk.StringVar(value="100")
        ttk.Entry(crop_frame, textvariable=self.height_var, width=10).grid(row=1, column=3, padx=(10,0), pady=(10,0))
        
        # 实时预览开关
        self.preview_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(crop_frame, text="实时预览", variable=self.preview_var, 
                       command=self.update_preview).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10,0))
        
        # 操作按钮
        button_frame = ttk.Frame(crop_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=(10,0))
        
        ttk.Button(button_frame, text="预览剪裁", command=self.preview_crop).grid(row=0, column=0, padx=(0,5))
        ttk.Button(button_frame, text="执行剪裁", command=self.execute_crop).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="批量剪裁", command=self.batch_crop).grid(row=0, column=2, padx=5)
        
        # 图片信息区域
        info_frame = ttk.LabelFrame(left_frame, text="图片信息", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0,10))
        
        self.image_info_label = ttk.Label(info_frame, text="未选择图片", font=("Consolas", 10))
        self.image_info_label.grid(row=0, column=0, sticky=tk.W)
        
        self.crop_info_label = ttk.Label(info_frame, text="剪裁区域: 未计算", font=("Consolas", 10), foreground="blue")
        self.crop_info_label.grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        
        # 输出设置区域
        output_frame = ttk.LabelFrame(left_frame, text="输出设置", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(output_frame, text="文件名后缀:").grid(row=0, column=0, sticky=tk.W)
        self.suffix_var = tk.StringVar(value="_cropped")
        ttk.Entry(output_frame, textvariable=self.suffix_var, width=15).grid(row=0, column=1, padx=(10,0))
        
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(output_frame, text="覆盖同名文件", variable=self.overwrite_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10,0))
        
        # 右侧预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="10")
        preview_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # 创建画布用于显示图片
        canvas_frame = ttk.Frame(preview_frame)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", width=self.canvas_width, height=self.canvas_height)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # 绑定参数变化事件
        for var in [self.x_var, self.y_var, self.width_var, self.height_var]:
            var.trace('w', self.on_parameter_change)
    
    def select_directory(self):
        """选择目录"""
        directory = filedialog.askdirectory(title="选择包含PNG图片的目录")
        if directory:
            self.current_directory = directory
            self.directory_label.config(text=directory, foreground="black")
            self.load_png_files()
    
    def load_png_files(self):
        """加载目录中的PNG文件"""
        if not self.current_directory:
            return
            
        try:
            self.image_files = []
            for file in os.listdir(self.current_directory):
                if file.lower().endswith('.png'):
                    self.image_files.append(file)
            
            self.image_files.sort()
            self.file_combo['values'] = self.image_files
            
            if self.image_files:
                self.file_combo.set(self.image_files[0])
                self.on_file_selected()
            else:
                messagebox.showinfo("提示", "目录中没有找到PNG文件")
                
        except Exception as e:
            messagebox.showerror("错误", f"加载文件列表失败: {str(e)}")
    
    def on_file_selected(self, event=None):
        """文件选择事件"""
        selected_file = self.file_var.get()
        if selected_file and self.current_directory:
            self.current_image_path = os.path.join(self.current_directory, selected_file)
            self.load_image()
    
    def load_image(self):
        """加载图片"""
        try:
            if not os.path.exists(self.current_image_path):
                return
                
            self.original_image = Image.open(self.current_image_path)
            width, height = self.original_image.size
            
            # 更新图片信息
            file_size = os.path.getsize(self.current_image_path) / 1024  # KB
            self.image_info_label.config(
                text=f"尺寸: {width}x{height}, 大小: {file_size:.1f}KB"
            )
            
            # 显示预览
            self.show_image_preview()
            self.update_crop_info()
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图片失败: {str(e)}")
    
    def show_image_preview(self):
        """显示图片预览"""
        if not self.original_image:
            return
            
        try:
            # 计算缩放比例以适应画布
            img_width, img_height = self.original_image.size
            scale_x = self.canvas_width / img_width
            scale_y = self.canvas_height / img_height
            self.scale_factor = min(scale_x, scale_y, 1.0)
            
            # 缩放图片
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            
            resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(resized_image)
            
            # 清除画布并显示图片
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.preview_image)
            
            # 更新画布滚动区域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # 如果启用实时预览，显示剪裁框
            if self.preview_var.get():
                self.draw_crop_rectangle()
                
        except Exception as e:
            print(f"预览显示失败: {str(e)}")
    
    def draw_crop_rectangle(self):
        """在预览中绘制剪裁矩形"""
        try:
            if not self.original_image:
                return
                
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
            width = int(self.width_var.get() or 0)
            height = int(self.height_var.get() or 0)
            
            # 转换到预览坐标
            preview_x1 = x * self.scale_factor
            preview_y1 = y * self.scale_factor
            preview_x2 = (x + width) * self.scale_factor
            preview_y2 = (y + height) * self.scale_factor
            
            # 删除之前的矩形
            self.canvas.delete("crop_rect")
            
            # 绘制剪裁矩形
            self.canvas.create_rectangle(
                preview_x1, preview_y1, preview_x2, preview_y2,
                outline="red", width=2, tags="crop_rect"
            )
            
        except ValueError:
            # 参数无效时删除矩形
            self.canvas.delete("crop_rect")
    
    def on_parameter_change(self, *args):
        """参数变化事件"""
        self.update_crop_info()
        if self.preview_var.get():
            self.draw_crop_rectangle()
    
    def update_crop_info(self):
        """更新剪裁信息"""
        try:
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
            width = int(self.width_var.get() or 0)
            height = int(self.height_var.get() or 0)
            
            if self.original_image:
                img_width, img_height = self.original_image.size
                valid = (x >= 0 and y >= 0 and 
                        x + width <= img_width and 
                        y + height <= img_height and
                        width > 0 and height > 0)
                
                status = "有效" if valid else "无效"
                color = "green" if valid else "red"
                
                self.crop_info_label.config(
                    text=f"剪裁区域: [{x}, {y}, {width}, {height}] - {status}",
                    foreground=color
                )
            else:
                self.crop_info_label.config(text="剪裁区域: 未加载图片", foreground="gray")
                
        except ValueError:
            self.crop_info_label.config(text="剪裁区域: 参数无效", foreground="red")
    
    def update_preview(self):
        """更新预览显示"""
        if self.original_image:
            self.show_image_preview()
    
    def preview_crop(self):
        """预览剪裁效果"""
        if not self.original_image:
            messagebox.showwarning("警告", "请先选择图片")
            return
            
        try:
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
            width = int(self.width_var.get() or 0)
            height = int(self.height_var.get() or 0)
            
            # 验证参数
            img_width, img_height = self.original_image.size
            if (x < 0 or y < 0 or x + width > img_width or y + height > img_height or
                width <= 0 or height <= 0):
                messagebox.showerror("错误", "剪裁参数超出图片范围或无效")
                return
            
            # 执行剪裁
            cropped = self.original_image.crop((x, y, x + width, y + height))
            
            # 显示剪裁预览窗口
            self.show_crop_preview_window(cropped)
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")
    
    def show_crop_preview_window(self, cropped_image):
        """显示剪裁预览窗口"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title("剪裁预览")
        preview_window.attributes("-topmost", True)
        
        # 计算窗口大小
        img_width, img_height = cropped_image.size
        window_width = min(img_width + 40, 800)
        window_height = min(img_height + 100, 600)
        preview_window.geometry(f"{window_width}x{window_height}")
        
        # 显示图片
        canvas = tk.Canvas(preview_window, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 如果图片太大，缩放显示
        display_image = cropped_image
        if img_width > window_width - 40 or img_height > window_height - 100:
            scale = min((window_width - 40) / img_width, (window_height - 100) / img_height)
            new_size = (int(img_width * scale), int(img_height * scale))
            display_image = cropped_image.resize(new_size, Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(display_image)
        canvas.create_image(canvas.winfo_reqwidth()//2, canvas.winfo_reqheight()//2, 
                          anchor="center", image=photo)
        
        # 保持引用
        canvas.image = photo
        
        # 添加关闭按钮
        ttk.Button(preview_window, text="关闭", 
                  command=preview_window.destroy).pack(pady=10)
    
    def execute_crop(self):
        """执行单个文件剪裁"""
        if not self.original_image:
            messagebox.showwarning("警告", "请先选择图片")
            return
            
        try:
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
            width = int(self.width_var.get() or 0)
            height = int(self.height_var.get() or 0)
            
            # 验证参数
            img_width, img_height = self.original_image.size
            if (x < 0 or y < 0 or x + width > img_width or y + height > img_height or
                width <= 0 or height <= 0):
                messagebox.showerror("错误", "剪裁参数超出图片范围或无效")
                return
            
            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            suffix = self.suffix_var.get()
            output_filename = f"{base_name}{suffix}.png"
            output_path = os.path.join(self.current_directory, output_filename)
            
            # 检查文件是否存在
            if os.path.exists(output_path) and not self.overwrite_var.get():
                if not messagebox.askyesno("文件已存在", f"文件 {output_filename} 已存在，是否覆盖？"):
                    return
            
            # 执行剪裁并保存
            cropped = self.original_image.crop((x, y, x + width, y + height))
            cropped.save(output_path, "PNG")
            
            messagebox.showinfo("成功", f"图片已保存为: {output_filename}")
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
        except Exception as e:
            messagebox.showerror("错误", f"剪裁失败: {str(e)}")
    
    def batch_crop(self):
        """批量剪裁"""
        if not self.image_files:
            messagebox.showwarning("警告", "请先选择包含PNG文件的目录")
            return
        
        try:
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
            width = int(self.width_var.get() or 0)
            height = int(self.height_var.get() or 0)
            
            if width <= 0 or height <= 0:
                messagebox.showerror("错误", "宽度和高度必须大于0")
                return
            
            # 确认批量操作
            if not messagebox.askyesno("确认批量剪裁", 
                                     f"将对 {len(self.image_files)} 个PNG文件执行剪裁操作\n"
                                     f"剪裁参数: [{x}, {y}, {width}, {height}]\n"
                                     f"是否继续？"):
                return
            
            # 创建进度窗口
            self.show_batch_progress(x, y, width, height)
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字参数")
    
    def show_batch_progress(self, x, y, width, height):
        """显示批量处理进度"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title("批量剪裁进度")
        progress_window.geometry("400x150")
        progress_window.attributes("-topmost", True)
        progress_window.resizable(False, False)
        
        # 进度标签
        progress_label = ttk.Label(progress_window, text="准备开始...")
        progress_label.pack(pady=10)
        
        # 进度条
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        
        # 状态标签
        status_label = ttk.Label(progress_window, text="")
        status_label.pack(pady=5)
        
        # 取消按钮
        cancel_var = tk.BooleanVar()
        ttk.Button(progress_window, text="取消", 
                  command=lambda: cancel_var.set(True)).pack(pady=10)
        
        def batch_process():
            """批量处理函数"""
            success_count = 0
            error_count = 0
            total_files = len(self.image_files)
            suffix = self.suffix_var.get()
            overwrite = self.overwrite_var.get()
            
            for i, filename in enumerate(self.image_files):
                if cancel_var.get():
                    break
                    
                try:
                    # 更新进度
                    progress = (i / total_files) * 100
                    progress_var.set(progress)
                    progress_label.config(text=f"处理中... ({i+1}/{total_files})")
                    status_label.config(text=f"正在处理: {filename}")
                    progress_window.update()
                    
                    # 加载图片
                    image_path = os.path.join(self.current_directory, filename)
                    image = Image.open(image_path)
                    img_width, img_height = image.size
                    
                    # 检查剪裁区域是否有效
                    if (x < 0 or y < 0 or x + width > img_width or y + height > img_height):
                        error_count += 1
                        continue
                    
                    # 生成输出文件名
                    base_name = os.path.splitext(filename)[0]
                    output_filename = f"{base_name}{suffix}.png"
                    output_path = os.path.join(self.current_directory, output_filename)
                    
                    # 检查是否覆盖
                    if os.path.exists(output_path) and not overwrite:
                        error_count += 1
                        continue
                    
                    # 执行剪裁
                    cropped = image.crop((x, y, x + width, y + height))
                    cropped.save(output_path, "PNG")
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"处理文件 {filename} 时出错: {str(e)}")
            
            # 完成
            progress_var.set(100)
            if cancel_var.get():
                progress_label.config(text="已取消")
                status_label.config(text=f"成功: {success_count}, 失败: {error_count}")
            else:
                progress_label.config(text="批量剪裁完成")
                status_label.config(text=f"成功: {success_count}, 失败: {error_count}")
            
            # 3秒后自动关闭
            progress_window.after(3000, progress_window.destroy)
        
        # 在新线程中执行批量处理
        thread = threading.Thread(target=batch_process)
        thread.daemon = True
        thread.start()

def main():
    root = tk.Tk()
    app = ImageCropTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()