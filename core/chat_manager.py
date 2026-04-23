import os
import time
from datetime import datetime
from config.config_loader import cfg

class ChatManager:
    def __init__(self):
        # 强制使用绝对路径防止丢失
        current_dir = os.path.dirname(os.path.abspath(__file__)) # core 目录
        project_root = os.path.dirname(current_dir) # 项目根目录
        self.log_dir = os.path.join(project_root, "logs")
        
        print(f"[*] 日志系统初始化中... 路径: {self.log_dir}")
        
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                print("[*] Logs 文件夹创建成功。")
            except Exception as e:
                print(f"[!] 无法创建日志文件夹: {e}")
            
        self.local_log_path = os.path.join(self.log_dir, "chat_local.log")
        self.tg_log_path = os.path.join(self.log_dir, "chat_tg.log")

    def log_message(self, role, content, channel="local"):
        """
        记录对话并输出到终端
        channel: "local" 或 "tg"
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{role.upper()}] ({channel}): {content}\n"
        
        # 1. 终端实时打印 (带点赛博味的颜色，Windows 兼容)
        color = "\033[92m" if role == "user" else "\033[96m" # 绿色用户，青色 Una
        print(f"{color}{log_entry}\033[0m", end="")

        # 2. 写入对应日志文件
        target_file = self.local_log_path if channel == "local" else self.tg_log_path
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

# 实例化
chat_logger = ChatManager()