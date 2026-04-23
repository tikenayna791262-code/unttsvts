import sys
import os
import ctypes
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QInputDialog, QMessageBox, QTextEdit, QLineEdit, 
                             QLabel, QHBoxLayout, QDialog, QFormLayout, QDialogButtonBox,
                             QFileDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QFont, QFontDatabase
from PIL import ImageGrab
from core.memory_manager import memory_sys




def resource_path(relative_path):
    """ 获取资源绝对路径，兼容打包后的环境 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

try:
    from plugins.tg_bot import init_tg_bot
    TG_AVAILABLE = True
except ImportError:
    TG_AVAILABLE = False
# 解决 Windows DPI 缩放导致的截图偏移问题
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1) 
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# --- 核心模块导入 ---
from config.config_loader import cfg
from core.ai_engine import ai_core
from core.chat_manager import chat_logger
from plugins.tts_engine import tts_sys
from core.vision_processor import vision_manager

# [VTS HOOK]
try:
    from plugins.vts_bridge import vts_sys
    VTS_AVAILABLE = True
except ImportError:
    VTS_AVAILABLE = False

# [OCR 管理器 - 仅保留非界面引用逻辑]
try:
    from core.ocr_manager import OcrManager
except ImportError:
    OcrManager = None

# ==========================================
# 1. 配置对话框 (完整恢复所有字段)
# ==========================================
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Una 配置重构中心")
        self.setFixedWidth(450)
        self.layout = QFormLayout(self)
        
        
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; color: #00ffcc; font-family: '微软雅黑'; }
            QLabel { color: #00ffcc; font-weight: bold; font-size: 14px; }
            QLineEdit { background-color: #2a2a2a; color: #fff; border: 1px solid #00ffcc; padding: 6px; border-radius: 3px; }
            QPushButton { background-color: #333; color: #00ffcc; border: 1px solid #00ffcc; min-width: 80px; padding: 5px; }
            QPushButton:hover { background-color: #00ffcc; color: #000; }
        """)

        self.inputs = {}
        
        # 字段 1: 用户名称
        self.inputs['user_name'] = QLineEdit(cfg.get('user_name', '蜂群'))
        self.layout.addRow("用户名称:", self.inputs['user_name'])
        
        # 字段 2: AI模型名称
        self.inputs['model'] = QLineEdit(cfg.get('ai_provider.model', ''))
        self.layout.addRow("AI模型名称:", self.inputs['model'])
        
        # 字段 3: API Key
        self.inputs['api_key'] = QLineEdit(cfg.get('ai_provider.api_key', ''))
        self.inputs['api_key'].setEchoMode(QLineEdit.Password)
        self.layout.addRow("API Key:", self.inputs['api_key'])
        
        # 字段 4: Base URL
        self.inputs['base_url'] = QLineEdit(cfg.get('ai_provider.base_url', ''))
        self.layout.addRow("API URL (含端口):", self.inputs['base_url'])

        # 字段 5: 网络代理
        self.inputs['proxy'] = QLineEdit(cfg.get('ai_provider.proxy', ''))
        self.inputs['proxy'].setPlaceholderText("例如: http://127.0.0.1:7890")
        self.layout.addRow("网络代理:", self.inputs['proxy'])
        
        # 字段 6: TG Token
        self.inputs['tg_token'] = QLineEdit(cfg.get('tg_bot.token', ''))
        self.layout.addRow("TG Token:", self.inputs['tg_token'])
        
        # 字段 7: 最大 Token 数
        self.inputs['max_tokens'] = QLineEdit(str(cfg.get('ai_provider.max_tokens', 2048)))
        self.layout.addRow("最大 Token 数:", self.inputs['max_tokens'])

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)

    def get_values(self):
        return {k: v.text() for k, v in self.inputs.items()}

# ==========================================
# 2. 主窗口类
# ==========================================
class UnaMain(QMainWindow):
    def __init__(self):
        super().__init__()
        # 基础状态
        self.is_mini = False
        self.tts_active = True 
        self.m_drag = False
        self.monitor_active = False # 快速传输开关
        self.user_name = cfg.get('user_name', '蜂群')
        self.pending_vision_prompt = ""
        self.chat_counter = 0
        
        # 清理由于 TTS 生成的大量废弃 MP3 垃圾文件
        self.clean_temp_audio()

        # 初始化 OCR 分发器
        self.ocr_manager = OcrManager(self) if OcrManager else None

        self.init_ui()

        if VTS_AVAILABLE:
            vts_sys.start_connection()
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # 启动日志标记
        self.log_to_terminal("[系统] 蜂群核心界面已初始化完毕。")

    def clean_temp_audio(self):
        """开机清理临时音频文件夹，防止垃圾挤占空间"""
        temp_dirs = [os.path.join(os.getcwd(), "temp"), os.path.join(os.getcwd(), "temp_audio")]
        for t_dir in temp_dirs:
            if os.path.exists(t_dir):
                for file in os.listdir(t_dir):
                    if file.endswith('.mp3') or file.endswith('.wav'):
                        try:
                            os.remove(os.path.join(t_dir, file))
                        except:
                            pass

    def log_to_terminal(self, message):
        """专门负责输出到终端以及确保 Log 更新"""
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{time_str}] {message}"
        
        # 1. 终端强制刷新输出
        print(formatted_msg, flush=True) 
        
        # 2. 修复写入日志失败
        try:
            from core.chat_manager import chat_logger
            # 检查 chat_logger 到底有哪些方法，防止报错
            if hasattr(chat_logger, 'info'):
                chat_logger.info(message)
            elif hasattr(chat_logger, 'log'):
                chat_logger.log(message)
            else:
                # 如果是自定义类且没写方法，直接手动追加到文件，确保万无一失
                log_path = os.path.join(os.getcwd(), "logs", "chat.log")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
        except Exception as e:
            print(f"写入日志文件时发生最终异常: {e}")

    def export_logs(self):
        """将日志文件复制到用户指定位置"""
        try:
            log_source = os.path.join(os.getcwd(), "logs", "chat.log") # 请确认你的 log 路径
            if not os.path.exists(log_source):
                QMessageBox.warning(self, "导出失败", "当前还没有产生日志文件。")
                return
            
            save_path, _ = QFileDialog.getSaveFileName(self, "导出日志", f"Una_Log_{datetime.now().strftime('%Y%m%d')}.txt", "Text Files (*.txt);;Log Files (*.log)")
            if save_path:
                import shutil
                shutil.copy(log_source, save_path)
                QMessageBox.information(self, "导出成功", f"日志已保存至:\n{save_path}")
                self.log_to_terminal(f"用户导出了日志至: {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出过程中发生异常: {e}")

    def clear_logs(self):
        """清空当前的日志内容"""
        reply = QMessageBox.question(self, "确认清空", "确定要删除所有历史日志记录吗？此操作不可撤销。", 
                                     QMessageBox.YES | QMessageBox.NO)
        if reply == QMessageBox.YES:
            try:
                log_path = os.path.join(os.getcwd(), "logs", "chat.log")
                if os.path.exists(log_path):
                    with open(log_path, 'w', encoding='utf-8') as f:
                        f.write(f"--- 日志已于 {datetime.now()} 被用户清空 ---\n")
                self.chat_display.clear()
                self.chat_display.append("<i style='color:#777;'>[系统] 历史记录及日志已清空。</i>")
                self.log_to_terminal("用户清空了所有日志记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空失败: {e}")

    # === 在 UnaMain 类中添加这个函数体 ===
    def generate_unique_filename(self):
        """生成绝对唯一的图片路径，防止覆盖"""
        from datetime import datetime
        import os
        
        # 使用 %f 包含微秒，确保每秒点击多次也不会文件名冲突
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"vision_{timestamp}.png"
        
        # 确保 temp 文件夹存在
        temp_dir = os.path.join(os.getcwd(), "temp")
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir)
            except Exception as e:
                print(f"创建目录失败: {e}")
                
        return os.path.join(temp_dir, filename)

    def init_ui(self):
        self.setWindowTitle(f"Una V2 - {self.user_name}")
        self.resize(500, 750) 
        self.setWindowOpacity(cfg.get('ui.opacity', 0.9))
        
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.main_layout = QVBoxLayout(self.main_container)

        # 顶部工具栏
        top_bar = QHBoxLayout()
        self.clock_label = QLabel()
        self.clock_label.setObjectName("ClockLabel") 
        self.status_light = QLabel("● 系统就绪")
        self.status_light.setStyleSheet("color: #008855; font-size: 14px; font-weight: bold;") 

        self.btn_mini = QPushButton("Una")
        self.btn_mini.setFixedWidth(50)
        self.btn_mini.clicked.connect(self.toggle_mini_mode)
        # 在原有 row2 中增加两个小按钮，或者放在配置按钮旁边
        self.btn_export = QPushButton("📤 导出日志")
        self.btn_export.clicked.connect(self.export_logs)
        self.btn_clear = QPushButton("🗑️ 清空日志")
        self.btn_clear.clicked.connect(self.clear_logs)
        
        
        top_bar.addWidget(self.clock_label)
        top_bar.addStretch()
        top_bar.addWidget(self.status_light)
        top_bar.addWidget(self.btn_mini)
        self.main_layout.addLayout(top_bar)

        # 核心内容区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.main_layout.addWidget(self.chat_display)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("在此输入指令...")
        self.input_field.returnPressed.connect(self.send_message)
        self.main_layout.addWidget(self.input_field)

        # --- 视觉功能与控制按钮组 ---
        btn_box = QVBoxLayout()
        
        # Row 1
        row1 = QHBoxLayout()
        self.btn_full_cap = QPushButton("📸 全屏截图")
        self.btn_full_cap.clicked.connect(self.action_full_screen)
        
        self.btn_fast_mode = QPushButton("⚡ 快速传输: OFF")
        self.btn_fast_mode.clicked.connect(self.toggle_fast_transfer)
        
        row1.addWidget(self.btn_full_cap)
        row1.addWidget(self.btn_fast_mode)

        # Row 2
        row2 = QHBoxLayout()
        self.btn_paste = QPushButton("📋 粘贴/上传")
        self.btn_paste.clicked.connect(self.action_image_input)
        
        self.btn_tts = QPushButton("🔊 语音: ON")
        self.btn_tts.clicked.connect(self.toggle_tts)
        self.btn_mem = QPushButton("🧠 查看记忆")
        self.btn_mem.clicked.connect(self.show_memory_viewer)
        # 放到 row2 或者你喜欢的位置
        
        
        self.btn_cfg = QPushButton("⚙️ 配置")
        self.btn_cfg.clicked.connect(self.open_settings)
        # 建议放在 row2
        row2.addWidget(self.btn_export)
        row2.addWidget(self.btn_clear)
        row2.addWidget(self.btn_paste)
        row2.addWidget(self.btn_tts)
        row2.addWidget(self.btn_cfg)
        row2.addWidget(self.btn_mem)
        
        btn_box.addLayout(row1)
        btn_box.addLayout(row2)
        self.main_layout.addLayout(btn_box)

        self.update_style()

    # --- 逻辑 A: 模型自检 ---
    def check_vision_capability(self):
        if not self.monitor_active: return True 
        
        current_model = cfg.get('ai_provider.model', '').lower()
        vision_keywords = ['vision', 'gpt-4o', 'claude-3', 'gemini-1.5', 'vl']
        if not any(kw in current_model for kw in vision_keywords):
            rant = "喂！快速传输开着呢，但你这模型没‘眼睛’啊！换个 Vision 模型！"
            self.chat_display.append(f"<b style='color:red;'>[自检拦截]</b> <i style='color:#00ffcc;'>Una: {rant}</i>")
            self.log_to_terminal(f"拦截操作: 当前模型 {current_model} 不支持视觉。")
            if self.tts_active: tts_sys.speak(rant)
            return False
        return True

    # --- 逻辑 B: 全屏截图逻辑 ---
    def action_full_screen(self):
        if not self.check_vision_capability(): return
        
        self.setWindowOpacity(0)
        QApplication.processEvents()
        time.sleep(0.3)
        
        try:
            file_path = self.generate_unique_filename() 
            
            screenshot = ImageGrab.grab()
            screenshot.save(file_path)
            
            self.setWindowOpacity(cfg.get('ui.opacity', 0.9))
            
            prompt, ok = QInputDialog.getText(self, "视觉指令", "添加提示词 (留空直接处理):", QLineEdit.Normal, "")
            self.pending_vision_prompt = prompt if (ok and prompt) else "描述图片内容"
            self.log_to_terminal(f"全屏截图保存成功: {file_path}")
            self.process_local_image_to_una(file_path)
        except Exception as e:
            self.chat_display.append(f"<b style='color:red;'>[截图失败]: {str(e)}</b>")
            self.log_to_terminal(f"[错误] 截图异常: {e}")
            self.setWindowOpacity(cfg.get('ui.opacity', 0.9))

    # --- 逻辑 C: 快速传输开关 ---
    def toggle_fast_transfer(self):
        self.monitor_active = not self.monitor_active
        state = "ON" if self.monitor_active else "OFF"
        self.btn_fast_mode.setText(f"⚡ 快速传输: {state}")
        if self.monitor_active:
            self.check_vision_capability()
            self.chat_display.append("<i style='color:#777;'>[系统] 快速传输已开启，后续所有图片操作将强制触发 Vision 自检。</i>")
            self.log_to_terminal("状态变更: 快速传输模式已开启")

    # --- 逻辑 D: 粘贴/上传 ---
    def action_image_input(self):
        if not self.check_vision_capability(): return
        
        msg = QMessageBox()
        msg.setWindowTitle("图片来源")
        msg.setText("请选择图片输入方式：")
        btn_paste = msg.addButton("从剪贴板粘贴", QMessageBox.ActionRole)
        btn_file = msg.addButton("从本地上传", QMessageBox.ActionRole)
        msg.exec_()

        file_path = ""
        if msg.clickedButton() == btn_paste:
            clipboard = QApplication.clipboard()
            if clipboard.mimeData().hasImage():
                file_path = vision_manager.generate_filename()
                clipboard.image().save(file_path)
                self.log_to_terminal(f"读取剪贴板图片成功: {file_path}")
            else:
                self.chat_display.append("<i style='color:#777;'>[系统] 剪贴板中没有图片。</i>")
                return
        elif msg.clickedButton() == btn_file:
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path: 
                file_path = path
                self.log_to_terminal(f"选中本地上传图片: {file_path}")
            else: return

        prompt, ok = QInputDialog.getText(self, "视觉分析", "请输入提示词:", QLineEdit.Normal, "识别此图片")
        self.pending_vision_prompt = prompt if (ok and prompt) else "直接处理"
        self.process_local_image_to_una(file_path)

    # --- 逻辑 E: 统一喂回 AI ---
    def process_local_image_to_una(self, file_path):
        self.status_light.setText("● 正在扫描...")
        self.status_light.setStyleSheet("color: #ffaa00; font-weight: bold;")
        QApplication.processEvents()
        
        try:
            detected_text = vision_manager.local_ocr(file_path)
            final_prompt = vision_manager.build_una_prompt(self.pending_vision_prompt, detected_text)
            
            self.chat_display.append(f"<b>{self.user_name}:</b> [视觉] {self.pending_vision_prompt}")
            self.log_to_terminal(f"{self.user_name} 触发视觉分析 (文件: {os.path.basename(file_path)})")
            
            reply = ai_core.chat(final_prompt)
            self.chat_display.append(f"<b style='color:#00ffcc;'>Una:</b> {reply}")
            self.log_to_terminal(f"Una 回复: {reply}")
            
            if self.tts_active: tts_sys.speak(reply)
        except Exception as e:
            self.chat_display.append(f"<b style='color:red;'>[视觉处理错误]: {str(e)}</b>")
            self.log_to_terminal(f"[错误] 处理异常: {str(e)}")
        finally:
            self.status_light.setText("● 系统就绪")
            self.status_light.setStyleSheet("color: #008855; font-weight: bold;")

    # --- 逻辑 F: 语音控制加强 (新增打断停止) ---
    def toggle_tts(self):
        self.tts_active = not self.tts_active
        self.btn_tts.setText("语音: ON" if self.tts_active else "语音: OFF")
        self.log_to_terminal(f"语音状态已切换: {self.tts_active}")
        
        if not self.tts_active:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload() # 卸载当前音频流
                
                # 如果你的 tts_sys 有队列管理，也在这里清空
                if hasattr(tts_sys, 'stop'):
                    tts_sys.stop() 
                    
                self.log_to_terminal("已彻底截断并卸载所有音频任务。")
            except Exception as e:
                print(f"TTS 停止异常: {e}")

    def open_settings(self):
        dialog = ConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            vals = dialog.get_values()
            cfg.set('user_name', vals['user_name'])
            cfg.set('ai_provider.model', vals['model'])
            cfg.set('ai_provider.api_key', vals['api_key'])
            cfg.set('ai_provider.base_url', vals['base_url'])
            cfg.set('ai_provider.proxy', vals['proxy'])
            cfg.set('tg_bot.token', vals['tg_token'])
            cfg.set('ai_provider.max_tokens', int(vals['max_tokens']))
            
            self.user_name = vals['user_name']
            self.setWindowTitle(f"Una V2 - {self.user_name}")
            self.chat_display.append("<b style='color:#00ffcc;'>[系统] 核心配置已覆盖保存并生效。</b>")
            self.log_to_terminal("用户重载了系统配置")

    # --- UI 逻辑辅助 ---
    def toggle_mini_mode(self):
        if not self.is_mini:
            self.setFixedSize(60, 60)
            self.btn_mini.setText("U")
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.is_mini = True
        else:
            self.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.setFixedSize(500, 750)
            self.btn_mini.setText("Una")
            self.is_mini = False
        self.show()

    def update_time(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def update_style(self):
        # 完整找回背景图加载逻辑
        def update_style(self):
    # 使用补丁函数获取路径
            bg_path = resource_path("ui/resources/bg.jpg").replace("\\", "/")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(current_dir, "ui", "resources", "bg.jpg").replace("\\", "/")
        
        style = f"""
            QMainWindow {{ 
                background-image: url('{bg_path}'); 
                background-position: center; 
                background-repeat: no-repeat; 
                background-color: #1a1a1a; 
            }}
            QTextEdit {{ background-color: rgba(0, 0, 0, 160); color: #00ffcc; border: 2px solid #00ffcc; font-size: 16px; padding: 10px; font-family: 'Consolas', '微软雅黑'; }}
            QLineEdit {{ background-color: rgba(26, 26, 26, 220); color: white; border: 2px solid #00ffcc; padding: 10px; border-radius: 5px; font-size: 16px; }}
            QPushButton {{ background-color: rgba(26, 26, 26, 210); color: #00ffcc; border: 1px solid #00ffcc; padding: 8px; font-weight: bold; font-size: 14px; min-height: 35px; }}
            QPushButton:hover {{ background-color: #00ffcc; color: black; }}
            QLabel#ClockLabel {{ color: #ffffff; font-size: 26px; font-weight: 900; background-color: rgba(0, 255, 204, 30); padding: 5px; border-radius: 5px; }}
        """
        self.setStyleSheet(style)


    def show_memory_viewer(self):
        """弹出窗口显示当前存下的所有记忆内容"""
        memories = memory_sys.get_all_memories()
        if not memories:
            QMessageBox.information(self, "记忆库", "当前还没有任何记忆记录。")
            return
            
        # 简单拼接字符串展示，也可以做成高级列表
        display_text = ""
        for m in memories:
            display_text += f"[{m[0]}] {m[1].upper()}: {m[2]}\n"
            
        msg_box = QDialog(self)
        msg_box.setWindowTitle("Una 记忆提取器")
        msg_box.resize(600, 400)
        layout = QVBoxLayout(msg_box)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(display_text)
        layout.addWidget(text_edit)
        msg_box.exec_()

    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)

    def mouseReleaseEvent(self, event):
        self.m_drag = False

    def mouseDoubleClickEvent(self, event):
        if self.is_mini: self.toggle_mini_mode()

    def auto_archive_memory(self):
        """自动总结逻辑"""
        try:
            from core.memory_manager import memory_sys
            self.log_to_terminal("正在执行记忆归档...")
            all_mem = memory_sys.get_all_memories()
            if not all_mem: return
            
            context_text = "\n".join([f"{m[1]}: {m[2]}" for m in all_mem])
            prompt = f"请总结以下对话的核心信息，压缩成300字以内的核心档案：\n\n{context_text}"
            
            summary = ai_core.chat(prompt)
            if memory_sys.wipe_and_summarize(summary):
                self.chat_display.append("<b style='color:yellow;'>[记忆系统] 对话已自动压缩归档。</b>")
        except Exception as e:
            self.log_to_terminal(f"总结失败: {e}")

    def send_message(self, source="local"):
        """
        发送消息逻辑
        source: "local" 代表本地输入框，"tg" 代表来自 Telegram 远程
        """
        txt = self.input_field.text().strip()
        if not txt: return
        self.input_field.clear()
        
        # 1. 确定用户名称显示
        display_name = self.user_name if source == "local" else "TG远程用户"
        
        # 2. UI 展示与本地日志
        self.chat_display.append(f"<b>{display_name}:</b> {txt}")
        self.log_to_terminal(f"[{display_name}] {txt}")
        
        # 3. 存入长期记忆库 (统一标记来源)
        memory_sys.save_chat("user", txt, tags=source)
        
        # 4. 获取 AI 回复
        try:
            reply = ai_core.chat(txt)
        except Exception as e:
            reply = f"抱歉，我出错了: {str(e)}"
            self.log_to_terminal(f"AI 响应错误: {e}")

        # 5. 展示 AI 回复并存入记忆
        self.chat_display.append(f"<b style='color:#00ffcc;'>Una:</b> {reply}")
        self.log_to_terminal(f"[Una] {reply}")
        memory_sys.save_chat("una", reply, tags=source)
        
        # 6. 如果是语音模式则播放
        if self.tts_active:
            from plugins.tts_engine import tts_sys
            tts_sys.speak(reply)

        # 7. 记忆库自动总结计数
        self.chat_counter += 1
        if self.chat_counter >= 50:
            # 这里的 auto_archive_memory 需要在 UnaMain 类中定义
            self.auto_archive_memory()
            self.chat_counter = 0

        txt = self.input_field.text().strip()
        if not txt: return
        self.input_field.clear()
        
        # UI 展示
        display_name = self.user_name if source == "local" else "TG远程用户"
        self.chat_display.append(f"<b>{display_name}:</b> {txt}")
        self.log_to_terminal(f"[{display_name}] {txt}")

        # --- 重要性筛选逻辑开始 ---
        # 1. 先进行简单的关键词预热判断（避免每句话都调 AI 浪费流量）
        if memory_sys.is_important(txt):
            # 2. 只有通过预热的，才让 AI 深度判断是否存入记忆
            check_prompt = f"判断以下内容是否包含用户的长期偏好、重要事实或需要记住的指令。如果是，请直接输出内容；如果只是无意义的闲聊，请输出'SKIP'。内容：\n{txt}"
            try:
                # 这里的 chat 可以使用更便宜的模型或者快速判断
                decision = ai_core.chat(check_prompt) 
                if "SKIP" not in decision.upper():
                    memory_sys.save_chat("user", txt, tags=f"{source}_important")
                    self.log_to_terminal("[记忆系统] 识别到重要信息，已录入库。")
            except:
                pass # 报错则不存，保证稳定性
        # --- 重要性筛选逻辑结束 ---

        # 获取 AI 回复
        reply = ai_core.chat(txt)
        self.chat_display.append(f"<b style='color:#00ffcc;'>Una:</b> {reply}")
        self.log_to_terminal(f"[Una] {reply}")
        
        # AI 的回复通常不建议全部存入长期记忆，除非你觉得 Una 的性格设定需要进化
        # 如果要存，也可以加同样的判断

        if self.tts_active:
            from plugins.tts_engine import tts_sys
            tts_sys.speak(reply)

        # 计数器依然累加（用于触发阶段性总结）
        self.chat_counter += 1
        if self.chat_counter >= 50:
            self.auto_archive_memory()
            self.chat_counter = 0

    # 启动 TG Bot 远程连接
        if TG_AVAILABLE:
            self.tg_bot = init_tg_bot(self)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UnaMain()
    window.show()
    sys.exit(app.exec_())