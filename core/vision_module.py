import pyautogui
import base64
from io import BytesIO
from PIL import Image

class VisionModule:
    def __init__(self):
        # 优化 PyAutoGUI 性能
        pyautogui.FAILSAFE = True

    def capture_screen(self):
        """截取当前屏幕并返回 PIL Image 对象"""
        try:
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            print(f"[!] 视觉系统故障: {e}")
            return None

    def image_to_base64(self, image):
        """将 PIL 图片转换为 Base64 字符串以便发送给 AI"""
        if image is None:
            return None
        
        buffered = BytesIO()
        # 适当压缩以减少 API 传输压力
        image.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str

# 实例化
vision_sys = VisionModule()