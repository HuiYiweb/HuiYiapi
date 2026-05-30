"""APK 下载二维码生成"""
import logging
logger = logging.getLogger("huiyi_plugin.qrcode")

def generate_qrcode(url: str, output_path: str) -> bool:
    try:
        import qrcode
        img = qrcode.make(url)
        img.save(output_path)
        return True
    except ImportError:
        logger.warning("qrcode 库未安装")
        return False
    except Exception as e:
        logger.error(f"二维码生成失败: {e}")
        return False
