import os
import sys
import time
import uuid
from datetime import datetime
from PIL import ImageGrab
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit
from PyQt5.QtCore import Qt

# 核心：导入视觉处理器与配置逻辑
from core.vision_processor import vision_manager
from config.config_loader import cfg

class OcrManager:
    """
    OCR 管理器 - 稳定版
    1. 解决了日志不更新问题（增加强制实时输出）
    2. 解决了图片覆盖问题（引入 UUID 唯一标识）
    3. 移除了有 Bug 的划选功能，改为全屏/粘贴板模式
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.log_to_terminal("[系统] OCR 逻辑中心已启动。")

    def log_to_terminal(self, message):
        """同步输出到终端、主界面和日志文件"""
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"[{time_str}] {message}"
        
        # 1. 终端实时打印 (强制刷新)
        print(full_msg, flush=True)
        
        # 2. 尝试写入 chat_logger (日志文件)
        try:
            from core.chat_manager import chat_logger
            chat_logger.info(message)
        except Exception as e:
            print(f"[日志异常] 无法写入 log 文件: {e}")

    # 请在生成文件名的地方替换为这个逻辑：
    def generate_unique_filename(self):
        """生成绝对唯一的图片路径，防止覆盖"""
        # 使用 %f 包含微秒，确保文件名绝对唯一
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"vision_{timestamp}.png"
        
        # 确保 temp 文件夹存在
        temp_dir = os.path.join(os.getcwd(), "temp")
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir)
            except:
                pass
                
        return os.path.join(temp_dir, filename)

    def start_screenshot_ocr(self):
        """
        全屏 OCR 文字识别
        """
        self.log_to_terminal("正在捕获全屏进行文字提取...")
        self.main_window.status_light.setText("● 正在读取屏幕文字...")
        
        # 隐藏窗口
        self.main_window.setWindowOpacity(0)
        QApplication.processEvents()
        time.sleep(0.3)
        
        try:
            # 解决覆盖保存：生成唯一路径
            file_path = self.generate_unique_path()
            screenshot = ImageGrab.grab()
            screenshot.save(file_path)
            
            # 恢复窗口
            self.main_window.setWindowOpacity(cfg.get('ui.opacity', 0.9))
            
            # 执行本地 OCR
            self.log_to_terminal(f"图片已暂存: {os.path.basename(file_path)}")
            detected_text = vision_manager.local_ocr(file_path)
            
            self._handle_ocr_result(detected_text)
            
        except Exception as e:
            err_msg = f"OCR 识别失败: {str(e)}"
            self.log_to_terminal(f"[错误] {err_msg}")
            self.main_window.chat_display.append(f"<b style='color:red;'>{err_msg}</b>")
        finally:
            self.main_window.status_light.setText("● 系统就绪")

    def start_clipboard_ocr(self):
        """
        粘贴板图片 OCR 识别
        """
        clipboard = QApplication.clipboard()
        if not clipboard.mimeData().hasImage():
            self.log_to_terminal("OCR 失败: 粘贴板没有图片内容")
            self.main_window.chat_display.append("<i style='color:#777;'>[系统] 粘贴板空空如也，请先截图或复制图片。</i>")
            return

        try:
            self.log_to_terminal("正在从粘贴板读取图片并识别...")
            file_path = self.generate_unique_path()
            qimage = clipboard.image()
            qimage.save(file_path)
            
            detected_text = vision_manager.local_ocr(file_path)
            self._handle_ocr_result(detected_text)
            self.log_to_terminal("粘贴板文字提取成功")
            
        except Exception as e:
            self.log_to_terminal(f"[错误] 粘贴板处理异常: {e}")
        finally:
            self.main_window.status_light.setText("● 系统就绪")

    def _handle_ocr_result(self, text: str):
        """
        美化展示 OCR 识别出的结果
        """
        if not text or not text.strip():
            text = "(未识别到任何文本内容)"
            
        self.log_to_terminal(f"OCR 识别内容: {text[:100]}...")
        
        ocr_html = (
            f"<div style='background-color: rgba(0, 80, 80, 150); color: #00ffcc; "
            f"border-left: 5px solid #00ffcc; padding: 12px; margin: 8px; border-radius: 4px;'>"
            f"<b style='color:#00ffff;'>🔍 屏幕文字提取结果:</b><br>"
            f"<div style='background-color: #1e1e1e; color: #ffffff; border: 1px solid #444; "
            f"padding: 10px; margin-top: 8px; font-family: Consolas; font-size: 14px;'>{text}</div>"
            f"</div>"
        )
        self.main_window.chat_display.append(ocr_html)

    def start_vision_capture_with_prompt(self):
        """
        全屏视觉分析 (带用户指令)
        """
        if not self.main_window.check_vision_capability(): return
        
        prompt, ok = QInputDialog.getText(
            self.main_window, "视觉问答", 
            "想让 Una 帮你分析什么？", 
            QLineEdit.Normal, "总结这张屏幕截图"
        )
        
        if ok and prompt:
            self.log_to_terminal(f"触发 AI 视觉分析: {prompt}")
            self.main_window.pending_vision_prompt = prompt
            # 直接调用主界面的全屏处理流程
            self.main_window.action_full_screen()