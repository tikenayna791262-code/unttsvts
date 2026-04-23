import os
import yaml
import sys

class ConfigManager:
    def __init__(self, config_path='config/settings.yaml'):
        # 处理打包后的路径偏移
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.full_path = os.path.join(self.base_dir, config_path)
        self.config = self._load_file()

    def _load_file(self):
        if not os.path.exists(self.full_path):
            return {}
        with open(self.full_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get(self, key_path, default=None):
        keys = key_path.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path, value):
        """动态设置并保存配置"""
        keys = key_path.split('.')
        curr = self.config
        for k in keys[:-1]:
            curr = curr.setdefault(k, {})
        curr[keys[-1]] = value
        
        # 立即持久化到硬盘
        with open(self.full_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

# 统一实例
cfg = ConfigManager()