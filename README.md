# 🌙 HuiYiapi — 手机消息桥接 + OneBot v11 + MCP + 语音/视频通话处理

**HuiYiapi** 是一套完整的「手机 ↔ AI」桥接系统，包含三个核心组件：
- 📱 **Android App** — 仿 iOS 风格，消息监听/发送/设备操控/实时通话处理
- ☁️ **Bridge Server** — Python 云桥接器，WebSocket + OneBot v11 + MCP
- 🤖 **AstrBot 插件** — 单实例多设备管理 + 一键构建 APK

---

## 🏗️ 项目结构

```
HuiYiapi/
├── HuiYiapi-Android/           # Android App (Kotlin + Jetpack Compose)
│   ├── build.gradle.kts
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── java/com/huiyi/api/
│   │       │   ├── core/network/       # WebSocket 连接管理
│   │       │   ├── service/            # 无障碍/通知监听/保活服务
│   │       │   ├── device/             # 设备操控 (点击/滑动/UI树)
│   │       │   ├── speech/             # ASR + TTS 音频管线
│   │       │   ├── call/               # 通话管理
│   │       │   ├── ui/theme/           # iOS 风格主题
│   │       │   ├── ui/components/      # iOS 风格组件
│   │       │   └── ui/screens/         # 主界面
│   │       └── res/
│   └── .github/workflows/build.yml     # GitHub Actions 构建 APK
│
├── HuiYiapi-Bridge/            # Python 桥接器
│   ├── config.yaml
│   ├── requirements.txt
│   └── src/huiyi_bridge/
│       └── bridge_server.py            # 单文件实现
│
└── HuiYiapi-Plugin/            # AstrBot 插件
    ├── metadata.yaml
    ├── requirements.txt
    └── huiyi_plugin/
        ├── main.py                     # 插件入口
        ├── device/                     # 多设备管理
        ├── apk_builder/                # APK 构建
        └── commands/                   # 命令处理
```

## 🚀 快速开始

### 1. 启动桥接器
```bash
cd HuiYiapi-Bridge
pip install -r requirements.txt
python src/huiyi_bridge/bridge_server.py --port 8765 --onebot-url ws://astrbot:6700/
```

### 2. 安装 AstrBot 插件
将 `HuiYiapi-Plugin/` 目录放入 AstrBot 的 `plugins/` 目录，重启 AstrBot。

### 3. 安装 Android App
通过插件 Web 管理面板的「一键构建」生成定制 APK，或直接编译：
```bash
cd HuiYiapi-Android
./gradlew assembleRelease
```

### 4. 连接手机
1. 打开 App，完成首次引导
2. 授予通知监听 + 无障碍服务权限
3. 填写桥接器地址 → 点击连接

## 🔧 核心功能

| 功能 | Android App | Bridge Server | AstrBot 插件 |
|------|:--:|:--:|:--:|
| 消息监听 (通知栏) | ✅ | — | — |
| 消息发送 (无障碍) | ✅ | — | — |
| WebSocket 长连接 | ✅ | ✅ | — |
| OneBot v11 协议 | — | ✅ | ✅ |
| MCP 工具 (30+) | — | ✅ | — |
| UI 自动化 (mcp_for_android) | ✅ | ✅ | — |
| 屏幕截图/操控 | ✅ | ✅ | — |
| 实时语音识别 (ASR) | ✅ | ✅ | — |
| 语音合成 (TTS) | ✅ | ✅ | — |
| 通话自动接听 | ✅ | ✅ | — |
| 多设备管理 | — | ✅ | ✅ |
| 一键构建 APK | — | — | ✅ |

## 📦 MCP 工具清单

桥接器暴露 30+ MCP 工具，涵盖：

**设备操控** (phoneMcp 能力)：
`screenshot`, `tap`, `swipe`, `double_tap`, `long_press`, `press_key`, `type_text`, `open_app`, `close_app`, `get_clipboard`, `set_clipboard`, `get_device_info`, `get_sensors`, `exec_shell`, `get_installed_apps`, `get_current_activity`, `get_location`, `send_phone_message`

**UI 自动化** (mcp_for_android 能力)：
`get_ui_tree`, `find_and_click`, `find_and_set_text`, `scroll_to_find`, `scroll`, `ui_press`, `back`, `home`

**通话控制**：
`start_call_capture`, `stop_call_capture`, `send_tts_text`, `set_asr_model`, `set_tts_model`, `answer_call`, `hangup_call`

## 📄 许可证

MIT License
