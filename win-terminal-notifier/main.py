#!/usr/bin/env python3
"""
Windows 终端离开通知器 - CLI 入口
用于 Claude Code hooks

用法:
    python main.py init      # 会话开始时调用，记录终端窗口
    python main.py notify    # 有待确认事件时调用，检查并发送通知
    python main.py task_done # 任务完成时调用，发送通知
    python main.py auto      # 自动检测并通知（检测用户输入是否需要确认）
    python main.py cleanup   # 会话结束时调用，清理会话
"""

import json
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from window_monitor import get_foreground_window, get_window_process_name, find_terminal_window
from session_manager import save_session, load_session, delete_session, should_send_notification, find_latest_session
from notifier import send_toast_notification, focus_window


# Claude Code Hook 数据类
class HookData:
    def __init__(self, session_id: str, hook_type: str = "", matcher: str = "", message: str = ""):
        self.session_id = session_id
        self.hook_type = hook_type
        self.matcher = matcher
        self.message = message

    @classmethod
    def from_stdin(cls) -> "HookData":
        """从 stdin 读取 hook 数据"""
        try:
            # Claude Code 通过环境变量或 stdin 传递数据
            # 尝试从环境变量读取
            session_id = os.environ.get("CLAUDE_SESSION_ID", "")
            hook_type = os.environ.get("CLAUDE_HOOK_TYPE", "")
            matcher = os.environ.get("CLAUDE_HOOK_MATCHER", "")

            # 如果环境变量为空，尝试从 stdin 读取 JSON
            if not session_id:
                try:
                    stdin_data = sys.stdin.read()
                    if stdin_data:
                        data = json.loads(stdin_data)
                        session_id = data.get("session_id", "")
                        hook_type = data.get("hook_type", "")
                        matcher = data.get("matcher", "")
                except:
                    pass

            # 使用时间戳作为 fallback session_id
            if not session_id:
                import time
                session_id = f"session_{int(time.time())}"

            return cls(session_id, hook_type, matcher, "")
        except Exception as e:
            print(f"读取 hook 数据失败: {e}", file=sys.stderr)
            # 使用时间戳作为 fallback
            import time
            return cls(f"session_{int(time.time())}", "", "", "")


def cmd_init(hook_data: HookData) -> None:
    """初始化会话 - 记录当前终端窗口"""
    hwnd, title = get_foreground_window()

    if hwnd > 0:
        proc_result = get_window_process_name(hwnd)
        if isinstance(proc_result, tuple):
            process_name, pid = proc_result
        else:
            process_name = proc_result
            pid = 0
        print(f"记录终端窗口: hwnd={hwnd}, title={title}, process={process_name}, pid={pid}")
        save_session(hook_data.session_id, hwnd, title, process_name, pid)
    else:
        print("无法获取前台窗口，跳过记录")


def _load_session_or_latest(session_id: str):
    """
    按 session_id 加载会话，找不到时回退到最新会话。
    返回 (session_data, source) 或 (None, reason)。
    """
    session = load_session(session_id)
    if session:
        return session, "exact"

    # Fallback: CLAUDE_SESSION_ID 可能未正确传递
    fallback = find_latest_session()
    if fallback:
        print(f"使用最近会话代替（session_id={session_id} 未找到）")
        return fallback, "fallback"

    return None, "无会话记录"


def cmd_notify(hook_data: HookData) -> None:
    """发送通知 - 有待确认事件时直接通知"""
    # 检查去重
    if not should_send_notification():
        print("跳过通知（去重）")
        return

    # 加载会话（含回退）
    session, reason = _load_session_or_latest(hook_data.session_id)
    if not session:
        print(f"跳过通知（{reason}）")
        return

    saved_hwnd, saved_title, saved_process, saved_pid = session

    # 直接发送通知（不管是否离开终端）
    title = "Claude Code 需要确认"
    message = "你有一个待确认请求"

    success = send_toast_notification(title, message)
    if success:
        print("已发送通知")
        # 聚焦到终端窗口
        if saved_hwnd > 0:
            focus_window(saved_hwnd)
    else:
        print("发送通知失败")


def cmd_cleanup(hook_data: HookData) -> None:
    """清理会话"""
    delete_session(hook_data.session_id)
    print(f"已清理会话: {hook_data.session_id}")


def cmd_task_done(hook_data: HookData) -> None:
    """任务完成时发送通知"""
    # 检查去重
    if not should_send_notification():
        print("跳过通知（去重）")
        return

    # 加载会话（含回退）
    session, reason = _load_session_or_latest(hook_data.session_id)
    if not session:
        print(f"跳过通知（{reason}）")
        return

    saved_hwnd, saved_title, saved_process, saved_pid = session

    # 发送任务完成通知
    title = "任务已完成"
    message = "后台任务已完成，请查看结果"

    success = send_toast_notification(title, message)
    if success:
        print("已发送任务完成通知")
        # 聚焦到终端窗口
        if saved_hwnd > 0:
            focus_window(saved_hwnd)
    else:
        print("发送通知失败")


def main() -> None:
    """主入口"""
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    hook_data = HookData.from_stdin()

    if command == "init":
        cmd_init(hook_data)
    elif command == "notify":
        cmd_notify(hook_data)
    elif command == "task_done":
        cmd_task_done(hook_data)
    elif command == "auto":
        # 自动检测用户的输入，发送通知
        # 检测关键词：确定、确认、是否、可以吗、行吗
        import re
        stdin_data = sys.stdin.read()

        # 解析用户输入
        try:
            data = json.loads(stdin_data) if stdin_data else {}
            prompt = data.get("prompt", "")
        except:
            prompt = stdin_data

        # 检测是否需要确认（关键词匹配）
        confirm_keywords = [
            "确定", "确认", "可以吗", "行吗", "要继续吗", "继续吗",
            "是否", "好不好", "行不行", "同意吗", "要吗", "吗？",
            "yes/no", "y/n", "ok?", "continue?"
        ]

        need_confirm = any(kw in prompt.lower() for kw in confirm_keywords)

        # 也检测是否有 AskUserQuestion 在上下文中
        if "AskUserQuestion" in str(hook_data.matcher) or "permission" in prompt.lower():
            need_confirm = True

        if need_confirm:
            # 加载会话获取保存的 hwnd（发起请求的标签页）
            session = load_session(hook_data.session_id)
            if session:
                saved_hwnd, saved_title, saved_process, saved_pid = session
                target_hwnd = saved_hwnd
            else:
                # 如果没有 session，回退到当前前台窗口
                current_hwnd, current_title = get_foreground_window()
                target_hwnd = current_hwnd

            # 发送通知
            success = send_toast_notification("Claude Code 需要确认", "你有一个待确认请求")
            if success:
                print("已发送通知")
                # 聚焦到发起请求的标签页
                if target_hwnd > 0:
                    focus_window(target_hwnd)
        else:
            print("无需确认")
    elif command == "cleanup":
        cmd_cleanup(hook_data)
    elif command in ("--version", "-v"):
        print("win-terminal-notifier 0.1.0")
    else:
        print("用法: main.py <init|notify|task_done|auto|cleanup>")
        sys.exit(1)


if __name__ == "__main__":
    main()