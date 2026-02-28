/**
 * @file src/offsets.h
 * @author SoM
 * @brief IL2CPP Static Offsets for Version Proxy (Auto-Generated)
 * @version 0.4
 * @date 2026-02-28
 * 
 * @copyright Copyright (c) 2026
 * 
 */

#pragma once
#include <stdint.h>

// ==========================================
// Reward Gun UI Offsets
// ==========================================

// "Signature": "UnityEngine_GameObject_o* UnityEngine_Component__get_gameObject (UnityEngine_Component_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_get_gameObject = 16465776;
// "Signature": "void UnityEngine_GameObject__SetActive (UnityEngine_GameObject_o* __this, bool value, const MethodInfo* method);"
constexpr uintptr_t OFFSET_SetActive      = 16488416;
// "Signature": "void UnityEngine_Object__Destroy (UnityEngine_Object_o* obj, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Destroy        = 16599120;
// "Signature": "void CommonGetNewGunController__InitGunInfo (CommonGetNewGunController_o* __this, GF_Battle_Gun_o* gun, System_Action_o* action, const MethodInfo* method);"
constexpr uintptr_t OFFSET_InitGunInfo    = 5437312;

// ==========================================
// Turn End - Module I (Spot Animation)
// ==========================================

// "Signature": "void DeploymentSpotController__ShowTurnEndAnima (DeploymentSpotController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Spot_Show      = 30831600;
// "Signature": "void DeploymentSpotController__OnFinishAnimation (DeploymentSpotController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Spot_Finish1   = 30819680;
// "Signature": "void DeploymentSpotController__OnFinishAnimationEvent (DeploymentSpotController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Spot_Finish2   = 30819312;

// ==========================================
// Turn End - Module II (Turn Animation)
// ==========================================

// "Signature": "void DeploymentTurnAnimationController__PlayChangeTurnEndAnime (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Turn_PlayEnd   = 25400800;
// "Signature": "void DeploymentTurnAnimationController__ToGKTurn (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Turn_ToGK      = 25401328;
// "Signature": "void DeploymentTurnAnimationController__ToSFTurn (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Turn_ToSF      = 25402080;
// "Signature": "void DeploymentTurnAnimationController__DisactiveMain (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Turn_Disact    = 25400320;
// "Signature": "bool DeploymentTurnAnimationController__IsPlaying (DeploymentTurnAnimationController_o* __this, const MethodInfo* method);"
constexpr uintptr_t OFFSET_Turn_IsPlay    = 25400544;

// ==========================================
// Turn End - Module III (Camera Movement)
// ==========================================

// "Signature": "void DeploymentController__TriggerMoveCameraEvent (UnityEngine_Vector2_o target, bool move, float duration, float delay, bool recordPos, bool changescale, float setscale, System_Action_o* handle, const MethodInfo* method);"
constexpr uintptr_t OFFSET_MoveCamera     = 24073760;