// tools/hack/trimmer/cpp/src/main.cpp

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
#include "MinHook.h"
#include "offsets.h"

typedef void* (*get_gameObject_t)(void* component, void* method);
typedef void  (*SetActive_t)(void* gameObject, uint64_t value, void* method); 
typedef void  (*Destroy_t)(void* obj, void* method);

get_gameObject_t get_gameObject = nullptr;
SetActive_t      SetActive      = nullptr;
Destroy_t        Destroy        = nullptr;

typedef void (*InitGunInfo_t)(void* __this, void* gun, void* action, void* method);
InitGunInfo_t o_InitGunInfo = nullptr;

void hk_InitGunInfo(void* __this, void* gun, void* action, void* method) {
    printf("[Native] >> UI Initialization Intercepted!\n");

    if (action != nullptr) {
        __try {
            uintptr_t action_ptr = (uintptr_t)action;
            typedef void (*ActionInvoke_t)(void* target);
            ActionInvoke_t invoke_impl = (ActionInvoke_t)(*(uintptr_t*)(action_ptr + 0x18));
            void* target = (void*)(*(uintptr_t*)(action_ptr + 0x20));
            if (invoke_impl) {
                invoke_impl(target);
                printf("[Native] [1/4] Faked Callback Invoke sent.\n");
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            printf("[Native Error] Callback invoke crashed!\n");
        }
    }

    if (__this != nullptr) {
        void* gameObject = nullptr;
        __try {
            if (get_gameObject) {
                gameObject = get_gameObject(__this, nullptr);
                if (gameObject) printf("[Native] [2/4] get_gameObject Success: 0x%p\n", gameObject);
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            printf("[Native Error] get_gameObject crashed!\n");
        }

        if (gameObject != nullptr) {
            __try {
                if (SetActive) {
                    SetActive(gameObject, 0, nullptr);
                    printf("[Native] [3/4] SetActive(false) Success.\n");
                }
            } __except(EXCEPTION_EXECUTE_HANDLER) {
                printf("[Native Error] SetActive crashed!\n");
            }

            __try {
                if (Destroy) {
                    Destroy(gameObject, nullptr);
                    printf("[Native] [4/4] Destroy Success.\n");
                }
            } __except(EXCEPTION_EXECUTE_HANDLER) {
                printf("[Native Error] Destroy crashed!\n");
            }
        }
    }
}

DWORD WINAPI ApplyCPUOptimization(LPVOID lpParam) {
    AllocConsole();
    FILE* fDummy;
    freopen_s(&fDummy, "CONOUT$", "w", stdout);
    freopen_s(&fDummy, "CONOUT$", "w", stderr);

    printf("[*] Initializing Engine-Level Annihilation Hook via version.dll...\n");

    HMODULE hGameAssembly = nullptr;
    while (!(hGameAssembly = GetModuleHandleA("GameAssembly.dll"))) {
        Sleep(100);
    }
    
    // Get the base address of the DLL loaded into memory.
    uintptr_t baseAddr = (uintptr_t)hGameAssembly;
    printf("[*] GameAssembly.dll loaded at 0x%p\n", (void*)baseAddr);

    // Binding via base address + static offset
    get_gameObject = (get_gameObject_t)(baseAddr + OFFSET_get_gameObject);
    SetActive      = (SetActive_t)(baseAddr + OFFSET_SetActive);
    Destroy        = (Destroy_t)(baseAddr + OFFSET_Destroy);
    uintptr_t addr_InitGunInfo = baseAddr + OFFSET_InitGunInfo;

    printf("[+] Static Resolution Success! InitGunInfo at: 0x%p\n", (void*)addr_InitGunInfo);
    
    if (MH_Initialize() == MH_OK) {
        MH_CreateHook((LPVOID)addr_InitGunInfo, &hk_InitGunInfo, (LPVOID*)&o_InitGunInfo);
        MH_EnableHook((LPVOID)addr_InitGunInfo);
        printf("[*] Zero-Frame UI Annihilator is ACTIVE. (CPU Hook Placed)\n");
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