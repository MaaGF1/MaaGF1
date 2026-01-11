// tools/hack/luna/hook.js

var State = {
	mode: "inject", 
	fakePos: { x: 0, y: 0 },
	blockWheel: true, // Default: Block physical wheel
	gameHwnd: null
};

// --- Constants ---
var RIM_TYPEMOUSE = 0;
var RI_MOUSE_WHEEL = 0x0400;

function debug_hook() {
	var user32 = Process.findModuleByName("user32.dll");
	if (!user32) user32 = Process.findModuleByName("User32.dll");
	if (!user32) {
		send({ type: 'error', stack: "user32.dll not found" });
		return;
	}

	var ptr_ScreenToClient = user32.findExportByName("ScreenToClient");
	var ptr_GetCursorPos = user32.findExportByName("GetCursorPos");
	var ptr_GetRawInputData = user32.findExportByName("GetRawInputData");

	// Helper: Get Pointer Size for struct offsets
	var ptrSize = Process.pointerSize; // 4 or 8

	// 1. Hook ScreenToClient (Coordinate Spoofing)
	if (ptr_ScreenToClient) {
		Interceptor.attach(ptr_ScreenToClient, {
			onEnter: function(args) {
				this.hwnd = args[0];
				this.lpPoint = args[1];
				if (State.gameHwnd === null) State.gameHwnd = this.hwnd;
			},
			onLeave: function(retval) {
			if (retval.toInt32() === 0) return;
				try {
					if (State.mode === "inject") {
						this.lpPoint.writeS32(parseInt(State.fakePos.x));
						this.lpPoint.add(4).writeS32(parseInt(State.fakePos.y));
					}
				} catch (e) {}
			}
		});
	}

	// 2. Hook GetCursorPos (Backup Coordinate Spoofing)
	if (ptr_GetCursorPos) {
		Interceptor.attach(ptr_GetCursorPos, {
			onEnter: function(args) { this.lpPoint = args[0]; },
			onLeave: function(retval) {
				if (retval.toInt32() === 0) return;
				try {
					if (State.mode === "inject") {
						this.lpPoint.writeS32(parseInt(State.fakePos.x));
						this.lpPoint.add(4).writeS32(parseInt(State.fakePos.y));
					}
				} catch (e) {}
			}
		});
	}

	// 3. Hook GetRawInputData (Blocks Physical/SendInput Wheel)
	if (ptr_GetRawInputData) {
		Interceptor.attach(ptr_GetRawInputData, {
			onEnter: function(args) {
				this.pData = args[2];
				this.uiCommand = args[1].toInt32(); // RID_INPUT = 0x10000003
			},
			onLeave: function(retval) {
				// If successful and we are reading Input Data (not header)
				if (retval.toInt32() > 0 && this.pData.isNull() === false && State.blockWheel) {
					try {
						// RAWINPUTHEADER is at pData
						// DWORD dwType is at offset 0
						var dwType = this.pData.readU32();
						
						if (dwType === RIM_TYPEMOUSE) {
							// RAWMOUSE struct starts after header
							// Header size: x64=24 bytes, x86=16 bytes
							var headerSize = (ptrSize === 8) ? 24 : 16;
							var rawMousePtr = this.pData.add(headerSize);
							
							// RAWMOUSE Layout:
							// Offset 0: usFlags (2 bytes)
							// Offset 4: usButtonFlags (2 bytes) - This contains RI_MOUSE_WHEEL
							// Offset 6: usButtonData (2 bytes) - This contains Wheel Delta
							
							var usButtonFlags = rawMousePtr.add(4).readU16();
							
							// If this is SendInput from user's real mouse, let game do nothing
							if ((usButtonFlags & RI_MOUSE_WHEEL) === RI_MOUSE_WHEEL) {
								rawMousePtr.add(4).writeU16(usButtonFlags & ~RI_MOUSE_WHEEL);
								rawMousePtr.add(6).writeU16(0);
							}
						}
					} catch (e) {
						// send({type: 'error', stack: "RawInput Error: " + e.message});
					}
				}
			}
		});
	}

	send({ type: 'info', payload: "Hooks installed: Pos(ScreenToClient/GetCursorPos), Wheel(RawInput Only)" });
}

// ================= Message Processing =================
recv(function onMessage(message) {
	if (message.type === "UPDATE_POS") {
		State.fakePos.x = message.x;
		State.fakePos.y = message.y;
	}
	else if (message.type === "SET_WHEEL") {
		State.blockWheel = !message.enable;
		send({ type: 'info', payload: "Wheel Block: " + State.blockWheel });
	}
	recv(onMessage);
});

try {
	debug_hook();
} catch (e) {
	send({ type: 'error', stack: e.message });
}