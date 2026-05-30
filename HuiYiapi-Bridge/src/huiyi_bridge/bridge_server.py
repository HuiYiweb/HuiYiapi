#!/usr/bin/env python3
"""
HuiYiapi Bridge Server — 云服务器桥接器
========================================
单文件实现，可直接运行。功能：
1. WebSocket 服务端 — 与多台 Android 手机保持长连接
2. OneBot v11 反向 WebSocket 客户端 — 每台手机一个实例，接入 AstrBot
3. MCP Server (Stdio) — 暴露完整手机操控工具集，集成 mcp_for_android 全部 UI 自动化能力
4. 语音/视频通话处理控制
5. ADB 集成（可选）

启动方式：
    python bridge_server.py
    
    或安装依赖后：
    pip install websockets aiohttp mcp pyyaml
    python bridge_server.py --config config.yaml
"""

import asyncio
import json
import time
import uuid
import logging
import hashlib
import hmac
import os
import sys
import signal
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional, Any, List, Callable, Awaitable
from dataclasses import dataclass, field, asdict
from enum import Enum

# ============================================================
# 第三方库导入（带优雅降级）
# ============================================================

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    from websockets.client import WebSocketClientProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    print("[WARN] websockets 未安装，请执行: pip install websockets")

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("[WARN] mcp 未安装，MCP 功能不可用。执行: pip install mcp")

# ADB 相关（可选）
try:
    import subprocess
    HAS_ADB = False  # 运行时检测
except ImportError:
    HAS_ADB = False

# ============================================================
# 配置
# ============================================================

@dataclass
class BridgeConfig:
    """桥接器全局配置"""
    # WebSocket 服务器（面向手机）
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    
    # OneBot 反向 WS 连接（面向 AstrBot）
    onebot_url: str = "ws://127.0.0.1:6700/"
    onebot_access_token: str = ""
    
    # MCP 配置
    mcp_enabled: bool = True
    mcp_name: str = "HuiYiapi Bridge"
    
    # ADB 配置
    adb_enabled: bool = False
    adb_path: str = "adb"
    
    # 超时配置
    tool_timeout: int = 30       # MCP 工具超时(秒)
    heartbeat_interval: int = 30  # 心跳间隔(秒)
    reconnect_delay: int = 3     # 重连延迟(秒)
    max_reconnect_delay: int = 30  # 最大重连延迟
    
    # 日志
    log_level: str = "INFO"
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BridgeConfig":
        return cls(
            ws_host=data.get("ws_host", "0.0.0.0"),
            ws_port=data.get("ws_port", 8765),
            onebot_url=data.get("onebot_url", "ws://127.0.0.1:6700/"),
            onebot_access_token=data.get("onebot_access_token", ""),
            mcp_enabled=data.get("mcp_enabled", True),
            tool_timeout=data.get("tool_timeout", 30),
            heartbeat_interval=data.get("heartbeat_interval", 30),
            log_level=data.get("log_level", "INFO"),
        )


# ============================================================
# 日志
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("huiyi_bridge")


# ============================================================
# 数据模型
# ============================================================

class MessageType(str, Enum):
    """WebSocket 消息类型"""
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    INCOMING_MESSAGE = "incoming"
    SEND_RESULT = "send_result"
    TOOL_RESULT = "tool_result"
    VOICE_TEXT = "voice_text"
    CALL_EVENT = "call_event"
    DEVICE_STATE = "device_state"
    UI_TREE = "ui_tree"
    ERROR = "error"


@dataclass
class DeviceSession:
    """单个设备会话"""
    device_id: str
    device_name: str = ""
    ws: Optional[Any] = None               # 手机 WebSocket 连接
    onebot_ws: Optional[Any] = None        # OneBot 客户端连接
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: float = field(default_factory=time.time)
    is_online: bool = False
    onebot_connected: bool = False
    send_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    pending_tools: Dict[str, asyncio.Event] = field(default_factory=dict)
    tool_results: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 主桥接器类
# ============================================================

class HuiYiBridgeServer:
    """
    HuiYi 云桥接器主类
    
    三合一：
    - WebSocket 服务端（面向 Android 手机）
    - OneBot v11 客户端（面向 AstrBot）
    - MCP 工具服务器（面向 AI Agent）
    """
    
    def __init__(self, config: BridgeConfig = None):
        self.config = config or BridgeConfig()
        
        # 设备会话管理
        self.devices: Dict[str, DeviceSession] = {}
        
        # OneBot 客户端管理（device_id -> WebSocket）
        self.onebot_clients: Dict[str, WebSocketClientProtocol] = {}
        
        # MCP 工具集
        self._mcp_tools: List[Tool] = []
        self._mcp_handlers: Dict[str, Callable] = {}
        
        # 运行状态
        self._running = False
        self._ws_server = None
        
        # 检测 ADB 可用性
        self._adb_available = self._check_adb()
        
        # 注册所有 MCP 工具
        self._register_all_mcp_tools()
        
        logger.info(f"🚀 HuiYi Bridge Server 初始化完成")
        logger.info(f"   WebSocket: ws://{self.config.ws_host}:{self.config.ws_port}")
        logger.info(f"   OneBot: {self.config.onebot_url}")
        logger.info(f"   MCP: {'✅ 已启用' if self.config.mcp_enabled else '❌ 已禁用'}")
        logger.info(f"   ADB: {'✅ 可用' if self._adb_available else '❌ 不可用'}")
    
    # ============================================================
    # 生命周期
    # ============================================================
    
    async def start(self):
        """启动桥接器（WebSocket 服务器 + MCP）"""
        self._running = True
        
        # 启动 WebSocket 服务器
        asyncio.create_task(self._run_ws_server())
        
        # 启动 MCP Server（如果可用）
        if self.config.mcp_enabled and HAS_MCP:
            asyncio.create_task(self._run_mcp_server())
        
        logger.info("✅ HuiYi Bridge Server 已启动，等待连接...")
        
        # 保持主循环
        while self._running:
            await asyncio.sleep(1)
    
    async def shutdown(self):
        """优雅关闭"""
        logger.info("🛑 正在关闭 HuiYi Bridge Server...")
        self._running = False
        
        # 关闭所有设备连接
        for device in self.devices.values():
            if device.ws:
                try:
                    await device.ws.close()
                except Exception:
                    pass
            if device.onebot_ws:
                try:
                    await device.onebot_ws.close()
                except Exception:
                    pass
        
        logger.info("👋 HuiYi Bridge Server 已关闭")
    
    # ============================================================
    # WebSocket 服务器（Android 手机端）
    # ============================================================
    
    async def _run_ws_server(self):
        """启动 WebSocket 服务器"""
        try:
            self._ws_server = await websockets.serve(
                self._handle_phone_connection,
                self.config.ws_host,
                self.config.ws_port,
                ping_interval=30,
                ping_timeout=10,
                max_size=10 * 1024 * 1024,  # 10MB
            )
            logger.info(f"📡 WebSocket 服务器已启动: ws://{self.config.ws_host}:{self.config.ws_port}")
        except Exception as e:
            logger.error(f"WebSocket 服务器启动失败: {e}")
    
    async def _handle_phone_connection(self, ws: WebSocketServerProtocol, path: str = "/"):
        """
        处理手机 WebSocket 连接。
        手机首次连接需发送注册帧。
        """
        peer = ws.remote_address
        logger.info(f"📱 新连接: {peer}")
        
        device_id = None
        session: Optional[DeviceSession] = None
        
        try:
            async for raw_message in ws:
                try:
                    msg = json.loads(raw_message)
                except json.JSONDecodeError:
                    logger.warning(f"无效 JSON: {raw_message[:100]}")
                    continue
                
                msg_type = msg.get("type", "")
                
                # === 注册 ===
                if msg_type == MessageType.REGISTER:
                    device_id = msg.get("device_id", "")
                    device_name = msg.get("device_name", f"Phone-{device_id[:8]}")
                    
                    if not device_id:
                        await ws.send(json.dumps({"type": "error", "message": "缺少 device_id"}))
                        continue
                    
                    # 创建或复用会话
                    if device_id in self.devices:
                        session = self.devices[device_id]
                        # 更新旧连接的 WS
                        if session.ws:
                            try:
                                await session.ws.close()
                            except Exception:
                                pass
                    else:
                        session = DeviceSession(device_id=device_id, device_name=device_name)
                        self.devices[device_id] = session
                        # 为新设备创建 OneBot 客户端
                        asyncio.create_task(self._onebot_client(device_id))
                    
                    session.ws = ws
                    session.is_online = True
                    session.device_name = device_name
                    session.last_heartbeat = time.time()
                    
                    await ws.send(json.dumps({
                        "type": "register_ack",
                        "device_id": device_id,
                        "status": "ok",
                        "message": f"注册成功: {device_name}"
                    }))
                    
                    logger.info(f"✅ 设备注册: {device_id} ({device_name})")
                
                # === 心跳 ===
                elif msg_type == MessageType.HEARTBEAT:
                    if session:
                        session.last_heartbeat = time.time()
                        await ws.send(json.dumps({"type": "heartbeat_ack"}))
                
                # === 收到手机消息 ===
                elif msg_type == MessageType.INCOMING_MESSAGE:
                    if session:
                        await self._handle_incoming_message(session, msg)
                
                # === 发送结果 ===
                elif msg_type == MessageType.SEND_RESULT:
                    if session:
                        msg_id = msg.get("id", "")
                        if msg_id in session.pending_tools:
                            session.tool_results[msg_id] = msg
                            session.pending_tools[msg_id].set()
                
                # === 工具执行结果 ===
                elif msg_type == MessageType.TOOL_RESULT:
                    if session:
                        tool_id = msg.get("id", "")
                        if tool_id in session.pending_tools:
                            session.tool_results[tool_id] = msg.get("result", msg)
                            session.pending_tools[tool_id].set()
                
                # === 实时语音识别文本 ===
                elif msg_type == MessageType.VOICE_TEXT:
                    if session:
                        await self._handle_voice_text(session, msg)
                
                # === 通话事件 ===
                elif msg_type == MessageType.CALL_EVENT:
                    if session:
                        await self._handle_call_event(session, msg)
                
                # === UI 层级树 ===
                elif msg_type == MessageType.UI_TREE:
                    if session:
                        tool_id = msg.get("id", "")
                        if tool_id in session.pending_tools:
                            session.tool_results[tool_id] = msg.get("tree", msg)
                            session.pending_tools[tool_id].set()
                
                # === 设备状态 ===
                elif msg_type == MessageType.DEVICE_STATE:
                    if session:
                        self._update_device_state(session, msg)
                
                else:
                    logger.debug(f"未知消息类型: {msg_type}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 连接关闭: {peer} (device={device_id})")
        except Exception as e:
            logger.error(f"📱 连接异常: {peer}: {e}")
        finally:
            if session:
                session.is_online = False
                session.ws = None
                logger.info(f"📱 设备离线: {session.device_id}")
    
    # ============================================================
    # OneBot v11 客户端（面向 AstrBot）
    # ============================================================
    
    async def _onebot_client(self, device_id: str):
        """
        为指定设备创建 OneBot v11 反向 WebSocket 客户端。
        连接 AstrBot 的内置 OneBot 服务端。
        """
        session = self.devices.get(device_id)
        if not session:
            return
        
        url = self.config.onebot_url
        token = self.config.onebot_access_token
        
        retry_count = 0
        
        while self._running and device_id in self.devices:
            try:
                # 构建连接头
                headers = {}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                
                async with websockets.connect(url, extra_headers=headers) as ws:
                    session.onebot_ws = ws
                    session.onebot_connected = True
                    self.onebot_clients[device_id] = ws
                    
                    logger.info(f"🔗 OneBot 已连接: device={device_id}, url={url}")
                    
                    # 重置重试计数
                    retry_count = 0
                    
                    # 监听 OneBot 下发的消息
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            await self._handle_onebot_event(device_id, data)
                        except json.JSONDecodeError:
                            logger.warning(f"OneBot 无效 JSON: {raw[:100]}")
                    
            except (websockets.exceptions.ConnectionClosed, OSError, ConnectionRefusedError) as e:
                retry_count += 1
                delay = min(self.config.reconnect_delay * (2 ** (retry_count - 1)), self.config.max_reconnect_delay)
                logger.warning(f"OneBot 连接断开 ({device_id})，{delay}s 后重试 ({retry_count})...")
                
                session.onebot_connected = False
                if device_id in self.onebot_clients:
                    del self.onebot_clients[device_id]
                
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"OneBot 客户端异常 ({device_id}): {e}")
                await asyncio.sleep(self.config.max_reconnect_delay)
    
    async def _handle_onebot_event(self, device_id: str, data: Dict):
        """
        处理来自 AstrBot 的 OneBot 事件（API 调用）。
        主要处理 send_msg 等 API，转发给对应手机。
        """
        session = self.devices.get(device_id)
        if not session or not session.ws:
            return
        
        post_type = data.get("post_type", "")
        
        # OneBot API 响应处理
        if "echo" in data:
            logger.debug(f"OneBot API 响应: echo={data.get('echo')}")
            return
        
        # 处理 send_msg 类 API
        action = data.get("action", "")
        
        if action == "send_msg" or action == "send_private_msg" or action == "send_group_msg":
            message = data.get("params", {}).get("message", "")
            user_id = data.get("params", {}).get("user_id", "")
            group_id = data.get("params", {}).get("group_id", "")
            
            is_group = bool(group_id)
            contact = user_id or group_id or ""
            
            # 检查是否附带 TTS 参数
            tts_params = None
            if isinstance(message, list):
                for item in message:
                    if isinstance(item, dict) and item.get("type") == "tts":
                        tts_params = item.get("data", {})
                        break
            
            if tts_params and "text" in tts_params:
                # 发送 TTS 指令给手机
                await self._send_to_phone(session, {
                    "type": "tts_play",
                    "id": str(uuid.uuid4())[:8],
                    "text": tts_params["text"],
                    "params": tts_params.get("params", {})
                })
            else:
                # 普通文本消息
                text = message if isinstance(message, str) else str(message)
                await self._send_to_phone(session, {
                    "type": "send_message",
                    "id": str(uuid.uuid4())[:8],
                    "contact": contact,
                    "text": text,
                    "is_group": is_group,
                    "group": group_id or ""
                })
    
    # ============================================================
    # 消息处理
    # ============================================================
    
    async def _handle_incoming_message(self, session: DeviceSession, msg: Dict):
        """处理手机发来的消息 → 转为 OneBot 事件推送给 AstrBot"""
        if not session.onebot_ws or not session.onebot_connected:
            logger.warning(f"设备 {session.device_id} OneBot 未连接，消息丢弃")
            return
        
        app = msg.get("app", "unknown")
        sender = msg.get("sender", "unknown")
        content = msg.get("content", "")
        is_group = msg.get("is_group", False)
        group_name = msg.get("group", "")
        
        # 构造 OneBot v11 事件
        event = {
            "time": int(time.time()),
            "self_id": session.device_id,
            "post_type": "message",
            "message_type": "group" if is_group else "private",
            "sub_type": "normal",
            "message_id": int(time.time() * 1000),
            "user_id": self._make_user_id(sender),
            "message": [
                {
                    "type": "text",
                    "data": {"text": f"[{app}] {sender}: {content}" if is_group else content}
                }
            ],
            "raw_message": content,
            "font": 0,
            "sender": {
                "user_id": self._make_user_id(sender),
                "nickname": sender,
                "sex": "unknown",
                "age": 0
            }
        }
        
        if is_group:
            event["group_id"] = self._make_group_id(group_name)
            event["anonymous"] = None
        
        try:
            await session.onebot_ws.send(json.dumps(event, ensure_ascii=False))
            logger.debug(f"📤 OneBot 上报: [{app}] {sender}: {content[:50]}")
        except Exception as e:
            logger.error(f"OneBot 上报失败: {e}")
    
    async def _handle_voice_text(self, session: DeviceSession, msg: Dict):
        """处理实时语音识别文本 → 转为 OneBot voice 事件"""
        if not session.onebot_ws or not session.onebot_connected:
            return
        
        text = msg.get("text", "")
        call_id = msg.get("call_id", "")
        
        event = {
            "time": int(time.time()),
            "self_id": session.device_id,
            "post_type": "message",
            "message_type": "voice",
            "sub_type": "normal",
            "message_id": int(time.time() * 1000),
            "user_id": f"call_{call_id}",
            "message": [
                {
                    "type": "text",
                    "data": {"text": f"[voice_text] {text}"}
                }
            ],
            "raw_message": f"[voice_text] {text}",
            "font": 0,
            "sender": {
                "user_id": f"call_{call_id}",
                "nickname": f"通话-{call_id[:6]}",
                "sex": "unknown",
                "age": 0
            }
        }
        
        try:
            await session.onebot_ws.send(json.dumps(event, ensure_ascii=False))
            logger.debug(f"🎤 语音识别上报: {text[:80]}")
        except Exception as e:
            logger.error(f"语音识别上报失败: {e}")
    
    async def _handle_call_event(self, session: DeviceSession, msg: Dict):
        """处理通话事件（来电、接通、挂断等）"""
        event_type = msg.get("call_event", "")
        call_id = msg.get("call_id", "")
        caller = msg.get("caller", "unknown")
        app = msg.get("app", "unknown")
        call_type = msg.get("call_type", "voice")  # voice / video
        
        logger.info(f"📞 通话事件: {event_type} | app={app} caller={caller} type={call_type}")
        
        # 如果是来电事件，可触发自动接听（由配置决定）
        if event_type == "incoming_call":
            await self._handle_incoming_call(session, msg)
    
    async def _handle_incoming_call(self, session: DeviceSession, msg: Dict):
        """处理来电事件 — 根据配置决定是否自动接听"""
        # 检查是否有自动接听配置（可从设备配置或默认配置读取）
        auto_answer = msg.get("auto_answer", False)
        delay = msg.get("answer_delay", 3)
        
        if auto_answer:
            logger.info(f"📞 自动接听: {delay}s 后接听来电")
            await asyncio.sleep(delay)
            await self._send_to_phone(session, {
                "type": "answer_call",
                "id": str(uuid.uuid4())[:8],
                "call_id": msg.get("call_id", "")
            })
    
    def _update_device_state(self, session: DeviceSession, msg: Dict):
        """更新设备状态信息"""
        pass  # 状态信息记录，可按需扩展
    
    # ============================================================
    # MCP 服务器（Stdio 传输）
    # ============================================================
    
    async def _run_mcp_server(self):
        """启动 MCP Stdio 服务器"""
        logger.info("🔧 启动 MCP Server (Stdio)...")
        
        mcp_server = Server(self.config.mcp_name)
        
        @mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            return self._mcp_tools
        
        @mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            handler = self._mcp_handlers.get(name)
            if handler:
                try:
                    result = await handler(**arguments)
                    return [TextContent(type="text", text=str(result))]
                except Exception as e:
                    logger.error(f"MCP 工具 {name} 执行失败: {e}")
                    return [TextContent(type="text", text=f"错误: {str(e)}")]
            return [TextContent(type="text", text=f"未知工具: {name}")]
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"MCP Server 运行异常: {e}")
    
    def _register_all_mcp_tools(self):
        """注册所有 MCP 工具 — 涵盖 phoneMcp + mcp_for_android + 通话控制"""
        
        self._register_device_tools()
        self._register_ui_automation_tools()
        self._register_call_tools()
        self._register_app_tools()
        
        logger.info(f"🔧 已注册 {len(self._mcp_tools)} 个 MCP 工具")
    
    def _register_device_tools(self):
        """注册手机设备操控工具（phoneMcp 完整能力）"""
        
        tools_definitions = [
            ("screenshot", "截取手机屏幕截图", {"device_id": ("string", "目标设备ID（可选，默认第一个在线设备）")}),
            ("get_clipboard", "获取剪贴板内容", {"device_id": ("string", "目标设备ID")}),
            ("set_clipboard", "设置剪贴板内容", {"device_id": ("string", "目标设备ID"), "text": ("string", "要设置的文本")}),
            ("get_device_info", "获取手机设备信息（型号、系统版本等）", {"device_id": ("string", "目标设备ID")}),
            ("get_sensors", "获取手机传感器数据", {"device_id": ("string", "目标设备ID")}),
            ("exec_shell", "在手机上执行 Shell 命令（需 Root）", {"device_id": ("string", "目标设备ID"), "command": ("string", "Shell命令")}),
            ("get_installed_apps", "获取已安装应用列表", {"device_id": ("string", "目标设备ID")}),
            ("get_current_activity", "获取当前前台 Activity", {"device_id": ("string", "目标设备ID")}),
            ("get_location", "获取手机 GPS 位置", {"device_id": ("string", "目标设备ID")}),
            # 操控类
            ("tap", "单击屏幕坐标", {"device_id": ("string", "目标设备ID"), "x": ("number", "X坐标"), "y": ("number", "Y坐标")}),
            ("double_tap", "双击屏幕坐标", {"device_id": ("string", "目标设备ID"), "x": ("number", "X坐标"), "y": ("number", "Y坐标")}),
            ("long_press", "长按屏幕", {"device_id": ("string", "目标设备ID"), "x": ("number", "X坐标"), "y": ("number", "Y坐标"), "duration_ms": ("number", "长按时长(毫秒，默认800)")}),
            ("swipe", "滑动屏幕", {"device_id": ("string", "目标设备ID"), "x1": ("number", "起点X"), "y1": ("number", "起点Y"), "x2": ("number", "终点X"), "y2": ("number", "终点Y"), "duration_ms": ("number", "滑动时长(毫秒，默认300)")}),
            ("press_key", "按下系统按键（home/back/recent/volume_up/volume_down/enter/delete）", {"device_id": ("string", "目标设备ID"), "key": ("string", "按键名称")}),
            ("type_text", "输入文本", {"device_id": ("string", "目标设备ID"), "text": ("string", "要输入的文本")}),
            ("send_phone_message", "通过手机发送消息", {"device_id": ("string", "目标设备ID"), "app": ("string", "应用包名"), "contact": ("string", "联系人/群名"), "text": ("string", "消息内容"), "is_group": ("boolean", "是否群聊")}),
        ]
        
        for name, desc, params in tools_definitions:
            param_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            for pname, (ptype, pdesc) in params.items():
                param_schema["properties"][pname] = {"type": ptype, "description": pdesc}
                if ptype != "string" or pname != "device_id":
                    param_schema["required"].append(pname)
            
            self._mcp_tools.append(Tool(name=name, description=desc, inputSchema=param_schema))
            self._mcp_handlers[name] = self._make_device_handler(name)
    
    def _register_ui_automation_tools(self):
        """注册 UI 自动化工具（mcp_for_android 完整能力）"""
        
        ui_tools = [
            ("get_ui_tree", "获取当前屏幕 UI 层级树（XML/JSON）", {
                "device_id": ("string", "目标设备ID"),
                "format": ("string", "输出格式：xml 或 json（默认json）")
            }),
            ("find_and_click", "根据条件查找 UI 元素并点击", {
                "device_id": ("string", "目标设备ID"),
                "text": ("string", "要查找的文本（可选）"),
                "resource_id": ("string", "资源ID（可选）"),
                "content_desc": ("string", "内容描述（可选）"),
                "class_name": ("string", "类名（可选）"),
                "index": ("number", "匹配第N个元素（默认0）")
            }),
            ("find_and_set_text", "查找可编辑元素并输入文本", {
                "device_id": ("string", "目标设备ID"),
                "text": ("string", "要输入的文本"),
                "hint_text": ("string", "输入框提示文字（可选，用于定位）"),
                "resource_id": ("string", "输入框资源ID（可选）")
            }),
            ("scroll_to_find", "滚动查找特定元素", {
                "device_id": ("string", "目标设备ID"),
                "text": ("string", "要查找的文本"),
                "max_scrolls": ("number", "最大滚动次数（默认10）")
            }),
            ("scroll", "按方向或距离滚动屏幕", {
                "device_id": ("string", "目标设备ID"),
                "direction": ("string", "方向：up/down/left/right"),
                "distance": ("number", "滚动距离（像素，默认500）")
            }),
            ("ui_press", "长按 UI 元素", {
                "device_id": ("string", "目标设备ID"),
                "text": ("string", "要长按的元素文本"),
                "duration_ms": ("number", "长按时长(毫秒，默认1000)")
            }),
            ("back", "模拟返回键", {"device_id": ("string", "目标设备ID")}),
            ("home", "模拟主页键", {"device_id": ("string", "目标设备ID")}),
        ]
        
        for name, desc, params in ui_tools:
            param_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            for pname, (ptype, pdesc) in params.items():
                param_schema["properties"][pname] = {"type": ptype, "description": pdesc}
                if ptype != "string" or pname != "device_id":
                    param_schema["required"].append(pname)
            
            self._mcp_tools.append(Tool(name=name, description=desc, inputSchema=param_schema))
            self._mcp_handlers[name] = self._make_device_handler(name)
    
    def _register_call_tools(self):
        """注册通话控制工具"""
        
        call_tools = [
            ("start_call_capture", "启用通话音频/视频捕获与处理", {
                "device_id": ("string", "目标设备ID"),
                "app_package": ("string", "目标应用包名（如 com.tencent.mm）")
            }),
            ("stop_call_capture", "停止通话处理", {"device_id": ("string", "目标设备ID")}),
            ("send_tts_text", "发送 TTS 文本让手机合成并注入通话", {
                "device_id": ("string", "目标设备ID"),
                "text": ("string", "要合成的文本"),
                "voice": ("string", "音色名称（可选，如 gentle_female）"),
                "speed": ("number", "语速（可选，1.0为正常）"),
                "pitch": ("number", "语调（可选，1.0为正常）")
            }),
            ("set_asr_model", "配置语音识别模型", {
                "device_id": ("string", "目标设备ID"),
                "model": ("string", "模型名称（cloud_whisper/vosk/sherpa-onnx）"),
                "language": ("string", "语言代码（可选，如 zh/en）")
            }),
            ("set_tts_model", "配置语音合成模型", {
                "device_id": ("string", "目标设备ID"),
                "model": ("string", "模型名称（cloud_azure/piper/edge_tts）"),
                "voice": ("string", "音色名称（可选）")
            }),
            ("answer_call", "接听来电", {"device_id": ("string", "目标设备ID")}),
            ("hangup_call", "挂断通话", {"device_id": ("string", "目标设备ID")}),
        ]
        
        for name, desc, params in call_tools:
            param_schema = {
                "type": "object",
                "properties": {},
                "required": ["device_id"]
            }
            for pname, (ptype, pdesc) in params.items():
                param_schema["properties"][pname] = {"type": ptype, "description": pdesc}
            
            self._mcp_tools.append(Tool(name=name, description=desc, inputSchema=param_schema))
            self._mcp_handlers[name] = self._make_device_handler(name)
    
    def _register_app_tools(self):
        """注册应用管理工具"""
        
        app_tools = [
            ("open_app", "打开指定应用", {
                "device_id": ("string", "目标设备ID"),
                "package_name": ("string", "应用包名")
            }),
            ("close_app", "强制停止指定应用", {
                "device_id": ("string", "目标设备ID"),
                "package_name": ("string", "应用包名")
            }),
        ]
        
        for name, desc, params in app_tools:
            param_schema = {
                "type": "object",
                "properties": {},
                "required": ["device_id", "package_name"]
            }
            for pname, (ptype, pdesc) in params.items():
                param_schema["properties"][pname] = {"type": ptype, "description": pdesc}
            
            self._mcp_tools.append(Tool(name=name, description=desc, inputSchema=param_schema))
            self._mcp_handlers[name] = self._make_device_handler(name)
    
    def _make_device_handler(self, tool_name: str) -> Callable:
        """
        创建设备操作处理器。
        优先使用 ADB（如果可用），否则通过 WebSocket 转发给手机 App。
        """
        async def handler(**kwargs) -> str:
            device_id = kwargs.pop("device_id", None)
            
            # 确定目标设备
            session = self._resolve_device(device_id)
            if not session:
                return json.dumps({"error": "设备不在线", "device_id": device_id}, ensure_ascii=False)
            
            # 生成工具调用 ID
            tool_id = str(uuid.uuid4())[:8]
            
            # 尝试 ADB 执行（如果工具支持且 ADB 可用）
            if self._adb_available and tool_name in self._ADB_SUPPORTED_TOOLS:
                try:
                    result = await self._execute_via_adb(tool_name, device_id, kwargs)
                    if result is not None:
                        return json.dumps(result, ensure_ascii=False)
                except Exception as e:
                    logger.debug(f"ADB 执行失败，回退 WebSocket: {e}")
            
            # WebSocket 下发到手机
            command = {
                "type": "tool_command",
                "id": tool_id,
                "tool": tool_name,
                "params": kwargs
            }
            
            # 创建等待事件
            event = asyncio.Event()
            session.pending_tools[tool_id] = event
            
            try:
                await self._send_to_phone(session, command)
                
                # 等待结果
                try:
                    await asyncio.wait_for(event.wait(), timeout=self.config.tool_timeout)
                except asyncio.TimeoutError:
                    return json.dumps({"error": f"工具执行超时 ({self.config.tool_timeout}s)", "tool": tool_name})
                
                result = session.tool_results.pop(tool_id, {"error": "无结果"})
                session.pending_tools.pop(tool_id, None)
                
                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False)
                return str(result)
                
            except Exception as e:
                session.pending_tools.pop(tool_id, None)
                return json.dumps({"error": str(e), "tool": tool_name})
        
        return handler
    
    # ADB 支持的工具列表
    _ADB_SUPPORTED_TOOLS = {
        "screenshot", "tap", "swipe", "press_key", "type_text",
        "get_ui_tree", "open_app", "close_app", "get_current_activity",
        "get_device_info", "exec_shell", "home", "back",
        "get_installed_apps"
    }
    
    async def _execute_via_adb(self, tool_name: str, device_id: str, params: Dict) -> Optional[Dict]:
        """通过 ADB 执行工具命令"""
        adb = self.config.adb_path
        
        if tool_name == "screenshot":
            import tempfile
            path = f"/data/local/tmp/huiyi_screenshot_{int(time.time())}.png"
            await self._adb_shell(adb, f"screencap -p {path}")
            await asyncio.sleep(0.5)
            result = await self._adb_shell(adb, f"cat {path} | base64")
            return {"success": True, "data": result, "type": "base64_image"}
        
        elif tool_name == "tap":
            x, y = int(params.get("x", 0)), int(params.get("y", 0))
            await self._adb_shell(adb, f"input tap {x} {y}")
            return {"success": True, "action": f"tap({x},{y})"}
        
        elif tool_name == "swipe":
            x1, y1 = int(params.get("x1", 0)), int(params.get("y1", 0))
            x2, y2 = int(params.get("x2", 0)), int(params.get("y2", 0))
            dur = int(params.get("duration_ms", 300))
            await self._adb_shell(adb, f"input swipe {x1} {y1} {x2} {y2} {dur}")
            return {"success": True}
        
        elif tool_name == "press_key":
            key_map = {
                "home": "KEYCODE_HOME", "back": "KEYCODE_BACK",
                "recent": "KEYCODE_APP_SWITCH", "volume_up": "KEYCODE_VOLUME_UP",
                "volume_down": "KEYCODE_VOLUME_DOWN", "enter": "KEYCODE_ENTER",
                "delete": "KEYCODE_DEL"
            }
            key = params.get("key", "").lower()
            keycode = key_map.get(key, f"KEYCODE_{key.upper()}")
            await self._adb_shell(adb, f"input keyevent {keycode}")
            return {"success": True}
        
        elif tool_name == "type_text":
            text = params.get("text", "")
            # 转义特殊字符
            text = text.replace(" ", "%s").replace("'", "\\'")
            await self._adb_shell(adb, f'input text "{text}"')
            return {"success": True}
        
        elif tool_name == "get_ui_tree":
            result = await self._adb_shell(adb, "uiautomator dump /data/local/tmp/ui.xml && cat /data/local/tmp/ui.xml")
            return {"success": True, "ui_tree": result}
        
        elif tool_name == "open_app":
            pkg = params.get("package_name", "")
            result = await self._adb_shell(adb, f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
            return {"success": True, "package": pkg}
        
        elif tool_name == "close_app":
            pkg = params.get("package_name", "")
            await self._adb_shell(adb, f"am force-stop {pkg}")
            return {"success": True}
        
        elif tool_name == "get_current_activity":
            result = await self._adb_shell(adb, "dumpsys activity activities | grep mResumedActivity")
            return {"success": True, "activity": result.strip()}
        
        elif tool_name == "get_device_info":
            model = await self._adb_shell(adb, "getprop ro.product.model")
            version = await self._adb_shell(adb, "getprop ro.build.version.release")
            sdk = await self._adb_shell(adb, "getprop ro.build.version.sdk")
            return {"success": True, "model": model.strip(), "android": version.strip(), "sdk": sdk.strip()}
        
        elif tool_name == "get_installed_apps":
            result = await self._adb_shell(adb, "pm list packages -3")
            packages = [line.replace("package:", "").strip() for line in result.split("\n") if line.startswith("package:")]
            return {"success": True, "packages": packages}
        
        elif tool_name == "exec_shell":
            cmd = params.get("command", "")
            result = await self._adb_shell(adb, cmd)
            return {"success": True, "output": result}
        
        elif tool_name == "home":
            await self._adb_shell(adb, "input keyevent KEYCODE_HOME")
            return {"success": True}
        
        elif tool_name == "back":
            await self._adb_shell(adb, "input keyevent KEYCODE_BACK")
            return {"success": True}
        
        return None  # 不支持 ADB 执行
    
    async def _adb_shell(self, adb_path: str, command: str) -> str:
        """执行 ADB shell 命令"""
        proc = await asyncio.create_subprocess_shell(
            f"{adb_path} shell {command}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ADB 命令失败: {stderr.decode()}")
        return stdout.decode("utf-8", errors="replace")
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _resolve_device(self, device_id: Optional[str]) -> Optional[DeviceSession]:
        """
        解析目标设备。
        如果未指定 device_id，返回第一个在线设备。
        """
        if device_id:
            session = self.devices.get(device_id)
            if session and session.is_online:
                return session
            return None
        
        # 返回第一个在线设备
        for session in self.devices.values():
            if session.is_online:
                return session
        return None
    
    async def _send_to_phone(self, session: DeviceSession, data: Dict) -> bool:
        """发送消息到手机 WebSocket"""
        if not session.ws:
            return False
        
        try:
            await session.ws.send(json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"发送到手机失败: {e}")
            return False
    
    @staticmethod
    def _make_user_id(name: str) -> str:
        """从名称生成数字 user_id"""
        return str(int(hashlib.md5(name.encode()).hexdigest()[:12], 16) % 10**10)
    
    @staticmethod
    def _make_group_id(name: str) -> str:
        """从群名生成数字 group_id"""
        return str(int(hashlib.md5(name.encode()).hexdigest()[:12], 16) % 10**10)
    
    def _check_adb(self) -> bool:
        """检查 ADB 是否可用"""
        try:
            result = subprocess.run(
                [self.config.adb_path, "devices"],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            # 检查是否有设备连接
            for line in lines[1:]:
                if line.strip() and "device" in line:
                    logger.info(f"✅ ADB 设备已检测: {line.strip()}")
                    return True
            logger.info("⚠️ ADB 可用但未检测到设备")
            return True  # 命令可用但无设备
        except Exception as e:
            logger.debug(f"ADB 不可用: {e}")
            return False


# ============================================================
# 命令行入口
# ============================================================

def load_config_from_file(path: str) -> BridgeConfig:
    """从 YAML 文件加载配置"""
    if HAS_YAML and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return BridgeConfig.from_dict(data)
    return BridgeConfig()


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description="HuiYiapi Bridge Server")
    parser.add_argument("--config", "-c", default="config.yaml", help="配置文件路径")
    parser.add_argument("--host", default="0.0.0.0", help="WebSocket 监听地址")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket 监听端口")
    parser.add_argument("--onebot-url", default="ws://127.0.0.1:6700/", help="OneBot 反向 WS 地址")
    parser.add_argument("--token", default="", help="OneBot access_token")
    parser.add_argument("--no-mcp", action="store_true", help="禁用 MCP Server")
    parser.add_argument("--adb", default="adb", help="ADB 路径")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


async def main():
    """主入口"""
    args = parse_args()
    
    # 加载配置
    config = load_config_from_file(args.config)
    
    # 命令行参数覆盖
    config.ws_host = args.host
    config.ws_port = args.port
    config.onebot_url = args.onebot_url
    config.onebot_access_token = args.token or config.onebot_access_token
    config.mcp_enabled = not args.no_mcp
    config.adb_path = args.adb
    config.log_level = args.log_level
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, config.log_level))
    
    # 创建并启动桥接器
    bridge = HuiYiBridgeServer(config)
    
    # 注册信号处理
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(bridge.shutdown()))
        except NotImplementedError:
            pass  # Windows 不支持
    
    await bridge.start()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════╗
    ║          🌙  HuiYiapi Bridge             ║
    ║      手机消息桥接 · OneBot · MCP         ║
    ╚══════════════════════════════════════════╝
    """)
    
    if not HAS_WEBSOCKETS:
        print("❌ 缺少 websockets 库。请执行: pip install websockets")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
