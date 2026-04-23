import asyncio
import json
import websockets
import threading
import os
from config.config_loader import cfg

# ====================================================
# [VTS BRIDGE MARKER] - 赛博躯体连接插件
# ====================================================

class VTSBridge:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 8001  # VTS 默认端口
        self.token_path = os.path.join(cfg.base_dir, "config/vts_token.txt")
        self.plugin_name = "Una_V2_Core"
        self.developer = "The_Swarm"
        self.auth_token = self._load_token()
        self.websocket = None

    def _load_token(self):
        """尝试读取持久化 Token"""
        if os.path.exists(self.token_path):
            with open(self.token_path, "r") as f:
                return f.read().strip()
        return None

    def _save_token(self, token):
        """保存鉴权成功的 Token"""
        with open(self.token_path, "w") as f:
            f.write(token)
        self.auth_token = token

    def set_mouth_open(self, value):
        """外部调用的同步接口 (value: 0.0 - 1.0)"""
        if self.websocket:
            asyncio.run_coroutine_threadsafe(self.send_parameter("MouthOpen", value), asyncio.get_event_loop())

    async def _send_audio_amplitude(self, amplitude):
        """发送音量振幅给 VTS 实现口型同步"""
        if not self.is_connected: return
        # 这里是 VTS 标准 API 逻辑（简化版）
        pass

    def start_bridge(self):
        """后台启动 VTS 监听"""
        # 实际开发中，这里通常通过插件如 VTS-Pygmalion 直接挂载
        # 这里预留接口，防止 run_una 导入报错
        print("[VTS] 联动插件已就绪")

    async def connect_and_auth(self):
        """
        [鉴权逻辑核心] 
        处理：握手 -> 获取Token(若无) -> 鉴权 -> 激活
        """
        uri = f"ws://{self.host}:{self.port}"
        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                
                # 1. 插件认证请求
                auth_req = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "UnaAuth",
                    "messageType": "AuthenticationTokenRequest",
                    "data": {
                        "pluginName": self.plugin_name,
                        "pluginDeveloper": self.developer
                    }
                }

                # 如果没有 token，去 VTS 申请
                if not self.auth_token:
                    await websocket.send(json.dumps(auth_req))
                    response = await websocket.recv()
                    data = json.loads(response)
                    # 此时 VTS 会弹出确认框，你需要点击“允许”
                    new_token = data['data']['authenticationToken']
                    self._save_token(new_token)
                    print(f"[VTS] 新 Token 已存入: {self.token_path}")

                # 2. 使用 Token 进行身份验证
                login_req = {
                    "apiName": "VTubeStudioPublicAPI",
                    "apiVersion": "1.0",
                    "requestID": "UnaLogin",
                    "messageType": "AuthenticationRequest",
                    "data": {
                        "pluginName": self.plugin_name,
                        "pluginDeveloper": self.developer,
                        "authenticationToken": self.auth_token
                    }
                }
                await websocket.send(json.dumps(login_req))
                login_res = await websocket.recv()
                print(f"[VTS] 鉴权响应: {login_res}")

        except Exception as e:
            print(f"[!] VTS 连接失败 (检查 VTS 是否开启 API): {e}")

    async def send_parameter(self, param_name, value):
        """发送 Live2D 参数驱动模型"""
        if not self.websocket: return
        
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "UnaParam",
            "messageType": "InjectParameterDataRequest",
            "data": {
                "faceFound": False,
                "mode": "set",
                "parameterValues": [
                    {"id": param_name, "value": value}
                ]
            }
        }
        await self.websocket.send(json.dumps(req))

    

    def start_connection(self):
        """在新线程中启动，防止卡死 UI"""
        threading.Thread(target=lambda: asyncio.run(self.connect_and_auth()), daemon=True).start()

# 实例化
vts_sys = VTSBridge()