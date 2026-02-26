// tools/hack/luna/hook.js

var State = {
	mode: "inject", 
	fakePos: { x: 0, y: 0 },
	blockWheel: true,	// Default: Block physical wheel
	pendingWheel: 0,	// Store fake wheel delta to inject
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

	if (ptr_GetRawInputData) {
		Interceptor.attach(ptr_GetRawInputData, {
			onEnter: function(args) {
				this.pData = args[2];
				this.uiCommand = args[1].toInt32(); // RID_INPUT = 0x10000003
			},
			onLeave: function(retval) {
				// Check success
				if (retval.toInt32() > 0 && this.pData.isNull() === false) {
					try {
						var dwType = this.pData.readU32();
						
						if (dwType === RIM_TYPEMOUSE) {
							var headerSize = (ptrSize === 8) ? 24 : 16;
							var rawMousePtr = this.pData.add(headerSize);
							
							// Check if we need to INJECT a fake wheel event
							if (State.pendingWheel !== 0) {
								// 1. Force flags to indicate wheel event
								// usButtonFlags offset = 4
								var currentFlags = rawMousePtr.add(4).readU16();
								rawMousePtr.add(4).writeU16(currentFlags | RI_MOUSE_WHEEL);
								
								// 2. Write the delta
								// usButtonData offset = 6
								rawMousePtr.add(6).writeU16(State.pendingWheel);
								
								// 3. Consume the event
								State.pendingWheel = 0;
								
								// send({type: 'info', payload: "Injected Wheel RawInput"});
								return; // Skip the blocking logic below
							}

							// Block physical wheel logic (Original Logic)
							if (State.blockWheel) {
								var usButtonFlags = rawMousePtr.add(4).readU16();
								if ((usButtonFlags & RI_MOUSE_WHEEL) === RI_MOUSE_WHEEL) {
									// Strip the wheel flag and zero the delta
									rawMousePtr.add(4).writeU16(usButtonFlags & ~RI_MOUSE_WHEEL);
									rawMousePtr.add(6).writeU16(0);
								}
							}
						}
					} catch (e) {
						 // send({type: 'error', stack: "RawInput Error: " + e.message});
					}
				}
			}
		});
	}

	send({ type: 'info', payload: "Hooks installed: Pos(Spoof), Wheel(Block/Inject)" });
}

// ================= Message Processing =================
recv(function onMessage(message) {
	if (message.type === "UPDATE_POS") {
		State.fakePos.x = message.x;
		State.fakePos.y = message.y;
	}
	else if (message.type === "SIMULATE_WHEEL") {
		// Receive delta from Python
		State.pendingWheel = message.delta;
		// send({ type: 'info', payload: "Pending Wheel: " + message.delta });
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