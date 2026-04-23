import os
import telebot
from datetime import datetime
from threading import Thread

# 导入配置加载器
from config.config_loader import cfg

class UnaTelegramBot:
    def __init__(self, main_window):
        self.main_window = main_window
        self.token = cfg.get('tg_bot.token', '')
        self.bot = None
        self.is_running = False
        
        if self.token:
            try:
                self.bot = telebot.TeleBot(self.token)
                self.setup_handlers()
            except Exception as e:
                print(f"[TG Bot] 初始化失败: {e}")

    def setup_handlers(self):
        """定义指令处理器"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            help_text = (
                "🤖 Una 远程接入成功！\n\n"
                "可用指令：\n"
                "/ss - 立即截取电脑全屏并回传\n"
                "/info - 获取电脑当前状态\n"
                "/msg [内容] - 在电脑端弹出并播报文字"
            )
            self.bot.reply_to(message, help_text)

        @self.bot.message_handler(commands=['ss'])
        def remote_screenshot(message):
            """远程截图指令"""
            self.main_window.log_to_terminal(f"收到 TG 远程截图请求 (User: {message.from_user.id})")
            try:
                # 1. 触发主窗口生成唯一文件名
                file_path = self.main_window.generate_unique_filename()
                
                # 2. 这里的截图逻辑需要直接调用 PIL (因为 TG 运行在后台线程)
                from PIL import ImageGrab
                # 截图前不需要隐藏窗口（因为是远程静默操作），如果需要隐藏可调用主窗口逻辑
                screenshot = ImageGrab.grab()
                screenshot.save(file_path)
                
                # 3. 发送回 TG
                with open(file_path, 'rb') as photo:
                    self.bot.send_photo(message.chat.id, photo, caption=f"📸 截图时间: {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self.bot.reply_to(message, f"❌ 截图失败: {str(e)}")

        @self.bot.message_handler(commands=['msg'])
        def remote_msg(message):
            """远程播报文字"""
            text = message.text.replace('/msg', '').strip()
            if text:
                # 触发主窗口 UI 更新和 TTS
                self.main_window.chat_display.append(f"<b style='color:#f1c40f;'>[TG 远程]:</b> {text}")
                if self.main_window.tts_active:
                    from plugins.tts_engine import tts_sys
                    tts_sys.speak(text)
                self.bot.reply_to(message, "✅ 指令已在电脑端执行")
            else:
                self.bot.reply_to(message, "请输入内容，例如: /msg 吃饭了")

    def _run_polling(self):
        """线程死循环监听"""
        try:
            self.log("TG Bot 服务已启动...")
            self.bot.infinity_polling()
        except Exception as e:
            self.log(f"TG Bot 异常中断: {e}")

    def start(self):
        """在独立线程中启动"""
        if self.bot and not self.is_running:
            self.thread = Thread(target=self._run_polling, daemon=True)
            self.thread.start()
            self.is_running = True
        elif not self.bot:
            self.log("错误: 未配置 TG Token，无法启动 Bot")

    def log(self, text):
        """同步显示到主界面"""
        if self.main_window:
            self.main_window.log_to_terminal(text)

    def log(self, text):
        """同步显示到主界面，并写入本地日志文件"""
        if self.main_window:
            # 1. 调用主窗口的统一日志接口 (这会自动处理打印、文件写入和异常兼容)
            self.main_window.log_to_terminal(f"[TG远程] {text}")

    

    


# 实例化入口
tg_sys = None 
def init_tg_bot(main_window):
    global tg_sys
    tg_sys = UnaTelegramBot(main_window)
    tg_sys.start()
    return tg_sys


