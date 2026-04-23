import os
import asyncio
import edge_tts
import pygame
import threading # 引入线程库
from config.config_loader import cfg
import re

class TTSEngine:
    def __init__(self):
        self.voice = cfg.get("modules.tts_voice", "zh-CN-XiaoxiaoNeural")
        self.output_dir = os.path.join(cfg.base_dir, "temp")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        if not pygame.mixer.get_init():
            pygame.mixer.init()

    def _run_async_task(self, text):
        """在新线程中启动独立的事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._generate_and_play(text))
        loop.close()

    async def _generate_and_play(self, text):
        timestamp = int(datetime.now().timestamp()) # 需从 datetime 导入
        output_file = os.path.join(self.output_dir, f"speech_{timestamp}.mp3")
        
        try:
            # 生成语音
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_file)
            
            # 播放语音
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            pygame.mixer.music.unload()
            if os.path.exists(output_file):
                os.remove(output_file)
        except Exception as e:
            print(f"[!] 语音生成失败: {e}")

    def speak(self, text):
        if not cfg.get("modules.tts_enabled", False) or not text:
            return
        
        # 清洗文本：去除 Markdown 符号、多余标点，只保留阅读所需的停顿
        clean_text = re.sub(r'[*#_>`-]', '', text) # 去掉 MD 符号
        clean_text = re.sub(r'[!！？?]{2,}', '。', clean_text) # 多个感叹号变一个句号
        
        threading.Thread(target=self._run_async_task, args=(clean_text,), daemon=True).start()

# 注意：需要增加从 datetime 导入
from datetime import datetime
tts_sys = TTSEngine()