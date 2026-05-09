"""
通知模块 - 发送 Windows Toast 通知和窗口聚焦
"""

import subprocess
import ctypes
import os
from ctypes import wintypes
from typing import Optional


# Windows 系统路径
SYSTEM_ROOT = os.environ.get("SystemRoot", "C:/Windows")
POWERSHELL_PATH = os.path.join(SYSTEM_ROOT, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
CMD_PATH = os.path.join(SYSTEM_ROOT, "System32", "cmd.exe")


# Windows API
user32 = ctypes.windll.user32

SetForegroundWindow = user32.SetForegroundWindow
SetForegroundWindow.argtypes = [wintypes.HWND]
SetForegroundWindow.restype = wintypes.BOOL

ShowWindow = user32.ShowWindow
ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
ShowWindow.restype = wintypes.BOOL

SW_RESTORE = 9  # 恢复窗口
SW_SHOW = 5     # 显示窗口


def send_toast_notification(title: str, message: str, app_id: str = "Claude Code") -> bool:
    """
    发送 Windows 通知（非阻塞）

    Args:
        title: 通知标题
        message: 通知内容
        app_id: 应用标识

    Returns:
        bool - 是否成功发送
    """
    # 方法1: 使用 PowerShell 的 [void] 异步弹窗
    ps_script = f'''
    Start-Process powershell -ArgumentList '-NoProfile', '-Command', "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show('{message}', '{title}', 'OK', 'Information')" -WindowStyle Hidden
    '''
    try:
        result = subprocess.run(
            [POWERSHELL_PATH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        print(f"通知失败: {e}")

    # 方法2: 回退到 msg 命令（可能需要用户确认）
    full_message = f"{title}\n{message}"
    try:
        result = subprocess.run(
            [CMD_PATH, "/c", f"msg * /TIME:5 \"{full_message}\""],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        print(f"msg 命令失败: {e}")
        return False


def focus_window(hwnd: int) -> bool:
    """
    聚焦到指定窗口

    Args:
        hwnd: 窗口句柄

    Returns:
        bool - 是否成功聚焦
    """
    if hwnd <= 0:
        return False

    try:
        # 先恢复窗口（如果最小化）
        ShowWindow(hwnd, SW_RESTORE)
        # 然后聚焦
        return SetForegroundWindow(hwnd) != 0
    except Exception as e:
        print(f"聚焦窗口失败: {e}")
        return False


def send_notification_with_action(title: str, message: str, window_handle: int = 0) -> None:
    """
    发送通知，并在用户点击时聚焦到窗口

    Args:
        title: 通知标题
        message: 通知内容
        window_handle: 窗口句柄（点击通知时聚焦）
    """
    # 先发送通知
    success = send_toast_notification(title, message)

    if success and window_handle > 0:
        # 聚焦到窗口
        focus_window(window_handle)


if __name__ == "__main__":
    # 测试
    print("测试发送通知...")
    result = send_toast_notification("测试通知", "这是一条测试通知")
    print(f"发送结果: {result}")