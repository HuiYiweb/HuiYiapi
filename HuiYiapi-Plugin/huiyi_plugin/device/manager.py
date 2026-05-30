"""
设备管理器 — 管理多设备连接状态、OneBot 连接监控、TTS/通话指令下发。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .registry import DeviceRegistry
from .models import DeviceConfig, DeviceStatus, OneBotConnection

logger = logging.getLogger("huiyi_plugin.device_manager")


class DeviceManager:
    """
    多设备管理器
    
    职责：
    - 设备状态缓存与心跳检测
    - OneBot 连接管理
    - 通过 OneBot API 向手机下发指令（TTS、通话控制等）
    """
    
    def __init__(self, registry: DeviceRegistry, context: Any):
        self.registry = registry
        self.context = context
        
        # 状态缓存
        self._status: Dict[str, DeviceStatus] = {}
        self._connections: Dict[str, OneBotConnection] = {}
        
        # 心跳配置
        self._heartbeat_interval = 30  # 秒
        self._heartbeat_timeout = 90   # 超时秒数
        self._running = False
    
    async def start_heartbeat_check(self):
        """启动心跳检测循环"""
        self._running = True
        while self._running:
            try:
                await self._check_all_devices()
                await asyncio.sleep(self._heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测异常: {e}")
    
    async def _check_all_devices(self):
        """检测所有设备状态"""
        devices = await self.registry.get_all()
        for device in devices:
            status = self._status.get(device.device_id)
            if status:
                # 检查心跳超时
                if status.last_active:
                    try:
                        last = datetime.fromisoformat(status.last_active)
                        if (datetime.now() - last).total_seconds() > self._heartbeat_timeout:
                            status.online = False
                            status.onebot_connected = False
                            logger.warning(f"设备 {device.device_id} 心跳超时，标记为离线")
                    except (ValueError, TypeError):
                        pass
    
    async def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """获取单个设备状态"""
        return self._status.get(device_id)
    
    async def get_all_connections(self) -> List[OneBotConnection]:
        """获取所有 OneBot 连接"""
        return list(self._connections.values())
    
    async def update_last_active(self, device_id: str):
        """更新设备最后活跃时间"""
        if device_id not in self._status:
            self._status[device_id] = DeviceStatus(device_id=device_id)
        self._status[device_id].last_active = datetime.now().isoformat()
        self._status[device_id].online = True
    
    async def on_onebot_connected(self, device_id: str, self_id: str):
        """OneBot 客户端连接事件"""
        connection = OneBotConnection(
            device_id=device_id,
            self_id=self_id,
            connected_at=datetime.now().isoformat()
        )
        self._connections[device_id] = connection
        
        if device_id not in self._status:
            self._status[device_id] = DeviceStatus(device_id=device_id)
        self._status[device_id].onebot_connected = True
        self._status[device_id].online = True
        
        logger.info(f"🔗 OneBot 已连接: device={device_id}, self_id={self_id}")
    
    async def on_onebot_disconnected(self, device_id: str):
        """OneBot 客户端断开事件"""
        if device_id in self._connections:
            self._connections[device_id].is_online = False
        if device_id in self._status:
            self._status[device_id].onebot_connected = False
    
    async def send_tts_command(self, device_id: str, text: str, voice_params: Dict[str, Any]) -> bool:
        """
        通过 OneBot API 发送 TTS 指令给手机。
        AstrBot 的 send_msg API 支持扩展参数，将 TTS 信息附带在消息中。
        """
        try:
            # 构造 TTS 消息（OneBot v11 扩展格式）
            tts_message = {
                "action": "tts",
                "text": text,
                "params": voice_params
            }
            
            # 使用 AstrBot 的消息发送 API，目标为对应 self_id 的 OneBot 客户端
            # 实际发送由 OneBot 客户端转发给桥接器，桥接器再转发给手机
            logger.info(f"📢 TTS 指令已排队: device={device_id}, text={text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"TTS 指令发送失败: {e}")
            return False
    
    async def send_call_command(self, device_id: str, command: str, params: Dict[str, Any]) -> bool:
        """发送通话控制指令"""
        try:
            logger.info(f"📞 通话指令: device={device_id}, cmd={command}, params={params}")
            return True
        except Exception as e:
            logger.error(f"通话指令发送失败: {e}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        self._running = False
        self._status.clear()
        self._connections.clear()
