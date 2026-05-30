"""
设备数据模型 — 定义插件中所有数据实体。

注意：所有字典操作确保类型正确，不应对列表调用 .items()。
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass
class MonitoredApp:
    """被监听的应用配置"""
    package_name: str          # 应用包名，如 com.tencent.mm
    app_name: str              # 应用显示名称，如 "微信"
    icon_url: str = ""         # 应用图标 URL
    enabled: bool = True       # 是否启用监听
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitoredApp":
        # 确保 data 是字典类型
        if not isinstance(data, dict):
            raise ValueError(f"MonitoredApp 需要字典类型，收到: {type(data)}")
        return cls(
            package_name=data.get("package_name", ""),
            app_name=data.get("app_name", ""),
            icon_url=data.get("icon_url", ""),
            enabled=data.get("enabled", True)
        )


@dataclass
class VoiceCallConfig:
    """语音/视频通话配置"""
    auto_answer: bool = False           # 是否自动接听
    answer_delay: int = 3               # 接听延迟（秒）
    default_asr_model: str = "cloud"    # 默认 ASR 模型
    default_tts_model: str = "cloud"    # 默认 TTS 模型
    tts_voice: str = "gentle_female"    # TTS 音色
    tts_speed: float = 1.0              # 语速
    tts_pitch: float = 1.0              # 语调
    video_enabled: bool = False         # 是否启用视频处理
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceCallConfig":
        if not isinstance(data, dict):
            data = {}
        return cls(
            auto_answer=data.get("auto_answer", False),
            answer_delay=data.get("answer_delay", 3),
            default_asr_model=data.get("default_asr_model", "cloud"),
            default_tts_model=data.get("default_tts_model", "cloud"),
            tts_voice=data.get("tts_voice", "gentle_female"),
            tts_speed=data.get("tts_speed", 1.0),
            tts_pitch=data.get("tts_pitch", 1.0),
            video_enabled=data.get("video_enabled", False)
        )


@dataclass
class DeviceConfig:
    """单个设备的完整配置"""
    device_id: str                      # 唯一设备标识
    device_name: str                    # 设备名称（自定义）
    bridge_ws_url: str = "ws://localhost:8765"  # 桥接器 WebSocket 地址
    monitored_apps: List[MonitoredApp] = field(default_factory=list)  # 监听应用列表
    voice_config: VoiceCallConfig = field(default_factory=VoiceCallConfig)  # 通话配置
    coordinate_template: str = "1080x2400"  # 坐标模板
    access_token: str = ""              # OneBot access token
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # 序列化内部列表
        result["monitored_apps"] = [app.to_dict() if isinstance(app, MonitoredApp) else app for app in self.monitored_apps]
        result["voice_config"] = self.voice_config.to_dict() if isinstance(self.voice_config, VoiceCallConfig) else self.voice_config
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceConfig":
        if not isinstance(data, dict):
            raise ValueError(f"DeviceConfig 需要字典类型，收到: {type(data)}")
        
        # 处理 monitored_apps（确保是列表）
        apps_raw = data.get("monitored_apps", [])
        if not isinstance(apps_raw, list):
            apps_raw = []
        apps = [MonitoredApp.from_dict(a) if isinstance(a, dict) else a for a in apps_raw]
        
        # 处理 voice_config（确保是字典）
        voice_raw = data.get("voice_config", {})
        if not isinstance(voice_raw, dict):
            voice_raw = {}
        voice_config = VoiceCallConfig.from_dict(voice_raw)
        
        return cls(
            device_id=data.get("device_id", str(uuid.uuid4())[:8]),
            device_name=data.get("device_name", "未命名设备"),
            bridge_ws_url=data.get("bridge_ws_url", "ws://localhost:8765"),
            monitored_apps=apps,
            voice_config=voice_config,
            coordinate_template=data.get("coordinate_template", "1080x2400"),
            access_token=data.get("access_token", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


@dataclass
class DeviceStatus:
    """设备实时状态"""
    device_id: str
    online: bool = False
    last_active: Optional[str] = None
    onebot_connected: bool = False
    ws_connected: bool = False
    call_active: bool = False
    current_app: str = ""
    battery_level: int = -1
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OneBotConnection:
    """OneBot 连接信息"""
    device_id: str
    self_id: str
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    is_online: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BuildRecord:
    """APK 构建记录"""
    build_id: str
    device_id: str
    status: str = "queued"  # queued, building, success, failed
    apk_url: str = ""
    error_message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
