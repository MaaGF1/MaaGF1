# tools/hack/trimmer/monitor/top.py

import os
import sys
import time
import psutil

# Attempt to load NVIDIA Management Library for deep GPU hardware metrics
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
    GPU_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    GPU_NAME = pynvml.nvmlDeviceGetName(GPU_HANDLE)
except Exception as e:
    HAS_NVML = False
    GPU_NAME = "Unknown or NVML Failed"

# Constants for Power Estimation (Heuristic)
ESTIMATED_CPU_TDP_W = 65.0 
ESTIMATED_SYS_BASE_W = 15.0

class AdvancedPowerMonitor:
    def __init__(self, process_name="GrilsFrontLine.exe"):
        self.process_name = process_name
        self.pid = None
        self.process = None
        
        if os.name == 'nt':
            os.system('')

    def _find_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == self.process_name.lower():
                    self.pid = proc.info['pid']
                    self.process = psutil.Process(self.pid)
                    self.process.cpu_percent() # Init baseline
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        self.pid = None
        self.process = None
        return False

    def clear_screen(self):
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

    def get_gpu_metrics(self):
        """Returns GPU metrics dict using NVML"""
        if not HAS_NVML:
            return None
        
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(GPU_HANDLE)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(GPU_HANDLE)
            temp = pynvml.nvmlDeviceGetTemperature(GPU_HANDLE, pynvml.NVML_TEMPERATURE_GPU)
            power_mw = pynvml.nvmlDeviceGetPowerUsage(GPU_HANDLE)
            
            # Find specific process GPU memory footprint if available
            proc_vram_mb = None
            try:
                graphics_procs = pynvml.nvmlDeviceGetGraphicsRunningProcesses(GPU_HANDLE)
                for p in graphics_procs:
                    if p.pid == self.pid:
                        # FIX: Handle Windows WDDM driver returning None for process memory
                        if p.usedGpuMemory is not None:
                            proc_vram_mb = p.usedGpuMemory / (1024 * 1024)
                        else:
                            proc_vram_mb = -1.0 # Indicator for WDDM limitation
            except pynvml.NVMLError:
                pass 

            return {
                'render_util': util.gpu,
                'mem_util': util.memory,
                'temp_c': temp,
                'power_w': power_mw / 1000.0,
                'total_vram_gb': mem_info.total / (1024**3),
                'used_vram_gb': mem_info.used / (1024**3),
                'target_vram_mb': proc_vram_mb
            }
        except pynvml.NVMLError:
            return None

    def draw_dashboard(self, interval=1.0):
        while True:
            try:
                self.clear_screen()
                print("=== MaaGF1 Advanced Power & Render Monitor ===")
                print("-" * 65)

                # 1. System Level Metrics
                sys_cpu = psutil.cpu_percent(interval=0)
                sys_cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0.0
                
                print(f"[ SYSTEM CPU ] LOAD: {sys_cpu:5.1f}% | FREQ: {sys_cpu_freq:4.0f} MHz")

                # 2. Hardware GPU Metrics (Power & Render)
                gpu_data = self.get_gpu_metrics()
                if gpu_data:
                    if isinstance(GPU_NAME, bytes):
                        gpu_name_str = GPU_NAME.decode('utf-8')
                    else:
                        gpu_name_str = GPU_NAME
                        
                    print(f"[ HARDWARE GPU ] {gpu_name_str}")
                    print(f"  RENDER CORE  : {gpu_data['render_util']:5.1f}% (SM Active)")
                    print(f"  VRAM USAGE   : {gpu_data['used_vram_gb']:.1f} GB / {gpu_data['total_vram_gb']:.1f} GB")
                    print(f"  TEMPERATURE  : {gpu_data['temp_c']} C")
                    print(f"  POWER DRAW   : {gpu_data['power_w']:5.1f} W (Exact Physical)")
                else:
                    print("[ HARDWARE GPU ] NVML Not Available or No NVIDIA GPU.")

                print("-" * 65)

                # 3. Target Process Metrics & Power Estimation
                if not self.process or not psutil.pid_exists(self.pid):
                    if not self._find_process():
                        print(f"TARGET PROCESS : '{self.process_name}' NOT FOUND. Waiting...")
                        time.sleep(interval)
                        continue

                try:
                    # CPU is normalized by core count
                    p_cpu = self.process.cpu_percent(interval=0) / psutil.cpu_count()
                    
                    # Heuristic Power Calculation
                    est_proc_cpu_w = (p_cpu / 100.0) * ESTIMATED_CPU_TDP_W
                    
                    est_proc_gpu_w = 0.0
                    if gpu_data and gpu_data['render_util'] > 0:
                        est_proc_gpu_w = gpu_data['power_w'] * 0.8 
                    
                    est_total_proc_w = est_proc_cpu_w + est_proc_gpu_w

                    print(f"[ TARGET PROC ] {self.process_name} (PID: {self.pid})")
                    print(f"  PROC CPU    : {p_cpu:5.1f}%")
                    
                    # FIX: Handle display logic for VRAM safely
                    if gpu_data and gpu_data['target_vram_mb'] is not None:
                        if gpu_data['target_vram_mb'] < 0:
                            print(f"  PROC VRAM   : N/A (OS Managed / WDDM)")
                        else:
                            print(f"  PROC VRAM   : {gpu_data['target_vram_mb']:.1f} MB (Dedicated)")
                    else:
                        print(f"  PROC VRAM   : Not Detected in GPU Engine")
                    
                    print(f"\n[ POWER ESTIMATION (Heuristic) ]")
                    print(f"  PROC CPU PWR: ~{est_proc_cpu_w:5.1f} W")
                    if gpu_data:
                        print(f"  PROC GPU PWR: ~{est_proc_gpu_w:5.1f} W (Estimated Share)")
                        print(f"  PROC TOTAL  : ~{est_total_proc_w:5.1f} W")
                        
                        sys_total_w = gpu_data['power_w'] + (sys_cpu / 100.0 * ESTIMATED_CPU_TDP_W) + ESTIMATED_SYS_BASE_W
                        print(f"  SYSTEM TOTAL: ~{sys_total_w:5.1f} W (CPU+GPU+Base)")

                except psutil.NoSuchProcess:
                    print(f"\nTARGET PROCESS : '{self.process_name}' HAS TERMINATED.")
                    self.process = None
                
                print("-" * 65)
                print("Press CTRL+C to exit...")
                
                time.sleep(interval)

            except KeyboardInterrupt:
                self.clear_screen()
                print("Monitor stopped safely.")
                break
            except Exception as e:
                # Print exact traceback for debugging if it happens again
                import traceback
                self.clear_screen()
                print("Error occurred:")
                traceback.print_exc()
                time.sleep(3)

if __name__ == "__main__":
    monitor = AdvancedPowerMonitor("GrilsFrontLine.exe")
    monitor.draw_dashboard(interval=1.0)