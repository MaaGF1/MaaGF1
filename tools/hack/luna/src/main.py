import tkinter as tk
from tkinter import ttk
import threading
import sys
from core import LunaService

class RedirectText:
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl

    def write(self, string):
        self.text_ctrl.insert(tk.END, string)
        self.text_ctrl.see(tk.END)

    def flush(self):
        pass

class LunaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MaaGFL Luna Injector")
        self.root.geometry("500x350")
        
        self.service = None
        self.worker_thread = None

        self._build_ui()
        
        # Redirect stdout
        sys.stdout = RedirectText(self.log_text)
        sys.stderr = RedirectText(self.log_text)

        print("Luna GUI Initialized. Ready to inject.")

    def _build_ui(self):
        frame_top = tk.Frame(self.root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)

        # Target Process
        tk.Label(frame_top, text="Target Process:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.combo_process = ttk.Combobox(frame_top, values=["GrilsFrontLine.exe", "MaaGFL.exe", "Unity.exe"], width=25)
        self.combo_process.current(0)
        self.combo_process.grid(row=0, column=1, padx=10, pady=5)

        # Pipe Name
        tk.Label(frame_top, text="Pipe Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_pipe = tk.Entry(frame_top, width=28)
        self.entry_pipe.insert(0, "MaaLunaPipe")
        self.entry_pipe.grid(row=1, column=1, padx=10, pady=5)

        # Buttons
        frame_btn = tk.Frame(self.root, pady=5)
        frame_btn.pack(fill=tk.X)
        
        self.btn_start = tk.Button(frame_btn, text="Start Injection", width=15, command=self.start_service)
        self.btn_start.pack(side=tk.LEFT, padx=10)

        self.btn_stop = tk.Button(frame_btn, text="Stop Injection", width=15, command=self.stop_service, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)

        self.btn_refresh = tk.Button(frame_btn, text="Refresh/Restart", width=15, command=self.restart_service)
        self.btn_refresh.pack(side=tk.LEFT, padx=10)

        # Log Console
        frame_log = tk.Frame(self.root, padx=10, pady=10)
        frame_log.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(frame_log, wrap=tk.WORD, state=tk.NORMAL)
        scrollbar = tk.Scrollbar(frame_log, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _run_service(self, process_name, pipe_name):
        self.service = LunaService(process_name, pipe_name)
        success = self.service.start()
        if not success:
            # If start failed, reset buttons
            self.root.after(0, self._set_gui_state, tk.NORMAL)

    def start_service(self):
        process_name = self.combo_process.get()
        pipe_name = self.entry_pipe.get()
        
        if not process_name or not pipe_name:
            print("[!] Process name and Pipe name cannot be empty.")
            return

        self._set_gui_state(tk.DISABLED)
        
        self.worker_thread = threading.Thread(target=self._run_service, args=(process_name, pipe_name))
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def stop_service(self):
        if self.service:
            self.service.stop()
        self._set_gui_state(tk.NORMAL)

    def restart_service(self):
        self.stop_service()
        self.root.after(500, self.start_service) # brief delay to allow cleanup

    def _set_gui_state(self, start_state):
        self.btn_start.config(state=start_state)
        self.entry_pipe.config(state=start_state)
        self.combo_process.config(state=start_state)
        
        stop_state = tk.NORMAL if start_state == tk.DISABLED else tk.DISABLED
        self.btn_stop.config(state=stop_state)

def on_closing():
    if getattr(app, 'service', None):
        app.service.stop()
    root.destroy()
    sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = LunaGUI(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()