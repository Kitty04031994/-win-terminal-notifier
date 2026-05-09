"""
窗口监控模块 - 获取当前活动窗口并判断是否为终端
"""

import ctypes
from ctypes import wintypes
import psutil
from typing import Optional, Tuple


# Windows API 定义
user32 = ctypes.windll.user32

GetForegroundWindow = user32.GetForegroundWindow
GetForegroundWindow.restype = wintypes.HWND

GetWindowTextW = user32.GetWindowTextW
GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(ctypes.c_ulong)]
GetWindowThreadProcessId.restype = ctypes.c_ulong

# 终端进程关键词（小写）
TERMINAL_PROCESSES = {
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "windowsterminal.exe",
    "wt.exe",
    "conhost.exe",
    "terminal.exe",
}

TERMINAL_WINDOW_TITLES = {
    "powershell",
    "powershell ise",
    "windows powershell",
    "command prompt",
    "terminal",
    "cmd",
}


def get_foreground_window() -> Tuple[int, str]:
    """
    获取前台窗口句柄和标题

    Returns:
        (hwnd, title) - 窗口句柄和窗口标题
    """
    hwnd = GetForegroundWindow()
    if hwnd == 0:
        return 0, ""

    title = get_window_title(hwnd)
    return hwnd, title


def get_window_title(hwnd: int) -> str:
    """获取窗口标题"""
    if hwnd == 0:
        return ""

    length = GetWindowTextW(hwnd, None, 0)
    if length == 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_process_name(hwnd: int) -> Tuple[str, int]:
    """
    获取窗口对应的进程名和 PID
    返回: (process_name, pid)
    """
    if hwnd == 0:
        return "", 0

    process_id = ctypes.c_ulong()
    GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    pid = process_id.value

    try:
        process = psutil.Process(pid)
        return process.name().lower(), pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "", 0


def is_terminal_window(hwnd: Optional[int] = None, title: str = "", process_name: str = "") -> bool:
    """
    判断窗口是否为终端窗口

    Args:
        hwnd: 窗口句柄（如果提供，将自动获取 process_name）
        title: 窗口标题
        process_name: 进程名（如果未提供 hwnd，需要手动传入）

    Returns:
        bool - 是否为终端窗口
    """
    # 如果提供了 hwnd，自动获取 process_name
    if hwnd is not None and not process_name:
        process_result = get_window_process_name(hwnd)
        if isinstance(process_result, tuple):
            process_name = process_result[0]
        else:
            process_name = process_result

    process_name = process_name.lower()
    title = title.lower()

    # 检查进程名
    if process_name in TERMINAL_PROCESSES:
        return True

    # 检查窗口标题关键词
    for keyword in TERMINAL_WINDOW_TITLES:
        if keyword in title:
            return True

    return False


def is_away_from_terminal(saved_hwnd: int, saved_title: str) -> bool:
    """
    判断用户是否离开了之前记录的终端窗口

    Args:
        saved_hwnd: 之前记录的终端窗口句柄
        saved_title: 之前记录的终端窗口标题

    Returns:
        bool - 是否离开终端
    """
    current_hwnd, current_title = get_foreground_window()
    process_result = get_window_process_name(current_hwnd)
    if isinstance(process_result, tuple):
        current_process = process_result[0]
    else:
        current_process = process_result

    # 如果当前窗口不是终端，认为离开
    if not is_terminal_window(current_hwnd, current_title, current_process):
        return True

    # 如果窗口句柄改变了，也认为离开
    if saved_hwnd > 0 and current_hwnd != saved_hwnd:
        return True

    # 否则认为没有离开
    return False


def find_terminal_window(saved_hwnd: int, process_name: str, target_pid: int = 0) -> int:
    """
    查找终端窗口句柄
    优先按 PID 查找，其次按进程名查找

    Args:
        saved_hwnd: 之前保存的窗口句柄
        process_name: 进程名
        target_pid: 目标进程 PID

    Returns:
        找到的窗口句柄，如果未找到返回 0
    """
    # 先检查当前前台窗口
    current_hwnd, current_title = get_foreground_window()
    if current_hwnd > 0:
        proc_result = get_window_process_name(current_hwnd)
        if isinstance(proc_result, tuple):
            current_process, current_pid = proc_result
        else:
            current_process = proc_result
            current_pid = 0

        if is_terminal_window(current_hwnd, current_title, current_process):
            return current_hwnd

    # 通过 PID 查找
    if target_pid > 0:
        hwnd = find_window_by_pid(target_pid)
        if hwnd > 0:
            return hwnd

    # 通过进程名查找
    if process_name:
        hwnd = find_window_by_process_name(process_name)
        if hwnd > 0:
            return hwnd

    # 尝试原来的 hwnd
    if saved_hwnd > 0:
        try:
            length = GetWindowTextW(saved_hwnd, None, 0)
            if length > 0:
                return saved_hwnd
        except:
            pass

    return 0


def find_window_by_pid(target_pid: int) -> int:
    """通过 PID 查找窗口句柄"""
    result_hwnd = 0

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    def enum_callback(hwnd, lParam):
        nonlocal result_hwnd
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            pid = ctypes.c_ulong()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            if pid.value == target_pid:
                result_hwnd = hwnd
                return False
        except:
            pass
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))(enum_callback), 0)
    return result_hwnd


def find_window_by_process_name(process_name: str) -> int:
    """根据进程名查找窗口句柄"""
    result_hwnd = 0

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    def enum_callback(hwnd, lParam):
        nonlocal result_hwnd
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            pid = ctypes.c_ulong()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            try:
                proc = psutil.Process(pid.value)
                if proc.name().lower() == process_name:
                    result_hwnd = hwnd
                    return False
            except:
                pass
        except:
            pass
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))(enum_callback), 0)
    return result_hwnd


if __name__ == "__main__":
    # 测试
    hwnd, title = get_foreground_window()
    proc_result = get_window_process_name(hwnd)
    if isinstance(proc_result, tuple):
        process_name, pid = proc_result
    else:
        process_name = proc_result
        pid = 0
    is_term = is_terminal_window(hwnd, title, process_name)

    print(f"前台窗口:")
    print(f"  句柄: {hwnd}")
    print(f"  标题: {title}")
    print(f"  进程: {process_name}, pid: {pid}")
    print(f"  是终端: {is_term}")