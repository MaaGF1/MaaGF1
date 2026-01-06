import ctypes
from ctypes import wintypes
import threading

# Windows Named Pipe Constants
PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_MESSAGE = 0x00000004
PIPE_READMODE_MESSAGE = 0x00000002
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255
BUFSIZE = 512
NMPWAIT_USE_DEFAULT_WAIT = 0
INVALID_HANDLE_VALUE = -1

kernel32 = ctypes.windll.kernel32

class NamedPipeServer:
    def __init__(self, pipe_name, handler_func):
        self.pipe_name = "\\\\.\\pipe\\" + pipe_name
        self.handler_func = handler_func
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._server_loop)
        self.thread.daemon = True
        self.thread.start()

    def _server_loop(self):
        print(f"[*] Pipe Server listening on {self.pipe_name}")
        while self.running:
            # Create Named Pipe
            h_pipe = kernel32.CreateNamedPipeW(
                self.pipe_name,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                PIPE_UNLIMITED_INSTANCES,
                BUFSIZE,
                BUFSIZE,
                0,
                None
            )

            if h_pipe == INVALID_HANDLE_VALUE:
                print(f"[!] Failed to create pipe. Error: {kernel32.GetLastError()}")
                return

            # Wait for client connection
            connected = kernel32.ConnectNamedPipe(h_pipe, None)
            if not connected and kernel32.GetLastError() == 535: # ERROR_PIPE_CONNECTED
                connected = True

            if connected:
                self._handle_client(h_pipe)
            
            kernel32.CloseHandle(h_pipe)

    def _handle_client(self, h_pipe):
        buffer = ctypes.create_string_buffer(BUFSIZE)
        bytes_read = wintypes.DWORD()
        
        while self.running:
            success = kernel32.ReadFile(
                h_pipe,
                buffer,
                BUFSIZE,
                ctypes.byref(bytes_read),
                None
            )

            if not success or bytes_read.value == 0:
                break # Client disconnected

            message = buffer.value[:bytes_read.value].decode('ascii')
            response = self.handler_func(message)
            
            if response:
                bytes_written = wintypes.DWORD()
                to_write = response.encode('ascii')
                kernel32.WriteFile(
                    h_pipe,
                    to_write,
                    len(to_write),
                    ctypes.byref(bytes_written),
                    None
                )