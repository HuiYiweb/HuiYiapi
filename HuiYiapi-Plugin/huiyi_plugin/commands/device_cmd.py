"""设备管理命令"""
import logging
from huiyi_plugin.device.manager import DeviceManager

logger = logging.getLogger("huiyi_plugin.device_cmd")

class DeviceCommands:
    def __init__(self, device_manager: DeviceManager):
        self.manager = device_manager

    async def list_devices(self) -> str:
        devices = await self.manager.registry.get_all()
        if not devices:
            return "📱 暂无注册设备"
        lines = ["📱 **已注册设备**："]
        for i, d in enumerate(devices, 1):
            status = "🟢" if self.manager._status.get(d.device_id, None) and self.manager._status[d.device_id].online else "🔴"
            lines.append(f"{i}. {status} **{d.device_name}** (`{d.device_id}`)")
        return "\n".join(lines)
