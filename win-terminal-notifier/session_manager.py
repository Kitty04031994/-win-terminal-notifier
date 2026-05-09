"""
会话管理模块 - 保存/读取终端窗口会话状态
"""

import json
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta


# 会话存储目录
SESSION_DIR = Path(os.environ.get("TEMP", "/tmp")) / "win_terminal_notifier"
SESSION_DIR.mkdir(exist_ok=True)

# 去重时间窗口（秒）
DEDUP_WINDOW_SECONDS = 2.0


def get_session_file(session_id: str) -> Path:
    """获取会话文件路径"""
    return SESSION_DIR / f"session_{session_id}.json"


def save_session(session_id: str, window_handle: int, window_title: str, process_name: str = "", pid: int = 0) -> None:
    """
    保存会话信息

    Args:
        session_id: Claude Code 会话 ID
        window_handle: 终端窗口句柄
        window_title: 终端窗口标题
        process_name: 进程名
        pid: 进程 PID
    """
    session_file = get_session_file(session_id)
    data = {
        "window_handle": window_handle,
        "window_title": window_title,
        "process_name": process_name,
        "pid": pid,
        "saved_at": datetime.now().isoformat(),
    }
    session_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_session(session_id: str) -> Optional[Tuple[int, str, str, int]]:
    """
    加载会话信息

    Args:
        session_id: Claude Code 会话 ID

    Returns:
        (window_handle, window_title, process_name, pid) 或 None
    """
    session_file = get_session_file(session_id)
    if not session_file.exists():
        return None

    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
        return (
            data.get("window_handle", 0),
            data.get("window_title", ""),
            data.get("process_name", ""),
            data.get("pid", 0)
        )
    except (json.JSONDecodeError, IOError):
        return None


def delete_session(session_id: str) -> None:
    """删除会话"""
    session_file = get_session_file(session_id)
    if session_file.exists():
        session_file.unlink()


def find_latest_session() -> Optional[Tuple[int, str, str, int]]:
    """
    扫描会话目录，找最新保存的会话

    用于 CLAUDE_SESSION_ID 环境变量未设置时的 fallback。
    """
    if not SESSION_DIR.exists():
        return None

    session_files = list(SESSION_DIR.glob("session_*.json"))
    if not session_files:
        return None

    # 按修改时间排序，取最新的
    latest = max(session_files, key=lambda f: f.stat().st_mtime)
    return load_session(latest.stem.replace("session_", "", 1))


# 去重相关
_last_notification_time = None


def should_send_notification() -> bool:
    """
    判断是否应该发送通知（去重）

    Returns:
        bool - 是否发送
    """
    global _last_notification_time

    now = datetime.now()
    if _last_notification_time is None:
        _last_notification_time = now
        return True

    # 检查是否在去重时间窗口内
    elapsed = (now - _last_notification_time).total_seconds()
    if elapsed < DEDUP_WINDOW_SECONDS:
        return False

    _last_notification_time = now
    return True


def reset_dedup() -> None:
    """重置去重状态"""
    global _last_notification_time
    _last_notification_time = None


if __name__ == "__main__":
    # 测试
    import uuid
    test_session = str(uuid.uuid4())

    save_session(test_session, 12345, "PowerShell")
    session = load_session(test_session)
    print(f"加载会话: {session}")

    delete_session(test_session)
    session = load_session(test_session)
    print(f"删除后会话: {session}")