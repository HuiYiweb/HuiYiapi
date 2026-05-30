"""APK 签名工具"""
import subprocess
import logging

logger = logging.getLogger("huiyi_plugin.signer")

def sign_apk(apk_path: str, keystore: str, alias: str, password: str) -> bool:
    try:
        cmd = [
            "apksigner", "sign",
            "--ks", keystore,
            "--ks-key-alias", alias,
            "--ks-pass", f"pass:{password}",
            apk_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"APK 签名失败: {e}")
        return False
