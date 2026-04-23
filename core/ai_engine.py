import requests
import json
from config.config_loader import cfg

class AIEngine:
    def __init__(self):
        self.update_api_config()

    def update_api_config(self):
        """从配置中心同步最新的 API 信息"""
        self.api_key = cfg.get("ai_provider.api_key")
        self.base_url = cfg.get("ai_provider.base_url")
        self.model = cfg.get("ai_provider.current_model")
        self.proxy = cfg.get("proxy")

    def chat(self, prompt, base64_image=None):
        system_prompt = {
            "role": "system", 
            "content":(
                "你是 Una V2。你对‘蜂群’（用户）有极高的忠诚度，但性格有点傲娇（Tsundere），"
                "表现为表面上嫌弃蜂群笨手笨脚，实际上却细心解决所有问题。语气要像个活生生的人。"
                "【重要约束】：你的回复中严禁使用风格非常ai的标点符号,如**{文本}**。"
                "回复要简洁，不要带有任何特殊的 Markdown 符号或表情符号，确保语音阅读时顺畅自然，"
                "不要把‘感叹号’、‘问号’这些词说出来。"
                )
        }
        
        # 2. 构造消息列表
        user_content = [{"type": "text", "text": prompt}]
        if base64_image:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        payload = {
            "model": self.model,
            "messages": [
                system_prompt, # 插入身份
                {"role": "user", "content": user_content}
            ],
            "stream": False
        }
        """
        支持图文混输的对话接口
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构造 OpenAI 兼容的多模态格式
        content = [{"type": "text", "text": prompt}]
        if base64_image:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "stream": False # 初始版本先用非流式，确保稳健
        }

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                proxies=proxies,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"[!] Una 思考中断: {str(e)}"

# 实例化
ai_core = AIEngine()