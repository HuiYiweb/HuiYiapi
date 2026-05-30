"""消息路由 — 根据消息来源路由到对应设备"""
import logging
from typing import Optional

logger = logging.getLogger("huiyi_plugin.router")

class DeviceRouter:
    """设备消息路由器"""
    
    @staticmethod
    def resolve_device_from_event(event: dict) -> Optional[str]:
        """从 OneBot 事件中解析设备 ID"""
        if not isinstance(event, dict):
            return None
        return (
            event.get("self_id") or 
            event.get("sender", {}).get("user_id") or 
            event.get("device_id")
        )
