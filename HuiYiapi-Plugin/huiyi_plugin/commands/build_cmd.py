"""APK 构建命令"""
import logging
from huiyi_plugin.device.manager import DeviceManager
from huiyi_plugin.apk_builder.builder import ApkBuilder, ConfigGenerator

logger = logging.getLogger("huiyi_plugin.build_cmd")

class BuildCommands:
    def __init__(self, device_manager: DeviceManager, apk_builder: ApkBuilder, config_generator: ConfigGenerator):
        self.device_manager = device_manager
        self.apk_builder = apk_builder
        self.config_generator = config_generator

    async def build_apk(self, device_id: str) -> str:
        config = await self.device_manager.registry.get(device_id)
        if not config:
            return f"❌ 设备 `{device_id}` 不存在"
        build_config = self.config_generator.generate(config.to_dict())
        build_id = await self.apk_builder.start_build(device_id, {"config": build_config})
        return f"🔨 构建已开始！\n构建 ID: `{build_id}`\n设备: {config.device_name}"
