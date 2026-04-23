import os
import time
from datetime import datetime
from PIL import ImageGrab

class VisionProcessor:
    def __init__(self, output_dir="captures"):
        self.output_dir = output_dir
        self._ensure_dir()
        self.session_counter = 1  # 启动后的截图序号

    def _ensure_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_filename(self):
        """生成格式如: 20231027_001.png 的文件名"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_{self.session_counter:03d}.png"
        self.session_counter += 1
        return os.path.join(self.output_dir, filename)

    def capture_screen_area(self, bbox):
        """执行截图并保存"""
        file_path = self.generate_filename()
        # bbox 格式: (x1, y1, x2, y2)
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        img.save(file_path)
        return file_path

    def local_ocr(self, file_path):
        """
        在这里对接你未来的 OCR (如 PaddleOCR 或 百度OCR)
        目前先做模拟返回
        """
        print(f"[*] 正在处理文件: {file_path}")
        # 实际代码示例 (如果以后用 paddle):
        # result = ocr_engine.ocr(file_path)
        # return "\n".join([line[1][0] for line in result])
        
        return f"[模拟识别内容] 截图 {os.path.basename(file_path)} 中的文字信息"

    def build_una_prompt(self, user_prompt, ocr_text):
        """构建最终喂给 AI 的字符串"""
        return (
            f"--- 视觉上下文信息 ---\n"
            f"识别到的文字内容：\n{ocr_text}\n"
            f"----------------------\n"
            f"基于以上内容，请回答：{user_prompt}"
        )

# 全局单例
vision_manager = VisionProcessor()