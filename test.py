import mss
import mss.tools

# with mss.mss() as sct:
#     # 强制获取主显示器
#     monitor = sct.monitors[1] 
    
#     # 捕获画面
#     sct_img = sct.shot(output="test.png")
    
#     # 打印捕获的信息，看是否抓取到了具体宽高
#     print(f"Captured: {monitor}")
from PIL import ImageGrab
img = ImageGrab.grab()
img.save("pil_test.png")