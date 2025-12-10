import json
import requests
import threading
import weakref
import gc
import time
import sys
import os
from typing import Optional, Dict, Any

# MaaFramework Imports
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

# Load config.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from utils import (get_telegram_config, is_telegram_configured, 
                   get_wechat_config, is_wechat_configured,
                   get_default_ext_notify, get_available_notifiers)

# Try import matlab engine
try:
    from .matlab import get_matlab_engine
except ImportError:
    get_matlab_engine = None

#################### Global Variables ####################

# Default Counter
Task_Counter = 0

# Log Control
Enable_MaaLog_Debug = 1
Enable_MaaLog_Info = 1

################################################################################ Part 0 : Logging Functions ################################################################################

def MaaLog_Debug(message):
    """Debug log output"""
    if Enable_MaaLog_Debug:
        print(f"[DEBUG] {message}")

def MaaLog_Info(message):
    """Info log output"""
    if Enable_MaaLog_Info:
        print(f"[INFO] {message}")

def set_debug_log(enabled):
    """Set debug log switch"""
    global Enable_MaaLog_Debug
    Enable_MaaLog_Debug = 1 if enabled else 0

def set_info_log(enabled):
    """Set info log switch"""
    global Enable_MaaLog_Info
    Enable_MaaLog_Info = 1 if enabled else 0

def get_Task_Counter():
    """Get current task run count"""
    global Task_Counter
    return Task_Counter

def reset_Task_Counter():
    """Reset task run count"""
    global Task_Counter
    Task_Counter = 0
    MaaLog_Debug("Task_Counter has been reset to 0")

################################################################################ Part I : Ultra-Lightweight Services ################################################################################

class _TelegramService:
    """Ultra-lightweight Telegram service"""
    def __init__(self):
        self.session = None
        self._config_cache = None
        self._message_count = 0
        MaaLog_Debug("_TelegramService initialized")
    
    def _get_session(self):
        """Get or create session with current config"""
        bot_token, chat_id = get_telegram_config()
        current_config = (bot_token, chat_id)
        
        if not bot_token or not chat_id:
            return None, None, None
        
        if current_config != self._config_cache or self.session is None:
            if self.session:
                try:
                    self.session.close()
                except:
                    pass
            
            self.session = requests.Session()
            # More aggressive connection pool configuration
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,
                max_retries=0
            )
            self.session.mount('https://', adapter)
            self.session.mount('http://', adapter)
            self._config_cache = current_config
            MaaLog_Debug(f"Telegram session recreated")
        
        return self.session, bot_token, chat_id
    
    def send_message(self, message):
        """Send message to Telegram"""
        session, bot_token, chat_id = self._get_session()
        
        if not session:
            MaaLog_Debug("Telegram not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message}
        
        try:
            response = session.post(url, data=data, timeout=5)
            
            self._message_count += 1
            if response.status_code == 200:
                MaaLog_Debug(f"Telegram message sent successfully")
                return True
            else:
                MaaLog_Debug(f"Telegram send failed: {response.status_code}")
                return False
                
        except Exception as e:
            MaaLog_Debug(f"Telegram error: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None
        self._config_cache = None

class _WeChatService:
    """Ultra-lightweight WeChat service"""
    def __init__(self):
        self.session = None
        self._config_cache = None
        self._message_count = 0
        MaaLog_Debug("_WeChatService initialized")
    
    def _get_session(self):
        """Get or create session with current config"""
        webhook_key = get_wechat_config()
        
        if not webhook_key:
            return None, None
        
        if webhook_key != self._config_cache or self.session is None:
            if self.session:
                try:
                    self.session.close()
                except:
                    pass
            
            self.session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,
                max_retries=0
            )
            self.session.mount('https://', adapter)
            self.session.mount('http://', adapter)
            self._config_cache = webhook_key
            MaaLog_Debug(f"WeChat session recreated")
        
        return self.session, webhook_key
    
    def send_message(self, message, msgtype="text"):
        """Send message to WeChat"""
        session, webhook_key = self._get_session()
        
        if not session:
            MaaLog_Debug("WeChat not configured")
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
        
        if msgtype == "text":
            data = {"msgtype": "text", "text": {"content": message}}
        elif msgtype == "markdown":
            data = {"msgtype": "markdown", "markdown": {"content": message}}
        else:
            MaaLog_Debug(f"Unsupported msgtype: {msgtype}")
            return False
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = session.post(
                url, 
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers=headers,
                timeout=5
            )
            
            self._message_count += 1
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    MaaLog_Debug(f"WeChat message sent successfully")
                    return True
                else:
                    MaaLog_Debug(f"WeChat send failed: {result.get('errmsg')}")
                    return False
            else:
                MaaLog_Debug(f"WeChat HTTP failed: {response.status_code}")
                return False
                
        except Exception as e:
            MaaLog_Debug(f"WeChat error: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None
        self._config_cache = None

# Module-level service instances
_telegram_service = _TelegramService()
_wechat_service = _WeChatService()

################################################################################ Part II : Singleton Handler System ################################################################################

class _SingletonHandler:
    """Centralized handler for all action types"""
    
    def __init__(self):
        self._call_count = 0
        self._handlers = {
            'log': self._handle_log,
            'telegram': self._handle_telegram, 
            'wechat': self._handle_wechat,
            'extnotify': self._handle_extnotify
        }
        MaaLog_Debug("SingletonHandler initialized")
    
    def handle(self, action_type: str, param) -> bool:
        """Main entry point for all action calls"""
        self._call_count += 1
        
        try:
            parsed_param = self._parse_param(param)
            handler = self._handlers.get(action_type)
            
            if not handler:
                MaaLog_Debug(f"Unknown action type: {action_type}")
                return False
            
            result = handler(parsed_param)
            
            # Periodic cleanup and statistics
            if self._call_count % 50 == 0:
                MaaLog_Debug(f"Handler total calls: {self._call_count}")
                self._cleanup_resources()
            
            return result
            
        except Exception as e:
            MaaLog_Debug(f"Handler error for {action_type}: {e}")
            return False
    
    def _cleanup_resources(self):
        """Periodic resource cleanup"""
        try:
            # Force garbage collection (use with caution)
            if self._call_count % 100 == 0:
                gc.collect()
                MaaLog_Debug(f"Performed GC after {self._call_count} calls")
        except Exception as e:
            MaaLog_Debug(f"Cleanup error: {e}")
    
    def _parse_param(self, param):
        """Parse parameter"""
        if not param:
            return None
        
        if isinstance(param, str):
            try:
                return json.loads(param)
            except json.JSONDecodeError:
                return param
        
        return param
    
    def _process_parameters(self, parameters: dict) -> dict:
        """Process special parameters"""
        global Task_Counter
        
        # 1. Start with Matlab variables as the base context
        # This allows "{Index}" in the message to work without explicit 'parameters' mapping
        try:
            if get_matlab_engine:
                # Copy to avoid modifying the engine's storage directly
                processed = get_matlab_engine().variables.copy()
            else:
                processed = {}
        except Exception:
            processed = {}

        # 2. Process explicit parameters from JSON
        # (This allows JSON params to override Matlab vars or use special tokens like Task_Counter)
        for key, value in parameters.items():
            if isinstance(value, str):
                if value == "{Task_Counter}":
                    processed[key] = Task_Counter
                elif value == "{increment_Task_Counter}":
                    Task_Counter += 1
                    processed[key] = Task_Counter
                # Check if value matches a variable in Matlab engine (e.g. "my_val": "{Index}")
                elif value.startswith("{") and value.endswith("}"):
                    var_name = value[1:-1]
                    # If the var exists in our base processed (which has matlab vars), use it
                    if var_name in processed:
                        processed[key] = processed[var_name]
                    else:
                        processed[key] = value
                else:
                    processed[key] = value
            else:
                processed[key] = value

        return processed
    
    def _format_message(self, template: str, parameters: dict) -> str:
        """Format message"""
        try:
            processed = self._process_parameters(parameters)
            # Use safe formatting to avoid crash if key is missing? 
            # Standard .format() will raise KeyError if key is missing, which is caught below.
            return template.format(**processed)
        except Exception as e:
            # Fallback: if format fails (e.g. missing key), return raw template
            # MaaLog_Debug(f"Message format error: {e}")
            return template
    
    def _handle_message_routing(self, parsed_param, default_handler, string_handler, dict_handler):
        """Common message routing logic"""
        if parsed_param is None:
            return default_handler()
        elif isinstance(parsed_param, str):
            return string_handler(parsed_param)
        elif isinstance(parsed_param, dict):
            return dict_handler(parsed_param)
        else:
            return string_handler(str(parsed_param))
    
    # Log handlers
    def _handle_log(self, parsed_param):
        return self._handle_message_routing(
            parsed_param,
            lambda: self._log_default(),
            lambda msg: self._log_string(msg),
            lambda d: self._log_dict(d)
        )
    
    def _log_default(self):
        MaaLog_Info("Default log message")
        return True
    
    def _log_string(self, message: str):
        MaaLog_Info(message)
        return True
    
    def _log_dict(self, param_dict: dict):
        log_type = param_dict.get('type', 'info')
        template = param_dict.get('message', 'Default log message')
        parameters = param_dict.get('parameters', {})
        
        message = self._format_message(template, parameters)
        
        if log_type.lower() == 'debug':
            MaaLog_Debug(message)
        else:
            MaaLog_Info(message)
        
        return True
    
    # Telegram handlers
    def _handle_telegram(self, parsed_param):
        return self._handle_message_routing(
            parsed_param,
            lambda: _telegram_service.send_message("Default Telegram message"),
            lambda msg: _telegram_service.send_message(msg),
            lambda d: self._telegram_dict(d)
        )
    
    def _telegram_dict(self, param_dict: dict):
        template = param_dict.get('message', 'Default Telegram message')
        parameters = param_dict.get('parameters', {})
        
        message = self._format_message(template, parameters)
        return _telegram_service.send_message(message)
    
    # WeChat handlers
    def _handle_wechat(self, parsed_param):
        return self._handle_message_routing(
            parsed_param,
            lambda: _wechat_service.send_message("Default WeChat message"),
            lambda msg: _wechat_service.send_message(msg),
            lambda d: self._wechat_dict(d)
        )
    
    def _wechat_dict(self, param_dict: dict):
        template = param_dict.get('message', 'Default WeChat message')
        parameters = param_dict.get('parameters', {})
        msgtype = param_dict.get('msgtype', 'text')
        
        message = self._format_message(template, parameters)
        return _wechat_service.send_message(message, msgtype)
    
    # ExtNotify handlers
    def _handle_extnotify(self, parsed_param):
        return self._handle_message_routing(
            parsed_param,
            lambda: self._extnotify_default(),
            lambda msg: self._extnotify_string(msg),
            lambda d: self._extnotify_dict(d)
        )
    
    def _send_with_fallback(self, message, msgtype="text", preferred=None):
        """Send with fallback"""
        default_platform = preferred or get_default_ext_notify()
        available = get_available_notifiers()
        
        if not available:
            return False
        
        order = []
        if default_platform and default_platform in available:
            order.append(default_platform)
        
        for platform in available:
            if platform not in order:
                order.append(platform)
        
        for platform in order:
            try:
                if platform == 'telegram':
                    if _telegram_service.send_message(message):
                        return True
                elif platform == 'wechat':
                    if _wechat_service.send_message(message, msgtype):
                        return True
            except Exception as e:
                MaaLog_Debug(f"{platform} error: {e}")
                continue
        
        return False
    
    def _extnotify_default(self):
        return self._send_with_fallback("Default smart notification")
    
    def _extnotify_string(self, message: str):
        return self._send_with_fallback(message)
    
    def _extnotify_dict(self, param_dict: dict):
        template = param_dict.get('message', 'Default smart notification')
        parameters = param_dict.get('parameters', {})
        msgtype = param_dict.get('msgtype', 'text')
        preferred = param_dict.get('platform', None)
        
        message = self._format_message(template, parameters)
        return self._send_with_fallback(message, msgtype, preferred)

# Global singleton handler instance
_global_handler = _SingletonHandler()

################################################################################ Part III : True Singleton Action Classes ################################################################################

class _UnifiedAction(CustomAction):
    """True unified singleton Action"""
    
    def __init__(self):
        super().__init__()
        self._call_count = 0
        MaaLog_Debug("_UnifiedAction singleton created")
    
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        """Unified handling of all action calls"""
        try:
            self._call_count += 1
            
            # Determine processing type based on action name
            action_name = argv.custom_action_name
            param = argv.custom_action_param
            
            # Map action names to processing types
            action_type_map = {
                'parametric_log': 'log',
                'parametric_telegram': 'telegram',
                'parametric_wechat': 'wechat',
                'parametric_extnotify': 'extnotify'
            }
            
            action_type = action_type_map.get(action_name)
            if not action_type:
                MaaLog_Debug(f"Unknown action name: {action_name}")
                return CustomAction.RunResult(success=False)
            
            # Delegate to global handler
            result = _global_handler.handle(action_type, param)
            
            if self._call_count % 20 == 0:
                MaaLog_Debug(f"UnifiedAction calls: {self._call_count}")
            
            return CustomAction.RunResult(success=result)
            
        except Exception as e:
            MaaLog_Debug(f"UnifiedAction error: {e}")
            return CustomAction.RunResult(success=False)

################################################################################ Part IV : Registration Prevention System ################################################################################

# Global registration status tracking
_registration_status = {
    'registered_actions': set(),
    'singleton_instance': None,
    'registration_count': 0
}

def _get_or_create_singleton():
    """Get or create unique Action instance"""
    if _registration_status['singleton_instance'] is None:
        _registration_status['singleton_instance'] = _UnifiedAction()
        MaaLog_Debug("Created singleton action instance")
    return _registration_status['singleton_instance']

def _safe_register_action(action_name: str):
    """Safe registration to prevent duplicates"""
    if action_name in _registration_status['registered_actions']:
        MaaLog_Debug(f"Action {action_name} already registered, skipping")
        return
    
    singleton_instance = _get_or_create_singleton()
    
    # Register using unified singleton instance
    success = AgentServer.register_custom_action(action_name, singleton_instance)
    
    if success:
        _registration_status['registered_actions'].add(action_name)
        _registration_status['registration_count'] += 1
        MaaLog_Debug(f"Successfully registered {action_name} (total: {_registration_status['registration_count']})")
    else:
        MaaLog_Debug(f"Failed to register {action_name}")

################################################################################ Part V : Modified Decorators ################################################################################

# Rewrite decorators to use safe registration
def custom_action_decorator(name: str):
    """Custom decorator to prevent duplicate registration"""
    def wrapper(action_class):
        # Don't create new instances, use safe registration directly
        _safe_register_action(name)
        return action_class
    return wrapper

# Use custom decorator to replace AgentServer.custom_action
@custom_action_decorator("parametric_log")
class ParametricLogAction:
    pass

@custom_action_decorator("parametric_telegram") 
class ParametricTelegramAction:
    pass

@custom_action_decorator("parametric_wechat")
class ParametricWeChatAction:
    pass

@custom_action_decorator("parametric_extnotify")
class ParametricExtNotifyAction:
    pass

################################################################################ Part VI : Monitoring and Debugging ################################################################################

def get_registration_stats():
    """Get registration statistics"""
    return {
        'registered_actions': list(_registration_status['registered_actions']),
        'registration_count': _registration_status['registration_count'],
        'handler_calls': getattr(_global_handler, '_call_count', 0),
        'action_calls': getattr(_registration_status['singleton_instance'], '_call_count', 0),
        'telegram_messages': getattr(_telegram_service, '_message_count', 0),
        'wechat_messages': getattr(_wechat_service, '_message_count', 0)
    }

def print_registration_status():
    """Print registration status"""
    stats = get_registration_stats()
    MaaLog_Info(f"Registration Status: {stats}")

################################################################################ Part VII : Cleanup and Compatibility ################################################################################

def cleanup_all_resources():
    """Cleanup module-level resources"""
    try:
        MaaLog_Debug("Cleaning up global resources...")
        _telegram_service.cleanup()
        _wechat_service.cleanup()
        
        # Cleanup global handler
        if hasattr(_global_handler, '_cleanup_resources'):
            _global_handler._cleanup_resources()
        
        gc.collect()
        MaaLog_Debug("Global cleanup completed")
    except Exception as e:
        MaaLog_Debug(f"Cleanup error: {e}")

# Register cleanup
import atexit
atexit.register(cleanup_all_resources)

def force_cleanup():
    """Force cleanup - use carefully"""
    cleanup_all_resources()

# Legacy compatibility classes
class TelegramNotifier:
    def __init__(self, *args, **kwargs): pass
    def send_message(self, msg): return _telegram_service.send_message(msg)
    def cleanup(self): pass
    @classmethod
    def cleanup_all_instances(cls): pass

class WeChatWorkNotifier:
    def __init__(self, *args, **kwargs): pass
    def send_message(self, msg, msgtype="text"): return _wechat_service.send_message(msg, msgtype)
    def cleanup(self): pass
    @classmethod
    def cleanup_all_instances(cls): pass

class ResourceManager:
    def __init__(self): pass
    def register_action(self, action): pass
    def perform_cleanup(self): pass
    def get_stats(self): return get_registration_stats()

class ParametricBaseAction:
    """Legacy compatibility"""
    pass

# Print status when module loads
MaaLog_Debug("Parametric actions module loaded with singleton architecture")
print_registration_status()