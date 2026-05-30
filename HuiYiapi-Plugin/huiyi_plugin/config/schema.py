"""Pydantic 配置模型"""
from pydantic import BaseModel, Field
from typing import Optional

class PluginConfig(BaseModel):
    bridge_default_url: str = Field(default="ws://localhost:8765")
    heartbeat_interval: int = Field(default=30)
    heartbeat_timeout: int = Field(default=90)
    enable_auto_build: bool = Field(default=False)
    github_token: Optional[str] = Field(default=None)
    build_repo_url: str = Field(default="https://github.com/your-org/HuiYiapi-Android")
