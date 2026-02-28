/**
 * @file src/main.cpp
 * @author SoM
 * @brief Native IL2CPP Injection payload (Version.dll Proxy)
 * @version 0.4
 * @date 2026-02-27
 * 
 * @copyright Copyright (c) 2026
 * 
 */

#pragma comment(linker, "/export:GetFileVersionInfoA=version_orig.GetFileVersionInfoA")
#pragma comment(linker, "/export:GetFileVersionInfoByHandle=version_orig.GetFileVersionInfoByHandle")
#pragma comment(linker, "/export:GetFileVersionInfoExA=version_orig.GetFileVersionInfoExA")
#pragma comment(linker, "/export:GetFileVersionInfoExW=version_orig.GetFileVersionInfoExW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeA=version_orig.GetFileVersionInfoSizeA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExA=version_orig.GetFileVersionInfoSizeExA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExW=version_orig.GetFileVersionInfoSizeExW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeW=version_orig.GetFileVersionInfoSizeW")
#pragma comment(linker, "/export:GetFileVersionInfoW=version_orig.GetFileVersionInfoW")
#pragma comment(linker, "/export:VerFindFileA=version_orig.VerFindFileA")
#pragma comment(linker, "/export:VerFindFileW=version_orig.VerFindFileW")
#pragma comment(linker, "/export:VerInstallFileA=version_orig.VerInstallFileA")
#pragma comment(linker, "/export:VerInstallFileW=version_orig.VerInstallFileW")
#pragma comment(linker, "/export:VerLanguageNameA=version_orig.VerLanguageNameA")
#pragma comment(linker, "/export:VerLanguageNameW=version_orig.VerLanguageNameW")
#pragma comment(linker, "/export:VerQueryValueA=version_orig.VerQueryValueA")
#pragma comment(linker, "/export:VerQueryValueW=version_orig.VerQueryValueW")

#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "MinHook.h"
#include "offsets.h"

// ==============================================================================
// KERNEL-STYLE CONFIGURATION MACROS
// ==============================================================================

#ifdef ENABLE_DEBUG_CONSOLE
	#define INIT_CONSOLE() \
		do { \
			AllocConsole(); \
			FILE* fDummy; \
			freopen_s(&fDummy, "CONOUT$", "w", stdout); \
			freopen_s(&fDummy, "CONOUT$", "w", stderr); \
		} while(0)
	#define LOG(...) printf(__VA_ARGS__)
#else
	#define INIT_CONSOLE() do {} while(0)
	#define LOG(...)	   do {} while(0)
#endif

// ==============================================================================
// TYPE DEFINITIONS
// ==============================================================================

// Unity Engine API
typedef void* (*get_gameObject_t)(void* component, void* method);
typedef void  (*SetActive_t)(void* gameObject, uint64_t value, void* method); 
typedef void  (*Destroy_t)(void* obj, void* method);

// Reward Gun
typedef void (*InitGunInfo_t)(void* __this, void* gun, void* action, void* method);

// Turn End
typedef void (*SpotFinish_t)(void* __this, void* method);
typedef void (*TurnDisact_t)(void* __this, void* method);
typedef void (*MoveCamera_t)(void* __this, uint64_t target, uint8_t move, float duration, float delay, uint8_t recordPos, uint8_t changescale, float setscale, void* handle, void* method);

// ==============================================================================
// GLOBAL POINTERS
// ==============================================================================

get_gameObject_t get_gameObject = nullptr;
SetActive_t SetActive = nullptr;
Destroy_t Destroy = nullptr;

InitGunInfo_t o_InitGunInfo = nullptr;
MoveCamera_t o_MoveCamera = nullptr;

SpotFinish_t p_SpotFinish1 = nullptr;
SpotFinish_t p_SpotFinish2 = nullptr;
TurnDisact_t p_TurnDisact = nullptr;

// ==============================================================================
// HOOK IMPLEMENTATIONS
// ==============================================================================

// --- REWARD GUN ---
void hk_InitGunInfo(void* __this, void* gun, void* action, void* method) {
	LOG("[Native] >> UI Initialization Intercepted!\n");

	if (action != nullptr) {
		__try {
			uintptr_t action_ptr = (uintptr_t)action;
			typedef void (*ActionInvoke_t)(void* target);
			ActionInvoke_t invoke_impl = (ActionInvoke_t)(*(uintptr_t*)(action_ptr + 0x18));
			void* target = (void*)(*(uintptr_t*)(action_ptr + 0x20));
			if (invoke_impl) {
				invoke_impl(target);
				LOG("[Native] [1/4] Faked Callback Invoke sent.\n");
			}
		} __except(EXCEPTION_EXECUTE_HANDLER) {
			LOG("[Native Error] Callback invoke crashed!\n");
		}
	}

	if (__this != nullptr) {
		void* gameObject = nullptr;
		__try {
			if (get_gameObject) {
				gameObject = get_gameObject(__this, nullptr);
				if (gameObject) LOG("[Native] [2/4] get_gameObject Success: 0x%p\n", gameObject);
			}
		} __except(EXCEPTION_EXECUTE_HANDLER) {
			LOG("[Native Error] get_gameObject crashed!\n");
		}

		if (gameObject != nullptr) {
			__try {
				if (SetActive) {
					SetActive(gameObject, 0, nullptr);
					LOG("[Native] [3/4] SetActive(false) Success.\n");
				}
			} __except(EXCEPTION_EXECUTE_HANDLER) {
				LOG("[Native Error] SetActive crashed!\n");
			}

			__try {
				if (Destroy) {
					Destroy(gameObject, nullptr);
					LOG("[Native] [4/4] Destroy Success.\n");
				}
			} __except(EXCEPTION_EXECUTE_HANDLER) {
				LOG("[Native Error] Destroy crashed!\n");
			}
		}
	}
}

// --- TURN END: Spot Animation ---
void hk_Spot_Show(void* __this, void* method) {
	if (__this != nullptr) {
		__try {
			// Instantly trigger the animation end events to deceive the state machine
			if (p_SpotFinish2) p_SpotFinish2(__this, nullptr);
			if (p_SpotFinish1) p_SpotFinish1(__this, nullptr);
			LOG("[Native] Spot Animation skipped & Finish Event faked.\n");
		} __except(EXCEPTION_EXECUTE_HANDLER) {
			LOG("[Native Error] Spot Finish fake failed!\n");
		}
	}
}

// --- TURN END: Turn Animation ---
// This single hook will be shared across PlayEnd, ToGK, and ToSF
void hk_TurnAnimFastForward(void* __this, void* method) {
	if (__this != nullptr) {
		__try {
			if (p_TurnDisact) p_TurnDisact(__this, nullptr);
			LOG("[Native] Turn Animation fast-forwarded to DisactiveMain.\n");
		} __except(EXCEPTION_EXECUTE_HANDLER) {
			LOG("[Native Error] Turn fast-forward failed!\n");
		}
	}
}

// --- TURN END: Camera Movement ---
void hk_MoveCamera(void* __this, uint64_t target, uint8_t move, float duration, float delay, uint8_t recordPos, uint8_t changescale, float setscale, void* handle, void* method) {
	__try {
		if (o_MoveCamera) {
			// Forward the call to original, but force duration and delay to 0.0f
			o_MoveCamera(__this, target, move, 0.0f, 0.0f, recordPos, changescale, setscale, handle, method);
		}
	} __except(EXCEPTION_EXECUTE_HANDLER) {
		LOG("[Native Error] MoveCamera hook failed!\n");
	}
}

// ==============================================================================
// PAYLOAD INITIALIZATION
// ==============================================================================

DWORD WINAPI ApplyCPUOptimization(LPVOID lpParam) {
	INIT_CONSOLE();

	LOG("[*] Initializing Engine-Level Annihilation Hook via version.dll...\n");

	HMODULE hGameAssembly = nullptr;
	while (!(hGameAssembly = GetModuleHandleA("GameAssembly.dll"))) {
		Sleep(100);
	}
	
	uintptr_t baseAddr = (uintptr_t)hGameAssembly;
	LOG("[*] GameAssembly.dll loaded at 0x%p\n", (void*)baseAddr);

	// --- Resolve Absolute Addresses ---
	get_gameObject = (get_gameObject_t)(baseAddr + OFFSET_get_gameObject);
	SetActive = (SetActive_t)(baseAddr + OFFSET_SetActive);
	Destroy = (Destroy_t)(baseAddr + OFFSET_Destroy);
	
	p_SpotFinish1 = (SpotFinish_t)(baseAddr + OFFSET_Spot_Finish1);
	p_SpotFinish2 = (SpotFinish_t)(baseAddr + OFFSET_Spot_Finish2);
	p_TurnDisact = (TurnDisact_t)(baseAddr + OFFSET_Turn_Disact);

	// --- Direct Memory Patch (Turn_IsPlay) ---
	void* pIsPlay = (void*)(baseAddr + OFFSET_Turn_IsPlay);
	DWORD oldProtect;
	if (VirtualProtect(pIsPlay, 3, PAGE_EXECUTE_READWRITE, &oldProtect)) {
		// xor eax, eax; ret (Return false always)
		uint8_t patch[] = { 0x31, 0xC0, 0xC3 };
		memcpy(pIsPlay, patch, 3);
		VirtualProtect(pIsPlay, 3, oldProtect, &oldProtect);
		LOG("[+] Memory Patch Applied: Turn_IsPlay bypassed.\n");
	} else {
		LOG("[-] Failed to unprotect memory for Turn_IsPlay patch.\n");
	}

	// --- Install Hooks ---
	if (MH_Initialize() == MH_OK) {
		
		// Reward Gun UI
		uintptr_t addr_InitGunInfo = baseAddr + OFFSET_InitGunInfo;
		MH_CreateHook((LPVOID)addr_InitGunInfo, &hk_InitGunInfo, (LPVOID*)&o_InitGunInfo);
		MH_EnableHook((LPVOID)addr_InitGunInfo);
		
		// Turn End - Spot
		uintptr_t addr_SpotShow = baseAddr + OFFSET_Spot_Show;
		MH_CreateHook((LPVOID)addr_SpotShow, &hk_Spot_Show, NULL);
		MH_EnableHook((LPVOID)addr_SpotShow);
		
		// Turn End - Turn Animation (Shared Hook)
		uintptr_t addr_TurnPlayEnd = baseAddr + OFFSET_Turn_PlayEnd;
		uintptr_t addr_TurnToGK	= baseAddr + OFFSET_Turn_ToGK;
		uintptr_t addr_TurnToSF	= baseAddr + OFFSET_Turn_ToSF;
		MH_CreateHook((LPVOID)addr_TurnPlayEnd, &hk_TurnAnimFastForward, NULL);
		MH_CreateHook((LPVOID)addr_TurnToGK, &hk_TurnAnimFastForward, NULL);
		MH_CreateHook((LPVOID)addr_TurnToSF, &hk_TurnAnimFastForward, NULL);
		MH_EnableHook((LPVOID)addr_TurnPlayEnd);
		MH_EnableHook((LPVOID)addr_TurnToGK);
		MH_EnableHook((LPVOID)addr_TurnToSF);
		
		// Turn End - Camera
		uintptr_t addr_MoveCamera = baseAddr + OFFSET_MoveCamera;
		MH_CreateHook((LPVOID)addr_MoveCamera, &hk_MoveCamera, (LPVOID*)&o_MoveCamera);
		MH_EnableHook((LPVOID)addr_MoveCamera);

		LOG("[*] All optimizations (Reward Gun + Turn End) are ACTIVE.\n");
	} else {
		LOG("[-] MinHook initialization failed.\n");
	}

	return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
	if (ul_reason_for_call == DLL_PROCESS_ATTACH) {
		DisableThreadLibraryCalls(hModule);
		CreateThread(nullptr, 0, ApplyCPUOptimization, nullptr, 0, nullptr);
	}
	return TRUE;
}