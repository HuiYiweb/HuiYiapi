"""
HuiYiapi — AstrBot 手机消息桥接与语音处理插件
=================================================
单实例插件，支持同时管理多台手机设备。
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# === 确保 huiyi_plugin 子包可被导入 ===
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

# === AstrBot v4.x 正确导入 ===
from astrbot.api import star
from astrbot.api.event import AstrMessageEvent

logger = logging.getLogger("huiyi_plugin")

PLUGIN_NAME = "HuiYiapi"
PLUGIN_VERSION = "1.0.0"


class HuiYiPlugin(star.Star):
    """HuiYiapi 插件主类"""

    def __init__(self, context: star.Context, config: dict | None = None) -> None:
        super().__init__(context, config)
        self.context = context

        # 数据目录
        self.data_dir = Path(os.path.join(_plugin_dir, "data", "huiyiapi"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 核心组件
        self._init_modules()

        logger.info(f"[{PLUGIN_NAME}] 插件初始化完成，版本 {PLUGIN_VERSION}")

    def _init_modules(self):
        """导入子模块（sys.path 已在模块顶部设置）"""
        from huiyi_plugin.device.manager import DeviceManager
        from huiyi_plugin.device.registry import DeviceRegistry
        from huiyi_plugin.apk_builder.builder import ApkBuilder
        from huiyi_plugin.apk_builder.config_generator import ConfigGenerator

        self.device_registry = DeviceRegistry(self.data_dir / "devices.db")
        self.device_manager = DeviceManager(self.device_registry, self.context)
        self.apk_builder = ApkBuilder(self.data_dir / "builds")
        self.config_generator = ConfigGenerator()

    async def initialize(self) -> None:
        """插件被激活时调用"""
        try:
            await self.device_registry.initialize()
            logger.info(f"[{PLUGIN_NAME}] 设备注册表已加载")
            self._register_web_routes()
            logger.info(f"[{PLUGIN_NAME}] Web API 路由已注册")
            asyncio.create_task(self.device_manager.start_heartbeat_check())
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 初始化异常: {e}")

    async def terminate(self) -> None:
        """插件被禁用/重载时调用"""
        try:
            await self.device_manager.cleanup()
            await self.device_registry.close()
            logger.info(f"[{PLUGIN_NAME}] 插件已卸载")
        except Exception as e:
            logger.error(f"[{PLUGIN_NAME}] 卸载异常: {e}")

    def _register_web_routes(self):
        """使用 AstrBot v4 register_web_api 注册路由"""
        self.context.register_web_api(
            "/huiyiapi/devices",
            self._api_get_devices,
            ["GET"],
            "获取所有设备列表",
        )
        self.context.register_web_api(
            "/huiyiapi/devices",
            self._api_add_device,
            ["POST"],
            "添加新设备",
        )
        self.context.register_web_api(
            "/huiyiapi/builds",
            self._api_get_builds,
            ["GET"],
            "获取构建记录",
        )
        self.context.register_web_api(
            "/huiyiapi/connections",
            self._api_get_connections,
            ["GET"],
            "获取连接状态",
        )
        logger.info(f"[{PLUGIN_NAME}] Web API 路由已注册")

    # ============ Web API ============

    async def _api_get_devices(self, **kwargs):
        devices = await self.device_registry.get_all()
        return {"code": 0, "data": [d.to_dict() for d in devices], "total": len(devices)}

    async def _api_add_device(self, **kwargs):
        try:
            data = kwargs.get("data", {})
            if not isinstance(data, dict):
                data = {}
            from huiyi_plugin.device.models import DeviceConfig
            config = DeviceConfig.from_dict(data)
            device_id = await self.device_registry.add(config)
            return {"code": 0, "data": {"device_id": device_id}, "message": "设备添加成功"}
        except Exception as e:
            return {"code": 1, "message": str(e)}

    async def _api_get_builds(self, **kwargs):
        builds = await self.apk_builder.get_all_builds()
        return {"code": 0, "data": builds}

    async def _api_get_connections(self, **kwargs):
        connections = await self.device_manager.get_all_connections()
        return {"code": 0, "data": [c.to_dict() for c in connections]}
