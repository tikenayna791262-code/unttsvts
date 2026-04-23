import os
import sys
import yaml

class ConfigLoader:
    def __init__(self):
        # 1. 核心路径识别：识别项目根目录
        if hasattr(sys, '_MEIPASS'):
            self.base_dir = sys._MEIPASS  # 打包后的路径
        else:
            # 这里的 .dirname 嵌套层数取决于 config_loader.py 的深度
            # 因为它在 config/ 文件夹下，所以需要向上跳一级
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.config_path = os.path.join(self.base_dir, "config", "config.yaml")
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            default = {
                "user_name": "蜂群",
                "ai_provider": {"model": "gpt-4o", "api_key": "", "base_url": "https://api.openai.com/v1"},
                "vts": {"enabled": True, "port": 8001}, # VTS 配置
                "tts": {"voice": "zh-CN-XiaoxiaoNeural"}
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default, f)
            return default
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get(self, key_path, default=None):
        keys = key_path.split('.')
        val = self.config
        try:
            for k in keys: val = val[k]
            return val
        except: return default

# 实例化
cfg = ConfigLoader()