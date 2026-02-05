"""
Scrcpy Ultra Launcher - A modern launcher for scrcpy
Built with CustomTkinter for a sleek dark mode UI
"""

import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_base_path() -> str:
    """获取外部依赖文件的基础路径。
    
    用于定位 scrcpy-core.exe, adb.exe, config.json 等外部文件。
    - PyInstaller 打包后: 返回 EXE 所在目录
    - 开发环境: 返回脚本所在目录
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - return the EXE's directory
        return os.path.dirname(sys.executable)
    else:
        # Running as script - return the script's directory
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str = "") -> str:
    """获取内部资源文件的路径。
    
    用于定位 icon.ico 等通过 --add-data 打包进 EXE 的资源文件。
    - PyInstaller 打包后: 返回 sys._MEIPASS 临时解压目录
    - 开发环境: 返回脚本所在目录
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - resources are in temp directory
        base_path = sys._MEIPASS
    else:
        # Running as script - resources are alongside the script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    if relative_path:
        return os.path.join(base_path, relative_path)
    return base_path


class DeviceMonitor(threading.Thread):
    """Background thread to monitor USB device hotplug events via 'adb track-devices'."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.daemon = True  # Thread will exit when main program exits
        self._stop_event = threading.Event()
        self._process = None
        self._first_output = True  # Flag to ignore initial track-devices output
    
    def run(self):
        """Main loop: run 'adb track-devices' and trigger refresh on device changes."""
        # Get adb path from app
        adb_path = getattr(self.app, 'adb_path', 'adb')
        
        while not self._stop_event.is_set():
            try:
                # Start adb track-devices process
                self._process = subprocess.Popen(
                    [adb_path, "track-devices"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Reset first output flag for new process
                self._first_output = True
                
                # Read output line by line
                while not self._stop_event.is_set():
                    if self._process.poll() is not None:
                        # Process ended, restart it
                        break
                    
                    line = self._process.stdout.readline()
                    if line:  # Non-empty line means device state changed
                        # Skip the first output (initial device list)
                        if self._first_output:
                            self._first_output = False
                            continue
                        # Use after() to schedule refresh on main thread with debounce
                        self.app.after(0, self.app._schedule_refresh)
                
            except FileNotFoundError:
                # ADB not found, wait and retry
                time.sleep(5)
            except Exception as e:
                # Log error and retry
                print(f"[DeviceMonitor] Error: {e}")
                time.sleep(2)
            finally:
                if self._process:
                    try:
                        self._process.terminate()
                    except Exception:
                        pass
                    self._process = None
    
    def stop(self):
        """Stop the monitor thread."""
        self._stop_event.set()
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass


# Localization dictionary for multi-language support
LOCALE = {
    "window_title": {"zh": "Scrcpy Pro Controller", "en": "Scrcpy Pro Controller"},
    "device_label": {"zh": "选择设备:", "en": "Device:"},
    "scanning": {"zh": "正在扫描...", "en": "Scanning..."},
    "no_device": {"zh": "未检测到设备", "en": "No device found"},
    "refresh_btn": {"zh": "🔄 刷新", "en": "🔄 Refresh"},
    "wireless_btn": {"zh": "📶 无线连接", "en": "📶 Wireless"},
    "params_title": {"zh": "推流参数", "en": "STREAM PARAMETERS"},
    "lbl_resolution": {"zh": "最大分辨率 (Max Size)", "en": "Max Size"},
    "lbl_fps": {"zh": "帧率限制 (Max FPS)", "en": "Max FPS"},
    "lbl_codec": {"zh": "视频编码 (Codec)", "en": "Video Codec"},
    "lbl_bitrate": {"zh": "传输码率 (Bitrate)", "en": "Bitrate"},
    "screen_off": {"zh": "启动即熄屏", "en": "Turn Screen Off"},
    "screen_off_warning": {"zh": "⚠️ 若有锁屏密码，投屏可能无法显示解锁界面。\n     建议取消勾选，连接后按 LCtrl+O 熄屏。", "en": "⚠️ If you have a lock screen, the unlock UI may not display.\n     Recommend: uncheck this, then press LCtrl+O after connected."},
    "borderless": {"zh": "无边框模式", "en": "Borderless Mode"},
    "borderless_hint": {"zh": "💡 提示：已启用智能辅助。按住 Alt + 鼠标左键 即可自由拖动窗口。", "en": "💡 Tip: Smart assist enabled. Hold Alt + Left-click to drag window."},
    "show_log": {"zh": "显示运行日志", "en": "Show Log"},
    "print_fps": {"zh": "在日志中打印 FPS", "en": "Print FPS to Log"},
    "lbl_position": {"zh": "窗口位置 (Window Position)", "en": "Window Position"},
    "position_center": {"zh": "居中 (Center)", "en": "Center"},
    "position_top_left": {"zh": "左上角 (Top-Left)", "en": "Top-Left"},
    "position_top_right": {"zh": "右上角 (Top-Right)", "en": "Top-Right"},
    "start_btn": {"zh": "▶ 开始投屏", "en": "▶ START STREAM"},
    "log_title": {"zh": "运行日志", "en": "CONSOLE OUTPUT"},
    "wireless_title": {"zh": "无线连接向导", "en": "Wireless Setup"},
    "wireless_prompt": {"zh": "请输入手机 IP 地址:\n\n提示：请前往 手机设置 -> 关于手机 -> 状态信息 查看 IP", "en": "Enter phone IP address:\n\nTip: Go to Settings -> About Phone -> Status to find IP"},
    "wireless_success_title": {"zh": "无线连接成功", "en": "Wireless Connected"},
    "wireless_success_msg": {"zh": "已成功连接到 {target}\n\n您现在可以拔掉 USB 线了！", "en": "Successfully connected to {target}\n\nYou can unplug USB cable now!"},
    "auto_config_hint": {"zh": "✨ 已根据硬件 [{model} + {ram}GB RAM] 自动优化", "en": "✨ Auto-configured for [{model} + {ram}GB RAM]"},
    # Device name suffixes
    "device_wireless": {"zh": "无线", "en": "Wireless"},
    "device_unauthorized": {"zh": "未授权", "en": "Unauthorized"},
    # Log messages
    "log_found_devices": {"zh": "[INFO] 找到 {count} 台设备", "en": "[INFO] Found {count} device(s)"},
    "log_no_device": {"zh": "[WARN] 未检测到设备", "en": "[WARN] No devices found"},
    "log_refreshing": {"zh": "[INFO] 正在刷新设备列表...", "en": "[INFO] Refreshing device list..."},
    "log_getting_info": {"zh": "[INFO] 正在获取设备详细信息...", "en": "[INFO] Getting device details..."},
    "log_auto_select": {"zh": "[INFO] 已自动选择无线设备: {name}", "en": "[INFO] Auto-selected wireless device: {name}"},
    "log_connecting": {"zh": "[INFO] 正在连接 {target}...", "en": "[INFO] Connecting to {target}..."},
    "log_connected": {"zh": "[INFO] 已成功连接到 {target}", "en": "[INFO] Successfully connected to {target}"},
    "log_enabling_tcpip": {"zh": "[INFO] 正在对 {device} 启用 TCP/IP 模式...", "en": "[INFO] Enabling TCP/IP mode on {device}..."},
    "log_waiting_restart": {"zh": "[INFO] 等待 2 秒让设备重启 ADB...", "en": "[INFO] Waiting 2 seconds for device to restart ADB..."},
    "log_scrcpy_launched": {"zh": "[INFO] Scrcpy 启动成功！", "en": "[INFO] Scrcpy launched successfully!"},
    "log_scrcpy_exited": {"zh": "[INFO] Scrcpy 已正常退出。", "en": "[INFO] Scrcpy exited normally."},
    "log_no_valid_device": {"zh": "[ERROR] 未选择有效设备。", "en": "[ERROR] No valid device selected."},
    "log_ip_fallback": {"zh": "[WARN] 无法自动检测 IP，将使用手动输入。", "en": "[WARN] Failed to auto-detect IP, falling back to manual input."},
    "log_detected_ip": {"zh": "[INFO] 检测到设备 IP: {ip}", "en": "[INFO] Detected device IP: {ip}"},
    "log_adb_not_found": {"zh": "[ERROR] 未找到 ADB。请确保 adb.exe 在 PATH 环境变量中。", "en": "[ERROR] ADB not found. Please ensure adb.exe is in PATH."},
    "log_adb_timeout": {"zh": "[ERROR] ADB 命令超时。", "en": "[ERROR] ADB command timed out."},
    "log_scan_failed": {"zh": "[ERROR] 扫描设备失败: {e}", "en": "[ERROR] Failed to scan devices: {e}"},
    "log_tcpip_failed": {"zh": "[ERROR] 启用 TCP/IP 模式失败: {e}", "en": "[ERROR] Failed to enable TCP/IP mode: {e}"},
    "log_connect_failed_output": {"zh": "[WARN] 连接可能失败: {output}", "en": "[WARN] Connection may have failed: {output}"},
    "log_connect_timeout": {"zh": "[ERROR] 连接超时。请检查 IP 是否正确。", "en": "[ERROR] Connection timed out. Check if the IP is correct."},
    "log_connect_exception": {"zh": "[ERROR] 连接失败: {e}", "en": "[ERROR] Failed to connect: {e}"},
    "log_scrcpy_not_found": {"zh": "[ERROR] scrcpy-core.exe 未找到: {path}", "en": "[ERROR] scrcpy-core.exe not found at: {path}"},
    "log_launch_failed": {"zh": "[ERROR] Scrcpy 启动失败: {e}", "en": "[ERROR] Failed to launch scrcpy: {e}"},
    "log_scrcpy_exit_code": {"zh": "[WARN] Scrcpy 异常退出，代码: {code}", "en": "[WARN] Scrcpy exited with code: {code}"},
    "log_read_error": {"zh": "[ERROR] 读取 Scrcpy 输出时出错: {e}", "en": "[ERROR] Error reading scrcpy output: {e}"},
    "log_autoconfig_device": {"zh": "设备", "en": "Device"},
    "log_autoconfig_screen": {"zh": "屏幕", "en": "Screen"},
    "log_autoconfig_recommend": {"zh": "[AutoConfig] 推荐", "en": "[AutoConfig] Recommended"},
    # Disconnect device
    "disconnect_btn": {"zh": "✕", "en": "✕"},
    "log_disconnected_wireless": {"zh": "[INFO] 已断开无线设备连接: {device}", "en": "[INFO] Disconnected wireless device: {device}"},
    "log_disconnect_failed": {"zh": "[ERROR] 断开设备失败: {e}", "en": "[ERROR] Failed to disconnect device: {e}"},
    "log_usb_cannot_disconnect": {"zh": "[WARN] USB 设备无法手动断开，请直接拔掉数据线。", "en": "[WARN] USB devices cannot be disconnected manually. Please unplug the cable."},
    "log_no_device_to_disconnect": {"zh": "[WARN] 未选择有效设备。", "en": "[WARN] No valid device selected."},
    "log_attempting_disconnect": {"zh": "[INFO] 正在断开设备: {device}...", "en": "[INFO] Disconnecting device: {device}..."},
    # Clear logs button
    "clear_logs_btn": {"zh": "清空日志", "en": "Clear Logs"},
    # Wireless first-time hint
    "wireless_first_time_title": {"zh": "首次无线连接提示", "en": "First-time Wireless Connection"},
    "wireless_first_time_msg": {"zh": "未检测到设备。\n\n首次无线连接有两种方式：\n\n① 使用 USB 线连接手机，程序会自动获取 IP 并连接\n\n② 如果已知手机 IP 地址，点击「是」手动输入", "en": "No device detected.\n\nFor first-time wireless connection:\n\n① Connect via USB - the app will auto-detect IP\n\n② If you know the device IP, click 'Yes' to enter manually"},
    "wireless_first_time_ask_manual": {"zh": "是否手动输入设备 IP 地址？", "en": "Would you like to enter the device IP manually?"},
    # Wireless device management (from dropdown)
    "history_menu_title": {"zh": "无线设备管理", "en": "Wireless Device Management"},
    "history_delete_btn": {"zh": "断开", "en": "Disconnect"},
    "history_delete_confirm_title": {"zh": "确认断开", "en": "Confirm Disconnect"},
    "history_delete_confirm_msg": {"zh": "确定要断开无线设备 '{device}' 吗？", "en": "Are you sure you want to disconnect '{device}'?"},
    "history_deleted": {"zh": "[INFO] 已断开无线设备: {device}", "en": "[INFO] Disconnected wireless device: {device}"},
    "history_empty": {"zh": "当前没有已连接的无线设备\n\n通过「无线连接」按钮添加设备", "en": "No wireless devices connected\n\nUse the 'Wireless' button to connect devices"},
    "history_clear_all": {"zh": "断开所有无线设备", "en": "Disconnect All"},
    "history_cleared": {"zh": "[INFO] 已断开所有无线设备", "en": "[INFO] All wireless devices disconnected"},
}

# Tutorial content pages
TUTORIAL_PAGES = [
    {
        "title": "📡 连接模式概览",
        "content": """1. 有线模式 (USB):
无需网络，延迟最低，画质最高。
只需用数据线连接电脑，并开启 USB 调试即可。

2. 无线模式 (Wi-Fi):
需要手机和电脑在同一 Wi-Fi 下。
摆脱线缆束缚，适合日常轻度使用。"""
    },
    {
        "title": "🛠️ 准备工作",
        "content": """如何开启 USB 调试?

1. 手机设置 → 关于手机 → 连续点击 7 次【版本号】开启开发者模式。

2. 返回设置 → 开发者选项 → 开启【USB 调试】。

3. 连接电脑后，手机上弹出授权框，请点击【允许】。"""
    },
    {
        "title": "📶 无线投屏步骤",
        "content": """首次连接需要插线:

1. 先插上 USB 线，确保有线连接成功。

2. 点击软件顶部的【无线连接】按钮。

3. 等待提示成功后，拔掉数据线即可。

注意：如果失败，请检查两者是否在同一 Wi-Fi 网络。"""
    },
    {
        "title": "⌨️ 快捷键与技巧",
        "content": """常用快捷键 (已改为左Ctrl以避免冲突):

• 左Ctrl + F: 全屏模式
• 左Ctrl + P: 点亮/关闭屏幕
• 左Ctrl + H: 返回桌面 (Home)
• Alt + 左键: 拖动无边框窗口

智能辅助:
软件已内置窗口增强引擎 (AltSnap)，
现在您可以在 Windows 上享受 Linux 级的窗口管理体验。"""
    }
]


class TutorialPopup(ctk.CTkToplevel):
    """Startup tutorial popup with multi-page content."""
    
    def __init__(self, parent, on_close_callback=None):
        super().__init__(parent)
        
        self.parent = parent
        self.on_close_callback = on_close_callback
        self.current_page = 0
        self.total_pages = len(TUTORIAL_PAGES)
        
        # Window setup
        self.title("Scrcpy 使用向导")
        self.geometry("520x420")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.configure(fg_color="#1A1A1A")
        
        # Center on screen
        self.transient(parent)
        self.grab_set()
        
        # Calculate center position
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 420) // 2
        self.geometry(f"520x420+{x}+{y}")
        
        # Create UI
        self._create_widgets()
        self._update_content()
        
        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """Create all tutorial popup widgets."""
        # Main container with padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=25, pady=20)
        
        # Header - Welcome title
        self.header_label = ctk.CTkLabel(
            main_frame,
            text="欢迎使用 Scrcpy Ultra",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#FFFFFF"
        )
        self.header_label.pack(pady=(0, 5))
        
        # Page title
        self.page_title = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#00BFFF"
        )
        self.page_title.pack(pady=(10, 10))
        
        # Content area
        self.content_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#2B2B2B",
            corner_radius=10,
            border_width=1,
            border_color="#444444"
        )
        self.content_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        self.content_label = ctk.CTkLabel(
            self.content_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="#E0E0E0",
            justify="left",
            anchor="nw",
            wraplength=440
        )
        self.content_label.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Page indicator
        self.page_indicator = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        self.page_indicator.pack(pady=(0, 10))
        
        # Bottom navigation bar
        nav_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        nav_frame.pack(fill="x")
        
        # Left side: "Don't show again" checkbox
        self.dont_show_var = ctk.BooleanVar(value=False)
        self.dont_show_checkbox = ctk.CTkCheckBox(
            nav_frame,
            text="下次不再显示",
            variable=self.dont_show_var,
            font=ctk.CTkFont(size=13),
            fg_color="#00BFFF",
            hover_color="#4169E1",
            text_color="#AAAAAA",
            checkbox_width=20,
            checkbox_height=20
        )
        self.dont_show_checkbox.pack(side="left")
        
        # Right side: Navigation buttons
        btn_frame = ctk.CTkFrame(nav_frame, fg_color="transparent")
        btn_frame.pack(side="right")
        
        self.prev_btn = ctk.CTkButton(
            btn_frame,
            text="◀ 上一页",
            width=90,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3A3A3A",
            hover_color="#4A4A4A",
            corner_radius=8,
            command=self._prev_page
        )
        self.prev_btn.pack(side="left", padx=(0, 8))
        
        self.next_btn = ctk.CTkButton(
            btn_frame,
            text="下一页 ▶",
            width=90,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0078D4",
            hover_color="#106EBE",
            corner_radius=8,
            command=self._next_page
        )
        self.next_btn.pack(side="left", padx=(0, 8))
        
        self.close_btn = ctk.CTkButton(
            btn_frame,
            text="关闭",
            width=70,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#DC3545",
            hover_color="#C82333",
            corner_radius=8,
            command=self._on_close
        )
        self.close_btn.pack(side="left")
    
    def _update_content(self):
        """Update displayed content based on current page."""
        page = TUTORIAL_PAGES[self.current_page]
        
        self.page_title.configure(text=page["title"])
        self.content_label.configure(text=page["content"])
        self.page_indicator.configure(text=f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页")
        
        # Update button states
        if self.current_page == 0:
            self.prev_btn.configure(state="disabled", fg_color="#2A2A2A")
        else:
            self.prev_btn.configure(state="normal", fg_color="#3A3A3A")
        
        if self.current_page == self.total_pages - 1:
            self.next_btn.configure(text="✓ 完成", fg_color="#28A745", hover_color="#218838")
        else:
            self.next_btn.configure(text="下一页 ▶", fg_color="#0078D4", hover_color="#106EBE")
    
    def _prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_content()
    
    def _next_page(self):
        """Go to next page or finish."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_content()
        else:
            # Last page, treat as finish
            self._on_close()
    
    def _on_close(self):
        """Handle close/finish action."""
        dont_show = self.dont_show_var.get()
        
        if self.on_close_callback:
            self.on_close_callback(dont_show)
        
        self.destroy()


class AutoConfig:
    """Smart hardware-based configuration recommender."""
    
    @staticmethod
    def get_pc_ram_gb() -> int:
        """Get PC RAM size in GB."""
        if not PSUTIL_AVAILABLE:
            return 8  # Default fallback
        try:
            ram_bytes = psutil.virtual_memory().total
            return int(ram_bytes / (1024 ** 3))
        except Exception:
            return 8
    
    @staticmethod
    def get_device_screen_size(serial: str, adb_path: str = "adb") -> tuple[int, int] | None:
        """Get device physical screen size via ADB.
        
        Returns (width, height) or None if failed.
        """
        try:
            result = subprocess.run(
                [adb_path, "-s", serial, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # Parse output like "Physical size: 3008x1880"
            output = result.stdout.strip()
            match = re.search(r'Physical size:\s*(\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
            # Fallback to override size or first line
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_device_model(serial: str, adb_path: str = "adb") -> str:
        """Get device model name for display."""
        try:
            result = subprocess.run(
                [adb_path, "-s", serial, "shell", "getprop", "ro.product.model"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip() or "Unknown"
        except Exception:
            return "Unknown"
    
    @classmethod
    def generate_recommendation(cls, serial: str, adb_path: str = "adb") -> dict:
        """Generate recommended settings based on hardware.
        
        Returns dict with: resolution, fps, bitrate, codec, device_model, pc_ram
        """
        # Get hardware info
        pc_ram = cls.get_pc_ram_gb()
        screen_size = cls.get_device_screen_size(serial, adb_path)
        device_model = cls.get_device_model(serial, adb_path)
        
        # Determine max screen dimension
        max_dimension = 0
        if screen_size:
            max_dimension = max(screen_size)
        
        # Resolution recommendation
        if max_dimension > 2500 and pc_ram >= 16:
            resolution = "2K (2560)"
            bitrate = 20
        else:
            resolution = "1080P (1920)"
            bitrate = 10
        
        # Default recommendations
        fps = "60 fps"
        codec = "H.264 (Low Latency)"  # More stable
        
        return {
            "resolution": resolution,
            "fps": fps,
            "bitrate": bitrate,
            "codec": codec,
            "device_model": device_model,
            "pc_ram": pc_ram,
            "screen_size": screen_size
        }


class ScrcpyLauncher(ctk.CTk):
    """Main application window for Scrcpy Ultra Launcher."""
    
    # Path to scrcpy core executable (renamed from scrcpy.exe to avoid recursion)
    SCRCPY_EXE = "scrcpy-core.exe"
    
    # Config file for saving user preferences
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        # Set Windows AppUserModelID for proper taskbar icon display
        # This must be done BEFORE creating the window
        try:
            app_id = "ScrcpyUltraLauncher.GUI.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass  # Silently fail on non-Windows platforms
        
        super().__init__()
        
        # Store the base directory for external dependencies
        # For PyInstaller: this is the EXE's directory (not the temp extraction directory)
        self.app_dir = get_base_path()
        
        # New directory structure: dependencies moved to subdirectories
        self.internal_dir = os.path.join(self.app_dir, "internal")
        self.tools_dir = os.path.join(self.internal_dir, "tools")
        
        # Core executable paths
        self.scrcpy_path = os.path.join(self.internal_dir, self.SCRCPY_EXE)
        self.adb_path = os.path.join(self.internal_dir, "adb.exe")
        
        # Pre-set icon path and load icon early (before any UI changes)
        self.icon_path = None
        try:
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.icon_path = icon_path
                self.iconbitmap(self.icon_path)
        except Exception:
            pass
        
        self._setup_window()
        self._create_variables()
        self._load_config()  # Load saved config before creating widgets
        self._create_widgets()
        self._layout_widgets()
        self._update_ui_text()  # Apply language after widgets are created
        
        # Perform initial device scan after UI is ready
        self.after(100, self._scan_devices)
        
        # Start device hotplug monitor thread
        self._start_device_monitor()
        
        # Start AltSnap for borderless window dragging (if available)
        self._ensure_altsnap_running()
        
        # Show tutorial popup for first-time users (1 second delay)
        self.after(1000, self._show_tutorial_if_needed)
        
        # Bind window close event to save config
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _setup_window(self) -> None:
        """Configure the main window properties."""
        self.title("Scrcpy Ultra Launcher")
        self.geometry("850x620")
        self.resizable(False, False)
        
        # Set window icon if available
        self._set_window_icon()
        
        # Center the window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 850) // 2
        y = (self.winfo_screenheight() - 620) // 2
        self.geometry(f"850x620+{x}+{y}")
    
    def _set_window_icon(self) -> None:
        """Set window icon from icon.ico or icon.png if available.
        
        Icon files are bundled INSIDE the EXE via --add-data,
        so we use get_resource_path() to locate them in sys._MEIPASS.
        """
        # Don't reset icon_path if already set in __init__
        if not hasattr(self, 'icon_path') or not self.icon_path:
            self.icon_path = None
        
        try:
            # Try .ico first (preferred for Windows)
            icon_path = get_resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.icon_path = icon_path  # Save for later use
                self.iconbitmap(icon_path)
                # Also set using wm_iconbitmap for better persistence
                self.wm_iconbitmap(default=icon_path)
                return
            
            # Try .png as fallback
            png_path = get_resource_path("icon.png")
            if os.path.exists(png_path):
                from PIL import Image, ImageTk
                img = Image.open(png_path)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._icon_photo = photo  # Keep reference to prevent garbage collection
                self.icon_path = png_path  # Save for later use (though .png uses different method)
                return
            
            print("[INFO] No icon file found (icon.ico or icon.png)")
            
        except Exception as e:
            # Icon setting is optional, just log and continue
            print(f"[INFO] Could not set window icon: {e}")
    
    def _create_variables(self) -> None:
        """Initialize tkinter variables for UI state."""
        self.selected_device = ctk.StringVar(value="Scanning...")
        self.screen_off_on_start = ctk.BooleanVar(value=False)
        self.borderless_mode = ctk.BooleanVar(value=False)
        self.window_position = ctk.StringVar(value="center")  # center, top-left, top-right
        self.show_log_on_start = ctk.BooleanVar(value=True)  # Show log window or hide GUI
        self.print_fps = ctk.BooleanVar(value=False)  # Print real-time FPS
        
        # Silent mode process tracking
        self.current_scrcpy_process = None
        
        # Stream parameters
        self.param_resolution = ctk.StringVar(value="1080P (1920)")
        self.param_fps = ctk.StringVar(value="60 fps")
        self.param_bitrate = ctk.IntVar(value=16)
        self.param_codec = ctk.StringVar(value="H.264 (Low Latency)")
        
        # Track available devices
        self.available_devices: list[str] = []
        
        # Auto-config state
        self._auto_config_applied = False
        
        # Language setting
        self.current_lang = "zh"
        self.language_var = ctk.StringVar(value="中文")
        
        # Hotplug detection debounce
        self._refresh_scheduled = None  # Stores the after() ID for debounce
        self._device_monitor = None  # Device monitor thread
    
    def _create_widgets(self) -> None:
        """Create all UI widgets."""
        # Create main container frames for layout control
        self.setup_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.log_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self._create_top_section()
        self._create_middle_section()
        self._create_bottom_section()
        self._create_log_section()

    def _create_top_section(self) -> None:
        """Create the device selection section."""
        self.top_frame = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        self.device_label = ctk.CTkLabel(
            self.top_frame,
            text="选择设备:",
            font=ctk.CTkFont(size=16)
        )
        
        self.device_dropdown = ctk.CTkComboBox(
            self.top_frame,
            variable=self.selected_device,
            values=["Scanning..."],
            width=300,
            height=38,
            font=ctk.CTkFont(size=14),
            fg_color="#2B2B2B",
            border_color="#444444",
            button_color="#444444",
            dropdown_fg_color="#2B2B2B",
            state="readonly"
        )

        
        # Refresh button - modern style
        self.refresh_button = ctk.CTkButton(
            self.top_frame,
            text="↻ 刷新",
            width=80,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0078D4",
            hover_color="#106EBE",
            corner_radius=8,
            command=self._on_refresh_clicked
        )
        
        # Wireless connect button - modern style
        self.wireless_button = ctk.CTkButton(
            self.top_frame,
            text="⚡ 无线连接",
            width=100,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5C6BC0",
            hover_color="#3F51B5",
            corner_radius=8,
            command=self._on_wireless_clicked
        )
        
        # Disconnect button - compact icon
        self.history_button = ctk.CTkButton(
            self.top_frame,
            text="✕",
            width=34,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#3A3A3A",
            hover_color="#DC3545",
            corner_radius=8,
            command=self._show_history_management_dialog
        )
        
        # Language selector - modern compact style
        self.language_menu = ctk.CTkOptionMenu(
            self.top_frame,
            variable=self.language_var,
            values=["中文", "English"],
            width=85,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#2B2B2B",
            button_color="#3A3A3A",
            dropdown_fg_color="#2B2B2B",
            corner_radius=6,
            command=self._on_language_changed
        )
        
        # Help button - opens tutorial
        self.help_button = ctk.CTkButton(
            self.top_frame,
            text="?",
            width=30,
            height=30,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#3A3A3A",
            hover_color="#5C6BC0",
            corner_radius=6,
            command=self._show_tutorial_manual
        )
    
    def _create_middle_section(self) -> None:
        """Create the Stream Parameters panel."""
        # Main container frame
        self.middle_frame = ctk.CTkFrame(
            self.setup_frame,
            fg_color="#1A1A1A",
            corner_radius=12,
            border_width=1,
            border_color="#333333"
        )
        
        # Auto-config status label (hidden by default)
        self.auto_config_label = ctk.CTkLabel(
            self.middle_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#4CAF50"
        )
        
        # Section title
        self.params_title = ctk.CTkLabel(
            self.middle_frame,
            text="STREAM PARAMETERS",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#666666"
        )
        
        # Parameters container with grid layout - compact 3-column design
        self.params_container = ctk.CTkFrame(self.middle_frame, fg_color="transparent")
        
        # Configure 3 columns for compact layout
        self.params_container.grid_columnconfigure(0, weight=1)
        self.params_container.grid_columnconfigure(1, weight=1)
        self.params_container.grid_columnconfigure(2, weight=1)
        
        # Ultra-compact widget dimensions
        DROPDOWN_WIDTH = 160
        DROPDOWN_HEIGHT = 26
        LABEL_FONT_SIZE = 14
        LABEL_FONT_WEIGHT = "bold"
        LABEL_TEXT_COLOR = "#FFFFFF"  # Bright white for prominence
        CELL_PADX = 6
        CELL_PADY = 4
        
        # --- Row 0: Resolution, FPS, Codec ---
        # Resolution
        res_frame = ctk.CTkFrame(self.params_container, fg_color="transparent")
        res_frame.grid(row=0, column=0, padx=CELL_PADX, pady=CELL_PADY, sticky="ew")
        
        self.res_label = ctk.CTkLabel(
            res_frame,
            text="Max Size (最大分辨率)",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight=LABEL_FONT_WEIGHT),
            text_color=LABEL_TEXT_COLOR
        )
        self.res_label.pack(anchor="w")
        
        self.resolution_dropdown = ctk.CTkComboBox(
            res_frame,
            variable=self.param_resolution,
            values=["Native", "2K (2560)", "1080P (1920)", "720P (1280)"],
            width=DROPDOWN_WIDTH,
            height=DROPDOWN_HEIGHT,
            font=ctk.CTkFont(size=12),
            fg_color="#2B2B2B",
            border_color="#444444",
            button_color="#444444",
            dropdown_fg_color="#2B2B2B",
            state="readonly"
        )
        self.resolution_dropdown.pack(anchor="w", pady=(3, 0))
        
        # Frame Rate
        fps_frame = ctk.CTkFrame(self.params_container, fg_color="transparent")
        fps_frame.grid(row=0, column=1, padx=CELL_PADX, pady=CELL_PADY, sticky="ew")
        
        self.fps_label = ctk.CTkLabel(
            fps_frame,
            text="Max FPS (帧率限制)",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight=LABEL_FONT_WEIGHT),
            text_color=LABEL_TEXT_COLOR
        )
        self.fps_label.pack(anchor="w")
        
        self.fps_dropdown = ctk.CTkComboBox(
            fps_frame,
            variable=self.param_fps,
            values=["120 fps", "90 fps", "60 fps", "30 fps"],
            width=DROPDOWN_WIDTH,
            height=DROPDOWN_HEIGHT,
            font=ctk.CTkFont(size=12),
            fg_color="#2B2B2B",
            border_color="#444444",
            button_color="#444444",
            dropdown_fg_color="#2B2B2B",
            state="readonly"
        )
        self.fps_dropdown.pack(anchor="w", pady=(3, 0))
        
        # Codec
        codec_frame = ctk.CTkFrame(self.params_container, fg_color="transparent")
        codec_frame.grid(row=0, column=2, padx=CELL_PADX, pady=CELL_PADY, sticky="ew")
        
        self.codec_label = ctk.CTkLabel(
            codec_frame,
            text="Codec (视频编码)",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight=LABEL_FONT_WEIGHT),
            text_color=LABEL_TEXT_COLOR
        )
        self.codec_label.pack(anchor="w")
        
        self.codec_dropdown = ctk.CTkComboBox(
            codec_frame,
            variable=self.param_codec,
            values=["H.264 (Low Latency)", "H.265 (High Quality)"],
            width=DROPDOWN_WIDTH,
            height=DROPDOWN_HEIGHT,
            font=ctk.CTkFont(size=12),
            fg_color="#2B2B2B",
            border_color="#444444",
            button_color="#444444",
            dropdown_fg_color="#2B2B2B",
            state="readonly"
        )
        self.codec_dropdown.pack(anchor="w", pady=(3, 0))
        
        # --- Row 1: Bitrate, Position ---
        # Bitrate (spans 2 columns for slider width)
        bitrate_frame = ctk.CTkFrame(self.params_container, fg_color="transparent")
        bitrate_frame.grid(row=1, column=0, columnspan=2, padx=CELL_PADX, pady=CELL_PADY, sticky="ew")
        
        bitrate_header = ctk.CTkFrame(bitrate_frame, fg_color="transparent")
        bitrate_header.pack(fill="x")
        
        self.bitrate_label = ctk.CTkLabel(
            bitrate_header,
            text="Bitrate (传输码率):",
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight=LABEL_FONT_WEIGHT),
            text_color=LABEL_TEXT_COLOR
        )
        self.bitrate_label.pack(side="left")
        
        self.bitrate_value_label = ctk.CTkLabel(
            bitrate_header,
            text=f"{self.param_bitrate.get()} Mbps",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00BFFF"
        )
        self.bitrate_value_label.pack(side="left", padx=(6, 0))
        
        self.bitrate_slider = ctk.CTkSlider(
            bitrate_frame,
            from_=4,
            to=40,
            number_of_steps=36,
            variable=self.param_bitrate,
            width=340,
            height=12,
            fg_color="#333333",
            progress_color="#00BFFF",
            button_color="#00BFFF",
            button_hover_color="#4169E1",
            command=self._on_bitrate_change
        )
        self.bitrate_slider.pack(anchor="w", pady=(3, 0))
        
        # Window Position
        position_frame = ctk.CTkFrame(self.params_container, fg_color="transparent")
        position_frame.grid(row=1, column=2, padx=CELL_PADX, pady=CELL_PADY, sticky="ew")
        
        self.position_label = ctk.CTkLabel(
            position_frame,
            text=LOCALE["lbl_position"][self.current_lang],
            font=ctk.CTkFont(size=LABEL_FONT_SIZE, weight=LABEL_FONT_WEIGHT),
            text_color=LABEL_TEXT_COLOR
        )
        self.position_label.pack(anchor="w")
        
        # Position values: internal value -> display text
        self._position_values = {
            "center": LOCALE["position_center"][self.current_lang],
            "top-left": LOCALE["position_top_left"][self.current_lang],
            "top-right": LOCALE["position_top_right"][self.current_lang]
        }
        
        self.position_menu = ctk.CTkComboBox(
            position_frame,
            values=list(self._position_values.values()),
            width=DROPDOWN_WIDTH,
            height=DROPDOWN_HEIGHT,
            font=ctk.CTkFont(size=12),
            fg_color="#2B2B2B",
            border_color="#444444",
            button_color="#444444",
            dropdown_fg_color="#2B2B2B",
            state="readonly",
            command=self._on_position_changed
        )
        self.position_menu.set(self._position_values["center"])
        self.position_menu.pack(anchor="w", pady=(3, 0))
    
    def _on_bitrate_change(self, value: float) -> None:
        """Update bitrate label when slider changes."""
        self.bitrate_value_label.configure(text=f"{int(value)} Mbps")
        self._hide_auto_config_hint()
    
    def _on_param_changed(self, *args) -> None:
        """Called when any parameter is manually changed."""
        self._hide_auto_config_hint()
    
    def _on_screen_off_toggled(self) -> None:
        """Handle screen off checkbox toggle - show/hide warning label."""
        if self.screen_off_on_start.get():
            # User checked the box - show warning (after checkbox_grid, before start button)
            self.screen_off_warning_label.pack(after=self.checkbox_grid, pady=(0, 5))
        else:
            # User unchecked - hide warning
            self.screen_off_warning_label.pack_forget()
    
    def _on_borderless_toggled(self) -> None:
        """Handle borderless checkbox toggle - show/hide hint label."""
        if self.borderless_mode.get():
            # User checked the box - show hint (after checkbox_grid, before start button)
            self.borderless_hint_label.pack(after=self.checkbox_grid, pady=(0, 5))
        else:
            # User unchecked - hide hint
            self.borderless_hint_label.pack_forget()
    
    def _on_position_changed(self, choice: str) -> None:
        """Handle window position selection change."""
        # Map display text back to internal value
        for key, value in self._position_values.items():
            if value == choice:
                self.window_position.set(key)
                break
    
    def _hide_auto_config_hint(self) -> None:
        """Hide the auto-config status message."""
        if self._auto_config_applied:
            self._auto_config_applied = False
            self.auto_config_label.configure(text="")
    
    def _on_language_changed(self, choice: str) -> None:
        """Handle language selection change."""
        self.current_lang = "en" if choice == "English" else "zh"
        self._update_ui_text()
        
        # Refresh device list to update localized names (e.g. Wireless/Unauthorized)
        # Run in background to avoid UI lag
        threading.Thread(target=self._scan_devices, daemon=True).start()
    
    def _update_ui_text(self) -> None:
        """Update all UI text based on current language."""
        lang = self.current_lang
        
        # Window title
        self.title(LOCALE["window_title"][lang])
        
        # Top section
        self.device_label.configure(text=LOCALE["device_label"][lang])
        self.refresh_button.configure(text=LOCALE["refresh_btn"][lang])
        self.wireless_button.configure(text=LOCALE["wireless_btn"][lang])
        
        # Stream parameters section
        self.params_title.configure(text=LOCALE["params_title"][lang])
        self.res_label.configure(text=LOCALE["lbl_resolution"][lang])
        self.fps_label.configure(text=LOCALE["lbl_fps"][lang])
        self.codec_label.configure(text=LOCALE["lbl_codec"][lang])
        self.bitrate_label.configure(text=LOCALE["lbl_bitrate"][lang])
        
        # Position dropdown
        self.position_label.configure(text=LOCALE["lbl_position"][lang])
        self._position_values = {
            "center": LOCALE["position_center"][lang],
            "top-left": LOCALE["position_top_left"][lang],
            "top-right": LOCALE["position_top_right"][lang]
        }
        current_pos = self.window_position.get()
        self.position_menu.configure(values=list(self._position_values.values()))
        self.position_menu.set(self._position_values[current_pos])
        
        # Bottom section
        self.screen_off_checkbox.configure(text=LOCALE["screen_off"][lang])
        self.screen_off_warning_label.configure(text=LOCALE["screen_off_warning"][lang])
        self.borderless_checkbox.configure(text=LOCALE["borderless"][lang])
        self.borderless_hint_label.configure(text=LOCALE["borderless_hint"][lang])
        self.show_log_checkbox.configure(text=LOCALE["show_log"][lang])
        self.print_fps_checkbox.configure(text=LOCALE["print_fps"][lang])
        self.start_button.configure(text=LOCALE["start_btn"][lang])
        
        # Log section
        self.log_title.configure(text=LOCALE["log_title"][lang])
        self.clear_logs_button.configure(text=LOCALE["clear_logs_btn"][lang])
        
        # Update scanning placeholder if no devices
        current_device = self.selected_device.get()
        if current_device in ("Scanning...", "正在扫描...", LOCALE["scanning"]["zh"], LOCALE["scanning"]["en"]):
            self.selected_device.set(LOCALE["scanning"][lang])
        elif current_device in ("No device found", "未检测到设备", LOCALE["no_device"]["zh"], LOCALE["no_device"]["en"]):
            self.selected_device.set(LOCALE["no_device"][lang])
    
    def _apply_auto_config(self, device_serial: str) -> None:
        """Apply auto-configuration based on hardware detection."""
        try:
            # Generate recommendations
            rec = AutoConfig.generate_recommendation(device_serial, self.adb_path)
            
            # Temporarily disable trace callbacks to avoid hiding the hint
            self._auto_config_applied = True
            
            # Apply recommended values
            self.param_resolution.set(rec["resolution"])
            self.param_fps.set(rec["fps"])
            self.param_bitrate.set(rec["bitrate"])
            self.bitrate_value_label.configure(text=f"{rec['bitrate']} Mbps")
            self.param_codec.set(rec["codec"])
            
            # Re-mark as applied (traces may have reset it)
            self._auto_config_applied = True
            
            # Build status message
            # Build status message
            device_model = rec["device_model"]
            pc_ram = rec["pc_ram"]
            self.auto_config_label.configure(
                text=LOCALE["auto_config_hint"][self.current_lang].format(model=device_model, ram=pc_ram)
            )
            
            # Log the recommendation
            screen_info = f"{rec['screen_size'][0]}x{rec['screen_size'][1]}" if rec['screen_size'] else "Unknown"
            
            log_device = LOCALE["log_autoconfig_device"][self.current_lang]
            log_screen = LOCALE["log_autoconfig_screen"][self.current_lang]
            log_recommend = LOCALE["log_autoconfig_recommend"][self.current_lang]
            
            self._log(f"[AutoConfig] {log_device}: {device_model} | {log_screen}: {screen_info} | PC RAM: {pc_ram}GB")
            self._log(f"{log_recommend}: {rec['resolution']} | {rec['fps']} | {rec['bitrate']}M | {rec['codec']}")
            
        except Exception as e:
            self._log(f"[AutoConfig] 自动配置失败: {e}")
    
    def _create_bottom_section(self) -> None:
        """Create the options and start button section."""
        self.bottom_frame = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        
        # Checkbox container for 2x2 grid layout
        self.checkbox_grid = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        
        # Screen off checkbox - bold style
        self.screen_off_checkbox = ctk.CTkCheckBox(
            self.checkbox_grid,
            text="启动即熄屏",
            variable=self.screen_off_on_start,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00BFFF",
            hover_color="#4169E1",
            text_color="#CCCCCC",
            checkbox_width=20,
            checkbox_height=20,
            command=self._on_screen_off_toggled
        )
        
        # Screen off warning label (hidden by default)
        self.screen_off_warning_label = ctk.CTkLabel(
            self.bottom_frame,
            text=LOCALE["screen_off_warning"][self.current_lang],
            font=ctk.CTkFont(size=11),
            text_color=("#FFB300", "#FFB300"),
            justify="left"
        )
        
        # Borderless mode checkbox - bold style
        self.borderless_checkbox = ctk.CTkCheckBox(
            self.checkbox_grid,
            text="无边框模式",
            variable=self.borderless_mode,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00BFFF",
            hover_color="#4169E1",
            text_color="#CCCCCC",
            checkbox_width=20,
            checkbox_height=20,
            command=self._on_borderless_toggled
        )
        
        # Borderless mode hint label (hidden by default)
        self.borderless_hint_label = ctk.CTkLabel(
            self.bottom_frame,
            text=LOCALE["borderless_hint"][self.current_lang],
            font=ctk.CTkFont(size=11),
            text_color=("#4CAF50", "#4CAF50"),
            justify="left"
        )
        
        # Show log checkbox - bold style (in checkbox grid)
        self.show_log_checkbox = ctk.CTkCheckBox(
            self.checkbox_grid,
            text=LOCALE["show_log"][self.current_lang],
            variable=self.show_log_on_start,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00BFFF",
            hover_color="#4169E1",
            text_color="#CCCCCC",
            checkbox_width=20,
            checkbox_height=20
        )
        
        # Print FPS checkbox - bold style (in checkbox grid)
        self.print_fps_checkbox = ctk.CTkCheckBox(
            self.checkbox_grid,
            text=LOCALE["print_fps"][self.current_lang],
            variable=self.print_fps,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#00BFFF",
            hover_color="#4169E1",
            text_color="#CCCCCC",
            checkbox_width=20,
            checkbox_height=20
        )
        
        # Start button - modern gradient style
        self.start_button = ctk.CTkButton(
            self.bottom_frame,
            text="▶ 开始投屏",
            width=280,
            height=44,
            font=ctk.CTkFont(size=17, weight="bold"),
            fg_color="#28A745",
            hover_color="#218838",
            corner_radius=12,
            command=self._on_start_clicked
        )
        
        # Shortcut hint label - inform user about LCtrl shortcuts
        self.shortcut_hint = ctk.CTkLabel(
            self.bottom_frame,
            text="提示：投屏窗口快捷键已改为左侧 Ctrl (LCtrl+F 全屏, LCtrl+O 熄屏)",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
    
    def _create_log_section(self) -> None:
        """Create the log output section."""
        self.log_frame = ctk.CTkFrame(self.log_container_frame, fg_color="transparent")
        
        # Log header frame (title + clear button)
        self.log_header_frame = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        
        # Log section title - modern style
        self.log_title = ctk.CTkLabel(
            self.log_header_frame,
            text="📋 CONSOLE OUTPUT",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#666666"
        )
        
        # Clear logs button - modern compact style
        self.clear_logs_button = ctk.CTkButton(
            self.log_header_frame,
            text="🗑 清空",
            width=65,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="#3A3A3A",
            hover_color="#DC3545",
            corner_radius=6,
            command=self._on_clear_logs_clicked
        )
        
        # Log textbox - larger font for better readability
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame,
            width=770,
            height=160,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#0D0D0D",
            border_width=1,
            border_color="#333333",
            corner_radius=8,
            state="disabled"
        )
    
    def _layout_widgets(self) -> None:
        """Arrange all widgets in the window."""
        # Configure grid weights for main window
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Setup section
        self.grid_rowconfigure(1, weight=1)  # Log section (expandable)
        
        # Layout main container frames
        self.setup_frame.grid(row=0, column=0, sticky="ew")
        self.log_container_frame.grid(row=1, column=0, sticky="nsew", padx=35, pady=(5, 12))
        
        # Configure setup_frame grid
        self.setup_frame.grid_columnconfigure(0, weight=1)
        
        # Layout top section
        self.top_frame.grid(row=0, column=0, pady=(8, 0), padx=35, sticky="ew")
        self.device_label.pack(side="left", padx=(0, 10))
        self.device_dropdown.pack(side="left", padx=(0, 10))
        self.refresh_button.pack(side="left", padx=(0, 6))
        self.wireless_button.pack(side="left", padx=(0, 6))
        self.history_button.pack(side="left")
        self.help_button.pack(side="right", padx=(8, 0))  # Help button on right
        self.language_menu.pack(side="right")  # Language selector on the right
        
        # Layout Stream Parameters panel
        self.middle_frame.grid(row=1, column=0, pady=(0, 5), padx=35, sticky="ew", in_=self.setup_frame)
        
        # Title and auto-config label in a row
        title_row = ctk.CTkFrame(self.middle_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=15, pady=(2, 2))
        self.params_title.pack_forget()  # Remove from previous layout
        self.params_title.pack(in_=title_row, side="left")
        self.auto_config_label.pack(in_=title_row, side="right")
        
        self.params_container.pack(fill="x", padx=10, pady=(0, 10))
        
        # Layout bottom section - compact 2x2 checkbox grid
        self.bottom_frame.grid(row=2, column=0, pady=(3, 6), in_=self.setup_frame)
        
        # Checkbox grid: 2 rows x 2 columns
        self.checkbox_grid.pack(pady=(0, 5))
        self.checkbox_grid.grid_columnconfigure(0, weight=1, minsize=180)
        self.checkbox_grid.grid_columnconfigure(1, weight=1, minsize=180)
        
        # Row 0: Screen Off, Borderless
        self.screen_off_checkbox.grid(row=0, column=0, padx=15, pady=3, sticky="w")
        self.borderless_checkbox.grid(row=0, column=1, padx=15, pady=3, sticky="w")
        
        # Row 1: Show Log, Print FPS
        self.show_log_checkbox.grid(row=1, column=0, padx=15, pady=3, sticky="w")
        self.print_fps_checkbox.grid(row=1, column=1, padx=15, pady=3, sticky="w")
        
        # Warning labels are not packed by default (hidden)
        # They will be shown/hidden by callbacks
        
        self.start_button.pack(pady=(20, 10))
        self.shortcut_hint.pack(pady=(0, 5))  # Shortcut hint below start button
        
        # Layout log container
        self.log_container_frame.grid_columnconfigure(0, weight=1)
        self.log_container_frame.grid_rowconfigure(0, weight=1)
        
        # Layout log section
        self.log_frame.grid(row=0, column=0, sticky="nsew")
        self.log_header_frame.pack(fill="x", pady=(0, 4))
        self.log_title.pack(side="left")
        self.clear_logs_button.pack(side="right")
        self.log_textbox.pack(fill="both", expand=True)
        
        # Bind parameter change events to hide auto-config hint
        self.param_resolution.trace_add("write", self._on_param_changed)
        self.param_fps.trace_add("write", self._on_param_changed)
        self.param_codec.trace_add("write", self._on_param_changed)
    
    def _load_config(self) -> None:
        """Load saved configuration from config.json."""
        config_path = os.path.join(self.app_dir, self.CONFIG_FILE)
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Restore stream parameters
                if "resolution" in config:
                    self.param_resolution.set(config["resolution"])
                if "fps" in config:
                    self.param_fps.set(config["fps"])
                if "bitrate" in config:
                    self.param_bitrate.set(config["bitrate"])
                if "codec" in config:
                    self.param_codec.set(config["codec"])
                if "screen_off" in config:
                    self.screen_off_on_start.set(config["screen_off"])
                if "last_ip" in config:
                    self.last_wireless_ip = config["last_ip"]
                else:
                    self.last_wireless_ip = ""
                
                # Restore language setting
                if "language" in config:
                    self.current_lang = config["language"]
                    self.language_var.set("English" if self.current_lang == "en" else "中文")
                
                # Restore tutorial setting (default True for first-time users)
                self.show_tutorial = config.get("show_tutorial", True)
                
                print(f"[INFO] Config loaded from {self.CONFIG_FILE}")
            else:
                self.last_wireless_ip = ""
                self.show_tutorial = True  # Default for new users
        except Exception as e:
            print(f"[WARN] Failed to load config: {e}")
            self.last_wireless_ip = ""
            self.show_tutorial = True
    
    def _save_config_internal(self) -> None:
        """Internal config save - used during initialization when widgets may not exist yet."""
        config_path = os.path.join(self.app_dir, self.CONFIG_FILE)
        
        # Try to get widget values if they exist, otherwise use defaults/cached values
        try:
            resolution = self.param_resolution.get() if hasattr(self, 'param_resolution') else "1080P (1920)"
            fps = self.param_fps.get() if hasattr(self, 'param_fps') else "60 fps"
            bitrate = self.param_bitrate.get() if hasattr(self, 'param_bitrate') else 10
            codec = self.param_codec.get() if hasattr(self, 'param_codec') else "H.264 (Low Latency)"
            screen_off = self.screen_off_on_start.get() if hasattr(self, 'screen_off_on_start') else False
        except:
            # Fallback if widgets not created yet
            resolution = "1080P (1920)"
            fps = "60 fps"
            bitrate = 10
            codec = "H.264 (Low Latency)"
            screen_off = False
            
        config = {
            "resolution": resolution,
            "fps": fps,
            "bitrate": bitrate,
            "codec": codec,
            "screen_off": screen_off,
            "last_ip": getattr(self, "last_wireless_ip", ""),
            "language": getattr(self, "current_lang", "zh"),
            "show_tutorial": getattr(self, "show_tutorial", True)
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Config saved (internal) to {self.CONFIG_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def _save_config(self) -> None:
        """Save current configuration to config.json."""
        config_path = os.path.join(self.app_dir, self.CONFIG_FILE)
        config = {
            "resolution": self.param_resolution.get(),
            "fps": self.param_fps.get(),
            "bitrate": self.param_bitrate.get(),
            "codec": self.param_codec.get(),
            "screen_off": self.screen_off_on_start.get(),
            "last_ip": getattr(self, "last_wireless_ip", ""),
            "language": self.current_lang,
            "show_tutorial": getattr(self, "show_tutorial", True)
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Config saved to {self.CONFIG_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def _on_window_close(self) -> None:
        """Handle window close event - save config and exit."""
        # Stop device monitor thread
        if self._device_monitor:
            self._device_monitor.stop()
        self._save_config()
        self.destroy()
    
    def _show_tutorial_if_needed(self) -> None:
        """Show the tutorial popup if this is the user's first time."""
        if getattr(self, "show_tutorial", True):
            TutorialPopup(self, on_close_callback=self._on_tutorial_closed)
    
    def _on_tutorial_closed(self, dont_show_again: bool) -> None:
        """Handle tutorial popup close - update config if 'Don't show again' is checked."""
        if dont_show_again:
            self.show_tutorial = False
            self._save_config()
            print("[INFO] Tutorial disabled for future launches")
    
    def _show_tutorial_manual(self) -> None:
        """Manually show the tutorial popup (from Help button)."""
        TutorialPopup(self, on_close_callback=self._on_tutorial_closed)
    
    def _start_device_monitor(self) -> None:
        """Start the device hotplug monitor thread."""
        self._device_monitor = DeviceMonitor(self)
        self._device_monitor.start()
        self._log("[INFO] 设备热插拔监听已启动")
    
    def _ensure_altsnap_running(self) -> None:
        """Ensure AltSnap is running for borderless window dragging.
        
        AltSnap allows dragging borderless windows by holding Alt and dragging.
        This is useful when scrcpy is launched in borderless mode.
        """
        if not PSUTIL_AVAILABLE:
            self._log("[WARN] psutil 不可用，跳过 AltSnap 检测")
            return
        
        altsnap_exe = "AltSnap.exe"
        altsnap_path = os.path.join(self.tools_dir, altsnap_exe)
        
        # Check if AltSnap executable exists
        if not os.path.exists(altsnap_path):
            self._log(f"[INFO] AltSnap 未找到: {altsnap_path}")
            return
        
        # Check if AltSnap is already running
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == altsnap_exe.lower():
                    self._log("[INFO] AltSnap 已在运行，跳过启动")
                    return
        except Exception as e:
            self._log(f"[WARN] 检测 AltSnap 进程失败: {e}")
        
        # Start AltSnap
        # IMPORTANT: cwd must be set to tools_dir so AltSnap can find hooks.dll and AltSnap.ini
        # Use -h flag to hide tray icon (silent mode)
        try:
            subprocess.Popen(
                [altsnap_path, "-h"],
                cwd=self.tools_dir,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log("[INFO] AltSnap 已静默启动 (按住 Alt + 鼠标左键拖动窗口)")
        except Exception as e:
            self._log(f"[WARN] 启动 AltSnap 失败: {e}")
    
    def _schedule_refresh(self) -> None:
        """Schedule a device refresh with debounce (1 second delay).
        
        If multiple device change events occur within 1 second,
        only the last one will trigger an actual refresh.
        """
        # Cancel any previously scheduled refresh
        if self._refresh_scheduled is not None:
            self.after_cancel(self._refresh_scheduled)
        
        # Schedule a new refresh after 1 second
        self._refresh_scheduled = self.after(1000, self._do_scheduled_refresh)
    
    def _do_scheduled_refresh(self) -> None:
        """Execute the scheduled refresh."""
        self._refresh_scheduled = None
        self._log("[INFO] 检测到设备变化，自动刷新...")
        self._scan_devices()

    def _log(self, message: str) -> None:
        """Append a message to the log textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")  # Auto-scroll to bottom
        self.log_textbox.configure(state="disabled")
    
    def _log_threadsafe(self, message: str) -> None:
        """Thread-safe version of _log using after()."""
        self.after(0, lambda: self._log(message))
    
    # ==================== Device History Management ====================
    
    def _get_wireless_devices_from_dropdown(self) -> list[dict]:
        """Get wireless devices (IP:5555) from current device list.
        
        Returns:
            List of dicts with 'serial' (IP:5555) and 'display_name' keys
        """
        wireless_devices = []
        device_map = getattr(self, "_device_serial_map", {})
        
        for display_name, serial in device_map.items():
            # Wireless devices have IP:5555 format
            if ":5555" in serial:
                wireless_devices.append({
                    "serial": serial,
                    "display_name": display_name
                })
        
        return wireless_devices
    
    def _disconnect_wireless_device(self, serial: str) -> None:
        """Disconnect a wireless device using adb disconnect.
        
        Args:
            serial: The device serial (IP:5555 format)
        """
        try:
            subprocess.run(
                [self.adb_path, "disconnect", serial],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log(LOCALE["history_deleted"][self.current_lang].format(device=serial))
            
            # Clear last_wireless_ip if it matches the disconnected device
            # Extract IP from serial (format: IP:5555)
            ip = serial.replace(":5555", "")
            if hasattr(self, 'last_wireless_ip') and self.last_wireless_ip == ip:
                self.last_wireless_ip = ""
                self._save_config()
                
        except Exception as e:
            self._log(f"[ERROR] Failed to disconnect {serial}: {e}")
    
    def _remove_from_device_history(self, ip_address: str) -> None:
        """Remove a device from history by IP address - kept for compatibility."""
        pass  # No longer used, we use adb disconnect instead
    
    def _clear_device_history(self) -> None:
        """Disconnect all wireless devices and clear saved IP."""
        wireless_devices = self._get_wireless_devices_from_dropdown()
        for device in wireless_devices:
            self._disconnect_wireless_device(device["serial"])
        
        # Clear saved last_wireless_ip
        self.last_wireless_ip = ""
        self._save_config()
        
        self._log(LOCALE["history_cleared"][self.current_lang])
        # Refresh device list
        self.after(500, self._scan_devices)
    
    def _show_history_management_dialog(self) -> None:
        """Show a dialog to manage wireless devices (from current device dropdown)."""
        wireless_devices = self._get_wireless_devices_from_dropdown()
        
        if not wireless_devices:
            messagebox.showinfo(
                LOCALE["history_menu_title"][self.current_lang],
                LOCALE["history_empty"][self.current_lang]
            )
            return
        
        # Create a toplevel window for history management
        dialog = ctk.CTkToplevel(self)
        dialog.title(LOCALE["history_menu_title"][self.current_lang])
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 350) // 2
        dialog.geometry(f"450x350+{x}+{y}")
        
        # Title label
        title_label = ctk.CTkLabel(
            dialog,
            text=f"📱 {LOCALE['history_menu_title'][self.current_lang]}",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(15, 10))
        
        # Subtitle - explain these are connected wireless devices
        subtitle = "当前已连接的无线设备" if self.current_lang == "zh" else "Currently connected wireless devices"
        subtitle_label = ctk.CTkLabel(
            dialog,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        subtitle_label.pack(pady=(0, 10))
        
        # Create scrollable frame for device list
        scroll_frame = ctk.CTkScrollableFrame(dialog, width=410, height=180)
        scroll_frame.pack(pady=5, padx=15, fill="both", expand=True)
        
        # Add each wireless device with delete button
        for device in wireless_devices:
            serial = device["serial"]  # IP:5555
            display_name = device["display_name"]
            
            row_frame = ctk.CTkFrame(scroll_frame, fg_color="#2A2A2A", corner_radius=8)
            row_frame.pack(fill="x", pady=4, padx=2)
            
            # Device info
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            
            # Device serial (main text)
            serial_label = ctk.CTkLabel(
                info_frame,
                text=serial,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            serial_label.pack(anchor="w")
            
            # Display name (if different from serial)
            if display_name != serial:
                name_label = ctk.CTkLabel(
                    info_frame,
                    text=display_name,
                    font=ctk.CTkFont(size=11),
                    text_color="#888888",
                    anchor="w"
                )
                name_label.pack(anchor="w")
            
            # Delete button
            delete_btn = ctk.CTkButton(
                row_frame,
                text=LOCALE["history_delete_btn"][self.current_lang],
                width=70,
                height=32,
                font=ctk.CTkFont(size=12),
                fg_color="#DC3545",
                hover_color="#C82333",
                command=lambda s=serial, dlg=dialog: self._on_delete_wireless_device(s, dlg)
            )
            delete_btn.pack(side="right", padx=10, pady=8)
        
        # Bottom buttons frame
        bottom_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=15, padx=15)
        
        # Clear all button
        clear_all_btn = ctk.CTkButton(
            bottom_frame,
            text=LOCALE["history_clear_all"][self.current_lang],
            width=130,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#6C757D",
            hover_color="#5A6268",
            command=lambda: self._on_clear_all_wireless(dialog)
        )
        clear_all_btn.pack(side="left")
        
        # Close button
        close_btn = ctk.CTkButton(
            bottom_frame,
            text="关闭" if self.current_lang == "zh" else "Close",
            width=80,
            height=32,
            font=ctk.CTkFont(size=12),
            command=dialog.destroy
        )
        close_btn.pack(side="right")
    
    def _on_delete_wireless_device(self, serial: str, dialog: ctk.CTkToplevel) -> None:
        """Handle delete button click - disconnect wireless device."""
        if messagebox.askyesno(
            LOCALE["history_delete_confirm_title"][self.current_lang],
            LOCALE["history_delete_confirm_msg"][self.current_lang].format(device=serial)
        ):
            dialog.destroy()
            self._disconnect_wireless_device(serial)
            # Refresh device list after disconnect
            self.after(500, self._scan_devices)
            # Reopen dialog after refresh
            self.after(1000, self._show_history_management_dialog)
    
    def _on_clear_all_wireless(self, dialog: ctk.CTkToplevel) -> None:
        """Handle clear all button - disconnect all wireless devices."""
        if messagebox.askyesno(
            LOCALE["history_delete_confirm_title"][self.current_lang],
            LOCALE["history_clear_all"][self.current_lang] + "?"
        ):
            dialog.destroy()
            self._clear_device_history()
    
    # ==================== End Device History Management ====================

    
    def _on_clear_logs_clicked(self) -> None:
        """Handle clear logs button click."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")
    


    def _on_disconnect_clicked(self) -> None:
        """Handle disconnect button click."""
        self._disconnect_current_device()
    
    def _disconnect_current_device(self) -> None:
        """Disconnect the currently selected device."""
        display_name = self.selected_device.get()
        lang = self.current_lang
        
        # Check if a valid device is selected
        invalid_values = (
            "Scanning...", "正在扫描...",
            LOCALE["scanning"]["zh"], LOCALE["scanning"]["en"],
            LOCALE["no_device"]["zh"], LOCALE["no_device"]["en"]
        )
        if not display_name or display_name in invalid_values:
            self._log(LOCALE["log_no_device_to_disconnect"][lang])
            return
        
        # Get the actual serial from the display name mapping
        device_serial_map = getattr(self, "_device_serial_map", {})
        serial = device_serial_map.get(display_name, display_name)
        
        # Check if it's a wireless device (IP:port format) or has special status
        is_wireless = bool(re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', serial))
        
        # Also check if display name contains offline/unauthorized indicators
        # These might be zombie connections that should be disconnected
        is_zombie = any(indicator in display_name.lower() for indicator in 
                       ["offline", "unauthorized", "未授权", "离线"])
        
        if is_wireless or is_zombie:
            # Wireless device or zombie connection - can disconnect
            self._log(LOCALE["log_attempting_disconnect"][lang].format(device=serial))
            try:
                result = subprocess.run(
                    [self.adb_path, "disconnect", serial],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0 or "disconnected" in result.stdout.lower():
                    self._log(LOCALE["log_disconnected_wireless"][lang].format(device=serial))
                else:
                    # Still log as success since adb disconnect doesn't always return proper status
                    self._log(LOCALE["log_disconnected_wireless"][lang].format(device=serial))
                
                # Refresh device list
                self._scan_devices()
                
            except subprocess.TimeoutExpired:
                self._log(LOCALE["log_adb_timeout"][lang])
            except Exception as e:
                self._log(LOCALE["log_disconnect_failed"][lang].format(e=e))
        else:
            # USB device - cannot disconnect via software
            self._log(LOCALE["log_usb_cannot_disconnect"][lang])

    def _on_refresh_clicked(self) -> None:
        """Handle refresh button click."""
        self._log("[INFO] Refreshing device list...")
        self._scan_devices()
    
    def _on_wireless_clicked(self) -> None:
        """Handle wireless connect button click - auto-detect or manual input."""
        # Check if there's a USB device connected
        usb_device = self._get_usb_device()
        
        if usb_device:
            # USB device found, try to auto-get IP and connect
            self._log(f"[INFO] Detected USB device: {usb_device}")
            self._auto_wireless_connect(usb_device)
        else:
            # No USB device connected
            # Check if any wireless devices are already connected in dropdown
            wireless_devices = self._get_wireless_devices_from_dropdown()
            has_previous_connection = (
                hasattr(self, 'last_wireless_ip') and self.last_wireless_ip
            ) or len(wireless_devices) > 0
            
            if has_previous_connection:
                # User has connected before or has wireless devices, allow manual input
                self._log("[INFO] No USB device detected, please enter IP manually.")
                self._show_manual_ip_dialog()
            else:
                # First-time user with no USB device - show guidance with option to manually enter
                self._log("[WARN] 首次无线连接未检测到设备")
                # Ask if user wants to manually enter IP
                result = messagebox.askyesno(
                    LOCALE["wireless_first_time_title"][self.current_lang],
                    LOCALE["wireless_first_time_msg"][self.current_lang]
                )
                if result:
                    # User wants to manually enter IP
                    self._show_manual_ip_dialog()
    
    def _get_usb_device(self) -> str | None:
        """Get the first USB-connected device serial (not wireless)."""
        for device in self.available_devices:
            # Wireless devices typically have IP:port format
            if not re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', device):
                return device
        return None
    
    def _get_device_ip(self, device_serial: str) -> str | None:
        """Get the WLAN IP address of a device via adb shell ip route."""
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_serial, "shell", "ip", "route"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout
            self._log(f"[DEBUG] ip route output: {output.strip()[:100]}...")
            
            # Look for wlan0 interface with src IP
            # Format: ... dev wlan0 proto kernel scope link src 192.168.x.x
            match = re.search(r'dev\s+wlan0\s+.*?src\s+(\d+\.\d+\.\d+\.\d+)', output)
            if match:
                ip = match.group(1)
                self._log(f"[INFO] Detected device IP: {ip}")
                return ip
            
            # Alternative pattern for some devices
            match = re.search(r'src\s+(\d+\.\d+\.\d+\.\d+)\s+.*?wlan0', output)
            if match:
                ip = match.group(1)
                self._log(f"[INFO] Detected device IP: {ip}")
                return ip
            
            self._log("[WARN] Could not find wlan0 IP in route output.")
            return None
            
        except subprocess.TimeoutExpired:
            self._log("[ERROR] Timeout getting device IP.")
            return None
        except Exception as e:
            self._log(f"[ERROR] Failed to get device IP: {e}")
            return None
    
    def _auto_wireless_connect(self, usb_device: str) -> None:
        """Auto-connect to wireless using USB device."""
        # Step 1: Get device IP
        ip_address = self._get_device_ip(usb_device)
        
        if not ip_address:
            self._log(LOCALE["log_ip_fallback"][self.current_lang])
            self._show_manual_ip_dialog()
            return
        
        self.last_wireless_ip = ip_address  # Remember for future
        
        # Step 2: Enable TCP/IP mode on device
        self._log(LOCALE["log_enabling_tcpip"][self.current_lang].format(device=usb_device))
        try:
            result = subprocess.run(
                [self.adb_path, "-s", usb_device, "tcpip", "5555"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log(f"[ADB] {result.stdout.strip() or result.stderr.strip() or 'TCP/IP mode enabled'}")
        except Exception as e:
            self._log(LOCALE["log_tcpip_failed"][self.current_lang].format(e=e))
            return
        
        # Step 3: Wait for device to restart ADB in TCP mode
        self._log(LOCALE["log_waiting_restart"][self.current_lang])
        time.sleep(2)
        
        # Step 4: Connect via wireless
        self._log(LOCALE["log_connecting"][self.current_lang].format(target=f"{ip_address}:5555"))
        self._connect_wireless(ip_address, show_success_dialog=True)
    
    def _show_manual_ip_dialog(self) -> None:
        """Show dialog for manual IP input."""
        dialog = ctk.CTkInputDialog(
            text="请输入手机 IP 地址:\n\n提示：请前往 手机设置 -> 关于手机 -> 状态信息 查看 IP",
            title="无线连接向导"
        )
        
        # Pre-fill with last used IP if available
        if hasattr(self, "last_wireless_ip") and self.last_wireless_ip:
            dialog._entry.insert(0, self.last_wireless_ip)
        
        ip_address = dialog.get_input()
        
        if ip_address and ip_address.strip():
            ip_address = ip_address.strip()
            self.last_wireless_ip = ip_address  # Remember for next time
            self._log(f"[INFO] Attempting to connect to {ip_address}:5555...")
            self._connect_wireless(ip_address)
    
    def _scan_devices(self) -> None:
        """Scan for connected ADB devices and update the dropdown."""
        try:
            # Run adb devices command
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hide console window on Windows
            )
            
            # Parse the output
            lines = result.stdout.strip().split("\n")
            device_serials = []
            
            for line in lines[1:]:  # Skip the first line ("List of devices attached")
                line = line.strip()
                if line and "\t" in line:
                    serial, status = line.split("\t", 1)
                    if status == "device":  # Only include ready devices
                        device_serials.append(serial)
            
            if device_serials:
                self._log(LOCALE["log_getting_info"][self.current_lang])
            
            # Get friendly names for all devices
            self._device_serial_map = {}  # display_name -> serial
            display_names = []
            
            for serial in device_serials:
                display_name = self._get_device_display_name(serial)
                display_names.append(display_name)
                self._device_serial_map[display_name] = serial
            
            self.available_devices = device_serials
            self._update_device_dropdown(display_names)
            
        except FileNotFoundError:
            self._log(LOCALE["log_adb_not_found"][self.current_lang])
            self._update_device_dropdown([])
        except subprocess.TimeoutExpired:
            self._log(LOCALE["log_adb_timeout"][self.current_lang])
            self._update_device_dropdown([])
        except Exception as e:
            self._log(LOCALE["log_scan_failed"][self.current_lang].format(e=e))
            self._update_device_dropdown([])
    
    def _get_device_display_name(self, serial: str) -> str:
        """Get a friendly display name for a device (Manufacturer Model (serial))."""
        # Check if it's a wireless device (IP:port format)
        is_wireless = bool(re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', serial))
        lang = self.current_lang
        
        # Get localized suffixes
        wireless_suffix = LOCALE["device_wireless"][lang]
        unauthorized_suffix = LOCALE["device_unauthorized"][lang]
        
        try:
            # Get manufacturer
            manufacturer_result = subprocess.run(
                [self.adb_path, "-s", serial, "shell", "getprop", "ro.product.manufacturer"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            manufacturer = manufacturer_result.stdout.strip()
            
            # Get model
            model_result = subprocess.run(
                [self.adb_path, "-s", serial, "shell", "getprop", "ro.product.model"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            model = model_result.stdout.strip()
            
            if manufacturer and model:
                # Format: "Manufacturer Model (serial)" or with wireless indicator
                if is_wireless:
                    return f"{manufacturer} {model} ({wireless_suffix})"
                else:
                    return f"{manufacturer} {model} ({serial})"
            else:
                # Failed to get info, use serial only
                if is_wireless:
                    return f"{serial} ({wireless_suffix})"
                else:
                    return serial
                    
        except subprocess.TimeoutExpired:
            # Device might be unauthorized or offline
            if is_wireless:
                return f"{serial} ({wireless_suffix})"
            else:
                return f"{serial} ({unauthorized_suffix})"
        except Exception:
            if is_wireless:
                return f"{serial} ({wireless_suffix})"
            else:
                return serial
    
    def _update_device_dropdown(self, display_names: list[str]) -> None:
        """Update the device selector with scanned devices."""
        # Save mapping first
        self._current_display_names = display_names
        
        if display_names:
            self.device_dropdown.configure(values=display_names, state="readonly")
            
            # If we have a pending wireless device to select, find its display name
            pending_serial = getattr(self, "_pending_wireless_device", None)
            selected = False
            
            if pending_serial:
                for display_name, serial in self._device_serial_map.items():
                    if serial == pending_serial:
                        self.selected_device.set(display_name)
                        self._pending_wireless_device = None
                        self._log(LOCALE["log_auto_select"][self.current_lang].format(name=display_name))
                        selected = True
                        break
            
            if not selected:
                # If current selection is invalid (not in new list), select first one
                current = self.selected_device.get()
                if current not in display_names:
                     self.selected_device.set(display_names[0])
            
            self.start_button.configure(state="normal")
            self._log(LOCALE["log_found_devices"][self.current_lang].format(count=len(display_names)))
            
            # Apply auto-config for the first device (or selected)
            # Find serial for current device
            current_display = self.selected_device.get()
            current_serial = self._device_serial_map.get(current_display)
            if current_serial:
                self._apply_auto_config(current_serial)
        else:
            no_device_text = LOCALE["no_device"][self.current_lang]
            self.device_dropdown.configure(values=[no_device_text], state="disabled")
            self.selected_device.set(no_device_text)
            self.start_button.configure(state="disabled")
            self._log(LOCALE["log_no_device"][self.current_lang])
    
    def _connect_wireless(self, ip_address: str, show_success_dialog: bool = False) -> None:
        """Connect to a device via wireless ADB."""
        target = f"{ip_address}:5555"
        
        try:
            result = subprocess.run(
                [self.adb_path, "connect", target],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            output = result.stdout.strip()
            self._log(f"[ADB] {output}")
            
            if "connected" in output.lower():
                self._log(LOCALE["log_connected"][self.current_lang].format(target=target))
                
                # Mark this device to be auto-selected after refresh
                self._pending_wireless_device = target
                
                # Save last connected IP for convenience
                self.last_wireless_ip = ip_address
                self._save_config()
                
                # Refresh device list to show the new wireless device
                self.after(500, self._scan_devices)
                
                # Show success dialog if requested
                if show_success_dialog:
                    messagebox.showinfo(
                        LOCALE["wireless_success_title"][self.current_lang],
                        LOCALE["wireless_success_msg"][self.current_lang].format(target=target)
                    )
            else:
                self._log(LOCALE["log_connect_failed_output"][self.current_lang].format(output=output))
                
        except subprocess.TimeoutExpired:
            self._log(LOCALE["log_connect_timeout"][self.current_lang])
        except Exception as e:
            self._log(LOCALE["log_connect_exception"][self.current_lang].format(e=e))
    
    def _on_start_clicked(self) -> None:
        """Handle start button click - launch scrcpy with selected options."""
        display_name = self.selected_device.get()
        
        # Safety check: ensure a valid device is selected
        if not display_name or display_name in ("Scanning...", "正在扫描...", LOCALE["scanning"]["zh"], LOCALE["scanning"]["en"], LOCALE["no_device"]["zh"], LOCALE["no_device"]["en"]):
            self._log(LOCALE["log_no_valid_device"][self.current_lang])
            return
        
        # Get the actual serial from the display name mapping
        device_serial_map = getattr(self, "_device_serial_map", {})
        device = device_serial_map.get(display_name, display_name)
        
        # Build the command as a list
        command = [self.scrcpy_path]
        
        # Add device serial
        command.extend(["-s", device])
        
        # Parse resolution (extract number from display value)
        resolution = self.param_resolution.get()
        if resolution != "Native":
            # Extract number: "1080P (1920)" -> "1920", "2K (2560)" -> "2560"
            import re
            res_match = re.search(r'\((\d+)\)', resolution)
            if res_match:
                command.extend(["-m", res_match.group(1)])
        
        # Parse FPS (extract number)
        fps = self.param_fps.get().replace(" fps", "")
        command.append(f"--max-fps={fps}")
        
        # Parse codec
        codec = self.param_codec.get()
        codec_value = "h264" if "H.264" in codec else "h265"
        command.append(f"--video-codec={codec_value}")
        
        # Bitrate
        bitrate = self.param_bitrate.get()
        command.extend(["-b", f"{bitrate}M"])
        
        # Screen off
        screen_off = self.screen_off_on_start.get()
        if screen_off:
            command.append("--turn-screen-off")
        
        # Borderless mode
        borderless = self.borderless_mode.get()
        if borderless:
            command.append("--window-borderless")
        
        # Print FPS (real-time performance monitor)
        if self.print_fps.get():
            command.append("--print-fps")
        
        # Window position
        position = self.window_position.get()
        if position == "top-left":
            command.extend(["--window-x", "50", "--window-y", "50"])
        elif position == "top-right":
            screen_width = self.winfo_screenwidth()
            # Estimate phone window width ~450px, add some margin
            x_pos = screen_width - 500
            command.extend(["--window-x", str(x_pos), "--window-y", "50"])
        # "center" is Scrcpy default, no params needed
        
        # Force LCtrl as shortcut modifier (avoid conflict with AltSnap)
        command.append("--shortcut-mod=lctrl")
        
        # Print the command to log
        self._log("=" * 50)
        self._log(f"[Device] {display_name}")
        self._log(f"[Params] {resolution} | {self.param_fps.get()} | {codec} | {bitrate}M")
        self._log(f"[Command] {' '.join(command)}")
        self._log("=" * 50)
        
        # Launch scrcpy asynchronously and capture output
        # Note: scrcpy must run from internal_dir to find its DLLs and scrcpy-server
        try:
            process = subprocess.Popen(
                command,
                cwd=self.internal_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log(LOCALE["log_scrcpy_launched"][self.current_lang])
            
            # Store process reference for silent mode monitoring
            self.current_scrcpy_process = process
            
            # Check if user wants to see log window or hide GUI (pure mirror mode)
            if self.show_log_on_start.get():
                # Traditional mode: Transform UI to monitoring mode
                self._enter_monitoring_mode()
                
                # Start a thread to read and display output
                output_thread = threading.Thread(
                    target=self._read_process_output,
                    args=(process,),
                    daemon=True
                )
                output_thread.start()
                
                # Start a thread to monitor process lifecycle
                monitor_thread = threading.Thread(
                    target=self._monitor_scrcpy_process,
                    args=(process,),
                    daemon=True
                )
                monitor_thread.start()
            else:
                # Pure mirror mode: Hide GUI completely
                self._log("[INFO] 纯净模式：隐藏主窗口，关闭投屏窗口后自动恢复")
                self.withdraw()  # Hide the main window
                
                # Start polling to monitor scrcpy process
                self._monitor_silent_process()
            
        except FileNotFoundError:
            self._log(LOCALE["log_scrcpy_not_found"][self.current_lang].format(path=self.scrcpy_path))
        except Exception as e:
            self._log(LOCALE["log_launch_failed"][self.current_lang].format(e=e))
    
    def _enter_monitoring_mode(self) -> None:
        """Transform UI to monitoring mode - hide setup, show only log."""
        # Hide setup frame
        self.setup_frame.grid_remove()
        
        # Resize window to be more compact for monitoring
        self.geometry("850x300")
        self.resizable(True, True)  # Allow resize in monitoring mode
        self.minsize(400, 200)
        
        # Re-center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 850) // 2
        y = (self.winfo_screenheight() - 300) // 2
        self.geometry(f"850x300+{x}+{y}")
        
        # Force reload icon multiple times to prevent taskbar icon disappearing (PyInstaller fix)
        # Windows sometimes resets icon during window geometry changes
        self._force_reload_icon()
        
        # Update window title to indicate monitoring mode
        self.title("Scrcpy Monitor - 投屏监控中...")
        
        self._log("[INFO] 已进入监控模式，关闭投屏窗口后程序将自动退出")
    
    def _monitor_silent_process(self) -> None:
        """Monitor scrcpy process in silent/pure mode.
        
        Polls every 500ms. When scrcpy exits, restore the main window.
        """
        if self.current_scrcpy_process is None:
            return
        
        # Check if process has exited
        if self.current_scrcpy_process.poll() is not None:
            # Process has ended - restore main window
            self.current_scrcpy_process = None
            self.deiconify()  # Show the main window again
            self.lift()  # Bring to front
            self.focus_force()  # Focus the window
            self._log("[INFO] 投屏已结束，主窗口已恢复")
            
            # Re-enable start button if needed
            self.start_button.configure(state="normal")
        else:
            # Process still running - check again in 500ms
            self.after(500, self._monitor_silent_process)
    
    def _force_reload_icon(self) -> None:
        """Force reload window icon with multiple attempts to ensure persistence."""
        if not hasattr(self, 'icon_path') or not self.icon_path:
            return
        if not os.path.exists(self.icon_path):
            return
        if not self.icon_path.endswith('.ico'):
            return
        
        def set_icon():
            try:
                self.iconbitmap(self.icon_path)
                self.wm_iconbitmap(default=self.icon_path)
            except Exception:
                pass
        
        # Set icon immediately
        set_icon()
        
        # Also set with delays to catch any late window redraws
        self.after(100, set_icon)
        self.after(300, set_icon)
        self.after(500, set_icon)
    
    def _monitor_scrcpy_process(self, process: subprocess.Popen) -> None:
        """Monitor scrcpy process and exit launcher when it ends."""
        while True:
            # Check if process is still running
            if process.poll() is not None:
                # Process has ended
                self._log_threadsafe("[INFO] 检测到投屏窗口已关闭，准备退出...")
                # Give a short delay for final log messages
                time.sleep(0.5)
                # Exit the application from main thread
                self.after(0, self._exit_application)
                break
            time.sleep(1)  # Check every second
    
    def _exit_application(self) -> None:
        """Cleanly exit the application."""
        self._save_config()
        if self._device_monitor:
            self._device_monitor.stop()
        self.destroy()
    
    def _read_process_output(self, process: subprocess.Popen) -> None:
        """Read process output in a separate thread and display in log."""
        try:
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    self._log_threadsafe(f"[SCRCPY] {line}")
            
            # Process has ended, get return code
            return_code = process.wait()
            if return_code == 0:
                self._log_threadsafe(LOCALE["log_scrcpy_exited"][self.current_lang])
            else:
                self._log_threadsafe(LOCALE["log_scrcpy_exit_code"][self.current_lang].format(code=return_code))
                
        except Exception as e:
            self._log_threadsafe(LOCALE["log_read_error"][self.current_lang].format(e=e))


def main():
    """Application entry point."""
    # Set appearance mode and color theme before creating the app
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create and run the application
    app = ScrcpyLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
