import time
import math
import sys
import os
import gc
import json
import atexit
from typing import Dict, Any, Optional

# MaaFramework Imports
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

# Load config.py (Keep consistency with log.py)
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Log function import (Optional, for internal debugging)
try:
    from .log import MaaLog_Debug, MaaLog_Info
except ImportError:
    # Fallback if log module is not fully initialized yet
    def MaaLog_Debug(msg): print(f"[Matlab-DEBUG] {msg}")
    def MaaLog_Info(msg): print(f"[Matlab-INFO] {msg}")

################################################################################ Part I : The Calculation Engine ################################################################################

class _MatlabEngine:
    """
    Singleton engine providing Turing-complete calculation environment.
    Stores variables and executes syntax.
    """
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self._call_count = 0
        MaaLog_Debug("_MatlabEngine initialized")

    def _get_context(self) -> Dict[str, Any]:
        """
        Construct the execution context.
        Injects built-in functions and current variables.
        """
        # Copy current variables to context
        ctx = self.variables.copy()
        
        # Inject System Constants/Functions
        ctx['_get_time'] = time.time()
        ctx['math'] = math
        ctx['abs'] = abs
        ctx['round'] = round
        ctx['min'] = min
        ctx['max'] = max
        ctx['int'] = int
        ctx['float'] = float
        ctx['str'] = str
        
        return ctx

    def update_variables(self, ctx: Dict[str, Any]):
        """
        Persist variables from context back to storage.
        Filters out built-ins and temporary system vars.
        """
        protected_keys = [
            '_get_time', 'math', '__builtins__', 
            'abs', 'round', 'min', 'max', 'int', 'float', 'str'
        ]
        
        for k, v in ctx.items():
            if k not in protected_keys:
                self.variables[k] = v

    def clear(self, target: str):
        """Memory management"""
        if target == 'all':
            self.variables.clear()
            MaaLog_Debug("MatlabEngine memory cleared (all)")
        elif target in self.variables:
            del self.variables[target]
            MaaLog_Debug(f"MatlabEngine variable cleared: {target}")

    def execute_command(self, syntax: str) -> bool:
        """
        Execute assignment or void function (e.g., "A = 1 + 2")
        """
        try:
            self._call_count += 1
            
            # Handle special 'clear' command
            if syntax.strip().startswith("clear "):
                target = syntax.strip().split(" ", 1)[1].strip()
                self.clear(target)
                return True

            ctx = self._get_context()
            
            # Execute with restricted builtins for basic safety
            exec(syntax, {"__builtins__": {}}, ctx)
            
            # Save state
            self.update_variables(ctx)
            
            # Periodic GC
            if self._call_count % 100 == 0:
                gc.collect()
                
            return True
        except Exception as e:
            MaaLog_Debug(f"Matlab Execution Error: '{syntax}' -> {e}")
            return False

    def evaluate_condition(self, syntax: str) -> bool:
        """
        Evaluate boolean expression (e.g., "A > 10")
        """
        try:
            ctx = self._get_context()
            # Eval returns the result of the expression
            result = eval(syntax, {"__builtins__": {}}, ctx)
            return bool(result)
        except Exception as e:
            MaaLog_Debug(f"Matlab Evaluation Error: '{syntax}' -> {e}")
            return False
            
    def get_variable(self, name: str) -> Any:
        """External access to variables (e.g. for logging)"""
        return self.variables.get(name, None)

# Global Singleton Instance
_matlab_engine = _MatlabEngine()

################################################################################ Part II : The Action Class ################################################################################

class _MatlabAction(CustomAction):
    """
    Action wrapper for MatlabEngine.
    Handles JSON parsing and Context flow control.
    """
    def __init__(self):
        super().__init__()
        self._action_count = 0
        MaaLog_Debug("_MatlabAction singleton created")

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            self._action_count += 1
            MaaLog_Debug(f"=== [Matlab] Run Start (Count: {self._action_count}) ===")
            
            # 1. Check argv
            if not argv:
                MaaLog_Debug("[Matlab] Error: argv is None")
                return CustomAction.RunResult(success=False)
            
            MaaLog_Debug(f"[Matlab] Node Name: {argv.node_name}")
            
            # 2. Parse Param
            param = argv.custom_action_param
            MaaLog_Debug(f"[Matlab] Raw Param Type: {type(param)}")
            MaaLog_Debug(f"[Matlab] Raw Param Value: {param}")

            if isinstance(param, str):
                try:
                    param = json.loads(param)
                    MaaLog_Debug("[Matlab] JSON parsed successfully")
                except json.JSONDecodeError as e:
                    MaaLog_Debug(f"[Matlab] JSON Error: {e}")
                    return CustomAction.RunResult(success=False)
            
            if not isinstance(param, dict):
                 MaaLog_Debug(f"[Matlab] Error: Param is {type(param)}, expected dict")
                 return CustomAction.RunResult(success=False)

            # 3. Get Syntax
            syntax = param.get('syntax', '')
            MaaLog_Debug(f"[Matlab] Syntax: '{syntax}'")
            
            if not syntax:
                MaaLog_Debug("[Matlab] Empty syntax, returning True")
                return CustomAction.RunResult(success=True)

            # 4. Check Logic Mode
            target_true = param.get('true')
            target_false = param.get('false')
            MaaLog_Debug(f"[Matlab] Targets -> True: {target_true}, False: {target_false}")

            if target_true or target_false:
                # --- Logic Mode ---
                MaaLog_Debug("[Matlab] Entering Logic Mode")
                
                # 4.1 Evaluate
                try:
                    result = _matlab_engine.evaluate_condition(syntax)
                    MaaLog_Debug(f"[Matlab] Evaluation Result: {result} (Type: {type(result)})")
                except Exception as e:
                    MaaLog_Debug(f"[Matlab] Engine Eval Exception: {e}")
                    return CustomAction.RunResult(success=False)
                
                # 4.2 Branching
                target_node = None
                if result:
                    if target_true:
                        target_node = target_true
                        MaaLog_Debug(f"[Matlab] Condition TRUE. Target: {target_node}")
                    else:
                        MaaLog_Debug("[Matlab] Condition TRUE. No Target.")
                else:
                    if target_false:
                        target_node = target_false
                        MaaLog_Debug(f"[Matlab] Condition FALSE. Target: {target_node}")
                    else:
                        MaaLog_Debug("[Matlab] Condition FALSE. No Target.")

                # 4.3 Override
                if target_node:
                    if not isinstance(target_node, str):
                        MaaLog_Debug(f"[Matlab] Error: Target node is not string! It is {type(target_node)}")
                        target_node = str(target_node) 
                        
                    MaaLog_Debug(f"[Matlab] Attempting override_next to: {target_node}")

                    try:
                        context.override_next(argv.node_name, [target_node])
                        MaaLog_Debug("[Matlab] override_next called successfully")
                    except Exception as e:
                        MaaLog_Debug(f"[Matlab] Context Override Exception: {e}")
                        return CustomAction.RunResult(success=False)

            else:
                # --- Execution Mode ---
                MaaLog_Debug("[Matlab] Entering Execution Mode")
                try:
                    success = _matlab_engine.execute_command(syntax)
                    MaaLog_Debug(f"[Matlab] Execution Success: {success}")
                    if not success:
                        return CustomAction.RunResult(success=False)
                except Exception as e:
                    MaaLog_Debug(f"[Matlab] Engine Exec Exception: {e}")
                    return CustomAction.RunResult(success=False)

            MaaLog_Debug("=== [Matlab] Run Finished Successfully ===")
            return CustomAction.RunResult(success=True)

        except Exception as e:
            # Catch all unexpected Python exceptions
            import traceback
            tb = traceback.format_exc()
            MaaLog_Debug(f"MatlabAction CRITICAL UNCAUGHT ERROR: {e}")
            MaaLog_Debug(f"Traceback: {tb}")
            return CustomAction.RunResult(success=False)

################################################################################ Part III : Registration System ################################################################################

# Reuse the robust registration logic from log.py
_registration_status = {
    'registered': False,
    'instance': None
}

def _get_or_create_instance():
    if _registration_status['instance'] is None:
        _registration_status['instance'] = _MatlabAction()
    return _registration_status['instance']

def _safe_register_matlab(action_name: str):
    if _registration_status['registered']:
        return
    
    instance = _get_or_create_instance()
    success = AgentServer.register_custom_action(action_name, instance)
    
    if success:
        _registration_status['registered'] = True
        MaaLog_Debug(f"Successfully registered {action_name}")
    else:
        MaaLog_Debug(f"Failed to register {action_name}")

def custom_action_decorator(name: str):
    def wrapper(cls):
        _safe_register_matlab(name)
        return cls
    return wrapper

# Register the action
@custom_action_decorator("matlab_calculate")
class MatlabCalculateAction:
    pass

################################################################################ Part IV : Cleanup ################################################################################

def cleanup_matlab_resources():
    try:
        _matlab_engine.clear('all')
        gc.collect()
        MaaLog_Debug("Matlab resources cleaned up")
    except:
        pass

atexit.register(cleanup_matlab_resources)

# Export engine for external access (e.g. by log.py)
def get_matlab_engine():
    return _matlab_engine