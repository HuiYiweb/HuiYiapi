"""
设备注册表 — 使用 SQLite 持久化设备配置。

注意：所有数据库操作返回字典或列表并确保类型正确。
"""

import json
import aiosqlite
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import DeviceConfig, MonitoredApp, VoiceCallConfig

logger = logging.getLogger("huiyi_plugin.registry")


class DeviceRegistry:
    """设备配置的 SQLite 持久化存储"""
    
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def initialize(self):
        """初始化数据库和表结构"""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                bridge_ws_url TEXT DEFAULT 'ws://localhost:8765',
                monitored_apps TEXT DEFAULT '[]',
                voice_config TEXT DEFAULT '{}',
                coordinate_template TEXT DEFAULT '1080x2400',
                access_token TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await self._conn.commit()
        logger.info(f"设备注册表已初始化: {self.db_path}")
    
    async def close(self):
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
    
    def __len__(self) -> int:
        """返回设备数量（需要异步获取，此处返回缓存值）"""
        return 0  # 实际通过 get_all 获取
    
    async def add(self, config: DeviceConfig) -> str:
        """添加新设备配置"""
        # 确保类型正确
        monitored_json = json.dumps(
            [app.to_dict() if isinstance(app, MonitoredApp) else app 
             for app in (config.monitored_apps if isinstance(config.monitored_apps, list) else [])],
            ensure_ascii=False
        )
        voice_json = json.dumps(
            config.voice_config.to_dict() if isinstance(config.voice_config, VoiceCallConfig) 
            else (config.voice_config if isinstance(config.voice_config, dict) else {}),
            ensure_ascii=False
        )
        
        await self._conn.execute(
            """INSERT OR REPLACE INTO devices 
               (device_id, device_name, bridge_ws_url, monitored_apps, voice_config, 
                coordinate_template, access_token, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                config.device_id, config.device_name, config.bridge_ws_url,
                monitored_json, voice_json, config.coordinate_template,
                config.access_token, config.created_at, config.updated_at
            )
        )
        await self._conn.commit()
        logger.info(f"设备已注册: {config.device_id} ({config.device_name})")
        return config.device_id
    
    async def update(self, device_id: str, data: Dict[str, Any]) -> None:
        """更新设备配置"""
        if not isinstance(data, dict):
            raise ValueError("更新数据必须是字典类型")
        
        # 检查设备是否存在
        existing = await self.get(device_id)
        if not existing:
            raise KeyError(f"设备 {device_id} 不存在")
        
        # 构建 UPDATE 语句
        fields = []
        values = []
        
        if "device_name" in data:
            fields.append("device_name = ?")
            values.append(data["device_name"])
        if "bridge_ws_url" in data:
            fields.append("bridge_ws_url = ?")
            values.append(data["bridge_ws_url"])
        if "monitored_apps" in data:
            apps = data["monitored_apps"]
            if isinstance(apps, list):
                fields.append("monitored_apps = ?")
                values.append(json.dumps(apps, ensure_ascii=False))
        if "voice_config" in data:
            vc = data["voice_config"]
            if isinstance(vc, (dict, VoiceCallConfig)):
                vc_dict = vc.to_dict() if isinstance(vc, VoiceCallConfig) else vc
                fields.append("voice_config = ?")
                values.append(json.dumps(vc_dict, ensure_ascii=False))
        if "coordinate_template" in data:
            fields.append("coordinate_template = ?")
            values.append(data["coordinate_template"])
        if "access_token" in data:
            fields.append("access_token = ?")
            values.append(data["access_token"])
        
        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(device_id)
        
        if fields:
            await self._conn.execute(
                f"UPDATE devices SET {', '.join(fields)} WHERE device_id = ?",
                values
            )
            await self._conn.commit()
            logger.info(f"设备配置已更新: {device_id}")
    
    async def delete(self, device_id: str) -> None:
        """删除设备配置"""
        await self._conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
        await self._conn.commit()
        logger.info(f"设备已删除: {device_id}")
    
    async def get(self, device_id: str) -> Optional[DeviceConfig]:
        """获取单个设备配置"""
        cursor = await self._conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_config(dict(row))
    
    async def get_all(self) -> List[DeviceConfig]:
        """获取所有设备配置"""
        cursor = await self._conn.execute("SELECT * FROM devices ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [self._row_to_config(dict(row)) for row in rows]
    
    def _row_to_config(self, row: Dict[str, Any]) -> DeviceConfig:
        """将数据库行转为 DeviceConfig（确保类型正确）"""
        # 解析 monitored_apps JSON
        apps_raw = row.get("monitored_apps", "[]")
        if isinstance(apps_raw, str):
            try:
                apps_raw = json.loads(apps_raw)
            except json.JSONDecodeError:
                apps_raw = []
        if not isinstance(apps_raw, list):
            apps_raw = []
        
        apps = []
        for a in apps_raw:
            if isinstance(a, dict):
                apps.append(MonitoredApp.from_dict(a))
        
        # 解析 voice_config JSON
        voice_raw = row.get("voice_config", "{}")
        if isinstance(voice_raw, str):
            try:
                voice_raw = json.loads(voice_raw)
            except json.JSONDecodeError:
                voice_raw = {}
        if not isinstance(voice_raw, dict):
            voice_raw = {}
        voice_config = VoiceCallConfig.from_dict(voice_raw)
        
        return DeviceConfig(
            device_id=row.get("device_id", ""),
            device_name=row.get("device_name", "未命名"),
            bridge_ws_url=row.get("bridge_ws_url", "ws://localhost:8765"),
            monitored_apps=apps,
            voice_config=voice_config,
            coordinate_template=row.get("coordinate_template", "1080x2400"),
            access_token=row.get("access_token", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", "")
        )
