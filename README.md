<p align="center">
  <img src="internal/icon.png" alt="Scrcpy Ultra Launcher" width="128">
</p>

<h1 align="center">Scrcpy Ultra Launcher</h1>

<p align="center">
  <strong>为 Scrcpy 打造的现代化图形界面启动器</strong><br>
  <em>A Modern GUI Launcher for Scrcpy</em>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Genymobile/scrcpy"><img src="https://img.shields.io/badge/Scrcpy-v2.0%2B-4CAF50?logo=android&logoColor=white" alt="Scrcpy"></a>
  <a href="https://github.com/TomSchimansky/CustomTkinter"><img src="https://img.shields.io/badge/GUI-CustomTkinter-FF6F00" alt="CustomTkinter"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/2K%20%7C%20120FPS-Supported-success" alt="2K 120FPS">
</p>

---

## 📖 简介

**Scrcpy Ultra Launcher** 是一个为 [Scrcpy](https://github.com/Genymobile/scrcpy) 量身打造的现代化 GUI 启动器。

它旨在解决 Scrcpy 命令行操作门槛高、参数记忆繁琐的问题，通过直观的图形界面和智能的硬件检测算法，让用户能够一键享受 **2K 分辨率**、**120Hz 高刷**的极致投屏体验。

> **⚠️ 声明 / Disclaimer**
>
> 本项目**并非** Scrcpy 官方项目。它仅仅是一个**图形界面启动器 (GUI Wrapper)**，核心投屏功能完全依赖于 [Genymobile/scrcpy](https://github.com/Genymobile/scrcpy)。
>
> *This project is a GUI wrapper, NOT scrcpy itself. All mirroring features are powered by Genymobile/scrcpy.*

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🚀 **零感启动** | 双击即进入配置界面，投屏开始后自动变身为监控日志 |
| 🎛️ **可视化参数** | 告别命令行！下拉菜单调整分辨率、帧率、码率、编码格式 |
| 🔌 **智能热插拔** | USB 设备即插即用，自动识别和刷新，无需手动操作 |
| 📡 **一键无线** | 内置无线向导，自动解析手机 IP 并开启 TCP/IP 模式 |
| 🧠 **智能推荐** | 根据 PC 内存和手机物理分辨率，自动推荐最佳配置 |
| 📝 **实时日志** | 投屏过程中实时显示 FPS、丢包率、错误信息 |
| 🌍 **多语言** | 支持 中文 / English 实时切换 |
| 🎨 **暗色主题** | 现代化 Dark Mode UI，护眼舒适 |

### 支持的参数选项

- **分辨率**: Native / 2K (2560) / 1080P (1920) / 720P (1280)
- **帧率**: 120 fps / 90 fps / 60 fps / 30 fps
- **编码**: H.264 (低延迟) / H.265 (高画质)
- **码率**: 4-40 Mbps 可调
- **其他**: 启动即熄屏、无线连接、设备断开

---

## 📦 安装部署

本项目采用 **"狸猫换太子"** 部署方式，无缝替换原版 Scrcpy 入口。

### 快速安装

1. 下载 [Scrcpy 官方原版](https://github.com/Genymobile/scrcpy/releases) (v2.0+) 并解压
2. 进入 Scrcpy 目录，将 `scrcpy.exe` **重命名**为 `scrcpy-core.exe`
3. 下载本项目的 `scrcpy.exe`（使用 PyInstaller 打包 `main.py` 生成），放入同一目录
4. 双击 `scrcpy.exe` 即可使用！

### 目录结构

```
Scrcpy-Folder/
├── scrcpy.exe           ← 本启动器 (GUI Launcher)
├── scrcpy-core.exe      ← 原版核心程序 (重命名后)
├── scrcpy-server        ← Scrcpy 服务端
├── adb.exe              ← Android Debug Bridge
├── icon.ico             ← 程序图标 (可选)
├── config.json          ← 用户配置 (自动生成)
├── *.dll                ← 依赖库
└── ...
```

---

## 🔄 Scrcpy 官方版本升级

> **本启动器与 Scrcpy 官方版本完全解耦，支持无痛升级！**

当 Scrcpy 官方发布新版本时，您只需：

1. 下载最新版 [Scrcpy Release](https://github.com/Genymobile/scrcpy/releases)
2. 解压并将 **新版 `scrcpy.exe` 重命名为 `scrcpy-core.exe`**
3. 用新文件**覆盖**旧目录中的 `scrcpy-core.exe`、`scrcpy-server`、`adb.exe` 及相关 DLL
4. 保留本启动器的 `scrcpy.exe`(也可以使用PyInstaller重新打包main.py) 和 `config.json` **不动**
5. 完成！启动器会自动调用新版核心

**原理**：本启动器仅负责 GUI 界面和参数组装，实际投屏功能由 `scrcpy-core.exe` 执行。两者通过命令行参数通信，无版本耦合。

---

## 🛠️ 开发构建

如果你想修改代码或自行编译，请按以下步骤操作。

### 环境要求

- Python 3.10+
- Windows 10/11

### 1. 安装依赖

```bash
pip install customtkinter packaging pillow psutil pyinstaller
```

### 2. 开发环境运行

```bash
# 确保目录中已有 scrcpy-core.exe (重命名后的原版)
python main.py
```

### 3. 打包构建

```bash
python -m PyInstaller --noconsole --onefile --icon=icon.ico --name=scrcpy --add-data "icon.ico;." main.py
```

打包完成后，将 `dist/scrcpy.exe` 复制到 Scrcpy 目录即可。

### 项目结构

```
Scrcpy-Ultra-Launcher/
├── main.py              # 主程序入口
├── icon.ico             # 程序图标
├── config.json          # 用户配置文件
├── README.md            # 说明文档
├── scrcpy.spec          # PyInstaller 配置
└── internal/            # 内部资源目录
    ├── icon.png         # PNG 图标 (用于 README)
    ├── scrcpy-core.exe  # Scrcpy 核心程序
    └── ...
```

---

## 🎯 使用指南

### 有线连接

1. USB 连接手机，开启 **USB 调试**
2. 启动程序，等待设备自动识别
3. 选择设备，调整参数
4. 点击 **▶ 开始投屏**

### 无线连接

1. 首先用 USB 连接一次手机
2. 点击 **📶 无线连接** 按钮
3. 程序自动检测 IP 并开启 TCP/IP 模式
4. 连接成功后即可拔掉 USB 线！

### 参数推荐

| 场景 | 分辨率 | 帧率 | 码率 | 编码 |
|------|--------|------|------|------|
| 普通使用 | 1080P | 60 fps | 10M | H.264 |
| 游戏投屏 | 1080P | 120 fps | 20M | H.264 |
| 高清演示 | 2K | 60 fps | 20M | H.265 |
| 低延迟 | 720P | 60 fps | 8M | H.264 |

---

## ❓ 常见问题

<details>
<summary><b>Q: 提示找不到 scrcpy-core.exe？</b></summary>

请确保已将原版 `scrcpy.exe` 重命名为 `scrcpy-core.exe`。
</details>

<details>
<summary><b>Q: 设备显示"未授权"？</b></summary>

请在手机上允许 USB 调试授权弹窗，勾选"始终允许"。
</details>

<details>
<summary><b>Q: 无线连接失败？</b></summary>

1. 确保手机和电脑在同一 WiFi 网络
2. 首次需要用 USB 连接一次来开启 TCP/IP 模式
3. 检查防火墙是否阻止了 5555 端口
</details>

<details>
<summary><b>Q: 投屏画面卡顿？</b></summary>

1. 降低分辨率或帧率
2. 使用 H.264 编码（延迟更低）
3. 使用 USB 连接代替无线
</details>

---

## 🤝 致谢

- **[Genymobile/scrcpy](https://github.com/Genymobile/scrcpy)** - 强大的投屏核心引擎
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - 现代化 Python GUI 框架
- **[psutil](https://github.com/giampaolo/psutil)** - 系统硬件检测库

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  <sub>Made with ❤️ for the Android community</sub>
</p>
