"""心跳检测"""
import asyncio
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger("huiyi_plugin.heartbeat")

class HeartbeatMonitor:
    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self._last_seen: Dict[str, datetime] = {}
    
    def touch(self, device_id: str):
        self._last_seen[device_id] = datetime.now()
    
    def is_alive(self, device_id: str) -> bool:
        if device_id not in self._last_seen:
            return False
        return (datetime.now() - self._last_seen[device_id]).total_seconds() < self.timeout
