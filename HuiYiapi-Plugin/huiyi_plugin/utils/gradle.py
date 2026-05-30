"""Gradle CLI 封装"""
import subprocess, logging
logger = logging.getLogger("huiyi_plugin.gradle")

def build_apk(project_dir: str, variant: str = "release") -> bool:
    try:
        cmd = ["./gradlew", f"assemble{variant.capitalize()}"]
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=1800)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Gradle 构建异常: {e}")
        return False
