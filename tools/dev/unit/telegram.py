# Telegram Bot (with Chat_ID) 测试工具

import requests
import json
import sys

class TelegramNotifier:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = None
    
    def get_latest_chat_id(self):
        """自动获取最新的chat_id"""
        url = f"{self.base_url}/getUpdates"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                updates = response.json()
                if updates['result']:
                    # 获取最新的消息
                    latest_update = updates['result'][-1]
                    if 'message' in latest_update:
                        chat_id = latest_update['message']['chat']['id']
                        username = latest_update['message']['from'].get('username', 'Unknown')
                        print(f"自动获取到chat_id: {chat_id} (用户: {username})")
                        return chat_id
                    else:
                        print("最新更新中没有找到消息")
                        return None
                else:
                    print("没有找到任何消息，请先给bot发送一条消息")
                    return None
            else:
                print(f"获取更新失败: {response.text}")
                return None
        except Exception as e:
            print(f"获取chat_id时出错: {e}")
            return None
    
    def send_message(self, message, auto_get_chat_id=True):
        """发送消息到Telegram"""
        # 如果没有chat_id且允许自动获取，则自动获取
        if self.chat_id is None and auto_get_chat_id:
            self.chat_id = self.get_latest_chat_id()
            if self.chat_id is None:
                print("无法获取chat_id，消息发送失败")
                return False
        
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': message
        }
        
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                print(f"消息发送成功: {message}")
                return True
            else:
                print(f"消息发送失败: {response.text}")
                return False
        except Exception as e:
            print(f"发送消息时出错: {e}")
            return False
    
    def set_chat_id(self, chat_id):
        """手动设置chat_id"""
        self.chat_id = chat_id
        print(f"已设置chat_id: {chat_id}")

def main(bot_token=None, message=None):

    # 第一个参数作为Bot_Token
    if bot_token is None:
        if len(sys.argv) > 1:
            bot_token = sys.argv[1]
        else:
            bot_token = input("请输入BOT_TOKEN: ").strip()
    
    if not bot_token:
        print("错误：需要提供BOT_TOKEN")
        return
    
    # 第二个参数作为Message
    if message is None:
        if len(sys.argv) > 2:
            message = sys.argv[2]
        else:
            message = input("请输入要发送的消息: ").strip()
    
    if not message:
        print("错误：消息内容不能为空")
        return
    
    # 创建通知器实例并发送消息
    notifier = TelegramNotifier(bot_token)
    notifier.send_message(message)

if __name__ == "__main__":
    main()