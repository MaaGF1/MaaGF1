# 企业微信 Bot(消息通知) 测试工具

import requests
import json
import sys

class WeChatWorkNotifier:
    def __init__(self, webhook_key):
        self.webhook_key = webhook_key
        self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
    
    def send_message(self, message, msgtype="text"):
        """发送消息到企业微信群"""
        # 构造消息体
        if msgtype == "text":
            data = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
        else:
            print(f"不支持的消息类型: {msgtype}")
            return False
        
        try:
            # 发送POST请求
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"消息发送成功: {message}")
                    return True
                else:
                    print(f"消息发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"HTTP请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"发送消息时出错: {e}")
            return False
    
    def send_markdown(self, content):
        """发送Markdown格式消息"""
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.webhook_url,
                data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    print(f"Markdown消息发送成功")
                    return True
                else:
                    print(f"Markdown消息发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                print(f"HTTP请求失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"发送Markdown消息时出错: {e}")
            return False
    
    def test_connection(self):
        """测试webhook连接"""
        test_message = "企业微信机器人连接测试成功！"
        return self.send_message(test_message)

def main(webhook_key=None, message=None, msgtype="text"):
    """主函数"""
    
    # 获取webhook key
    if webhook_key is None:
        if len(sys.argv) > 1:
            webhook_key = sys.argv[1]
        else:
            webhook_key = input("请输入企业微信Webhook Key: ").strip()
    
    if not webhook_key:
        print("错误：需要提供Webhook Key")
        return
    
    # 获取消息内容
    if message is None:
        if len(sys.argv) > 2:
            message = sys.argv[2]
        else:
            message = input("请输入要发送的消息: ").strip()
    
    if not message:
        print("错误：消息内容不能为空")
        return
    
    # 获取消息类型（可选）
    if len(sys.argv) > 3:
        msgtype = sys.argv[3]
    
    # 创建通知器实例
    notifier = WeChatWorkNotifier(webhook_key)
    
    # 发送消息
    if msgtype == "markdown":
        success = notifier.send_markdown(message)
    else:
        success = notifier.send_message(message, msgtype)
    
    if not success:
        sys.exit(1)

def test_mode():
    """测试模式"""
    print("=== 企业微信机器人测试模式 ===")
    webhook_key = input("请输入企业微信Webhook Key: ").strip()
    
    if not webhook_key:
        print("错误：需要提供Webhook Key")
        return
    
    notifier = WeChatWorkNotifier(webhook_key)
    
    # 测试连接
    print("\n正在测试连接...")
    if notifier.test_connection():
        print("连接测试成功！")
        
        # 交互式发送消息
        while True:
            print("\n选择操作：")
            print("1. 发送文本消息")
            print("2. 发送Markdown消息")
            print("3. 退出")
            
            choice = input("请选择 (1-3): ").strip()
            
            if choice == "1":
                message = input("请输入文本消息: ").strip()
                if message:
                    notifier.send_message(message)
            elif choice == "2":
                message = input("请输入Markdown内容: ").strip()
                if message:
                    notifier.send_markdown(message)
            elif choice == "3":
                print("退出测试模式")
                break
            else:
                print("无效选择，请重试")
    else:
        print("连接测试失败，请检查Webhook Key是否正确")

if __name__ == "__main__":
    # 如果没有参数，进入测试模式
    if len(sys.argv) == 1:
        test_mode()
    else:
        main()