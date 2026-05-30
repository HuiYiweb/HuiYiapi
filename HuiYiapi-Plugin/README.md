# HuiYiapi — 手机消息桥接与语音处理插件

通过 OneBot v11 协议将手机即时通讯消息接入 AstrBot，支持多设备管理、语音/视频通话实时处理、一键构建定制 APK。

## 功能

- 📱 多设备同时管理（单实例，无限设备）
- 🔗 OneBot v11 反向 WebSocket 连接
- 🎤 实时语音识别（ASR）+ 语音合成（TTS）
- 📞 通话自动接听与 AI 代接
- 🔧 MCP 工具集（30+ 设备操控 + UI 自动化）
- 📦 一键构建定制 Android APK

## Web API

| 路由 | 方法 | 说明 |
|------|------|------|
| `/huiyiapi/devices` | GET | 获取设备列表 |
| `/huiyiapi/devices` | POST | 添加设备 |
| `/huiyiapi/connections` | GET | 获取连接状态 |
| `/huiyiapi/builds` | GET | 获取构建记录 |

## 配套组件

- **HuiYiapi-Bridge**: Python 云桥接器（WebSocket + OneBot v11 + MCP）
- **HuiYiapi-Android**: Android App（Kotlin + Jetpack Compose）
