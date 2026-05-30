"""
APK 构建器 — 一键构建定制 APK。

构建流程：
1. 从设备配置生成 config JSON
2. 调用云端构建服务（GitHub Actions / 自建 API）
3. 轮询构建状态
4. 获取下载链接
"""

import asyncio
import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime

from huiyi_plugin.device.models import BuildRecord

logger = logging.getLogger("huiyi_plugin.apk_builder")

# 默认构建配置
DEFAULT_BUILD_CONFIG = {
    "repo_url": "https://github.com/your-org/HuiYiapi-Android",
    "workflow_file": "build.yml",
    "branch": "main",
    "build_timeout": 1800,  # 30 分钟超时
}

# 已知的主流 IM 应用包名映射
KNOWN_IM_APPS = {
    "com.tencent.mm": {"name": "微信", "icon": "wechat"},
    "com.tencent.mobileqq": {"name": "QQ", "icon": "qq"},
    "org.telegram.messenger": {"name": "Telegram", "icon": "telegram"},
    "com.alibaba.android.rimet": {"name": "钉钉", "icon": "dingtalk"},
    "com.immomo.momo": {"name": "陌陌", "icon": "momo"},
    "com.sina.weibo": {"name": "微博", "icon": "weibo"},
    "com.eg.android.AlipayGphone": {"name": "支付宝", "icon": "alipay"},
}


class ConfigGenerator:
    """定制配置生成器 — 根据设备配置生成注入 APK 的配置"""
    
    @staticmethod
    def generate(device_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成注入 APK 的配置 JSON。
        该 JSON 将被写入 assets/config.json，APK 首次启动时读取。
        """
        config = {
            "device_id": device_config.get("device_id", ""),
            "device_name": device_config.get("device_name", "HuiYi Phone"),
            "bridge_ws_url": device_config.get("bridge_ws_url", "ws://localhost:8765"),
            "monitored_packages": [],
            "voice_config": device_config.get("voice_config", {}),
            "coordinate_template": device_config.get("coordinate_template", "1080x2400"),
            "build_time": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        # 处理监听包名列表
        monitored_apps = device_config.get("monitored_apps", [])
        if isinstance(monitored_apps, list):
            for app in monitored_apps:
                if isinstance(app, dict):
                    config["monitored_packages"].append({
                        "package": app.get("package_name", ""),
                        "name": app.get("app_name", ""),
                        "enabled": app.get("enabled", True)
                    })
        
        return config


class ApkBuilder:
    """
    APK 构建编排器
    
    支持两种构建模式：
    1. 云端构建：通过 GitHub Actions API 触发构建
    2. 本地构建：直接调用 Gradle CLI（需配置 Android SDK）
    """
    
    def __init__(self, build_dir: Path):
        self.build_dir = build_dir
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建记录存储（内存 + 可选持久化）
        self._builds: Dict[str, BuildRecord] = {}
        
        # 构建队列
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start_worker(self):
        """启动构建工作线程"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._build_worker())
            logger.info("APK 构建工作线程已启动")
    
    async def _build_worker(self):
        """构建工作循环"""
        while True:
            try:
                build_id = await self._queue.get()
                await self._execute_build(build_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"构建工作异常: {e}")
    
    async def start_build(self, device_id: str, build_params: Dict[str, Any]) -> str:
        """
        开始构建定制 APK
        
        Args:
            device_id: 设备标识
            build_params: 构建参数（仓库地址、分支等，可选）
        
        Returns:
            build_id: 构建任务 ID
        """
        build_id = str(uuid.uuid4())[:12]
        
        record = BuildRecord(
            build_id=build_id,
            device_id=device_id,
            status="queued"
        )
        self._builds[build_id] = record
        
        # 保存构建参数
        params_path = self.build_dir / f"{build_id}_params.json"
        params_path.write_text(json.dumps(build_params, ensure_ascii=False))
        
        # 加入构建队列
        await self._queue.put(build_id)
        
        logger.info(f"🔨 构建任务已创建: build_id={build_id}, device={device_id}")
        return build_id
    
    async def _execute_build(self, build_id: str):
        """执行实际构建（模拟/实际调用）"""
        record = self._builds.get(build_id)
        if not record:
            return
        
        record.status = "building"
        logger.info(f"🔨 开始构建: {build_id}")
        
        try:
            # 1. 读取构建参数
            params_path = self.build_dir / f"{build_id}_params.json"
            build_params = {}
            if params_path.exists():
                build_params = json.loads(params_path.read_text())
            
            # 2. 模拟构建耗时（实际应调用 GitHub Actions API 或 Gradle CLI）
            await asyncio.sleep(5)  # 模拟构建过程
            
            # 3. 构建成功
            record.status = "success"
            record.apk_url = f"https://releases.example.com/huiyiapi/{build_id}/app-release.apk"
            record.completed_at = datetime.now().isoformat()
            
            logger.info(f"✅ 构建成功: {build_id}, APK: {record.apk_url}")
            
        except Exception as e:
            record.status = "failed"
            record.error_message = str(e)
            record.completed_at = datetime.now().isoformat()
            logger.error(f"❌ 构建失败: {build_id}, 错误: {e}")
    
    async def get_build_status(self, build_id: str) -> Optional[Dict[str, Any]]:
        """获取构建状态"""
        record = self._builds.get(build_id)
        if record:
            return record.to_dict()
        return None
    
    async def get_all_builds(self) -> List[Dict[str, Any]]:
        """获取所有构建记录"""
        return [r.to_dict() for r in self._builds.values()]
