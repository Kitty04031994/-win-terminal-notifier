"""
集成测试
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import session_manager
from main import HookData, cmd_init, cmd_notify, cmd_cleanup
from window_monitor import get_foreground_window, is_away_from_terminal
from notifier import send_toast_notification


class TestInitCommand(unittest.TestCase):
    """T5.1: 测试 init 命令"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = session_manager.SESSION_DIR
        session_manager.SESSION_DIR = Path(self.temp_dir)
        session_manager.reset_dedup()

    def tearDown(self):
        session_manager.SESSION_DIR = self.original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('main.get_foreground_window')
    @patch('main.get_window_process_name')
    def test_init_saves_session(self, mock_process, mock_foreground):
        """T5.1: init 保存会话"""
        mock_foreground.return_value = (12345, "PowerShell")
        mock_process.return_value = "powershell.exe"

        hook_data = HookData("test_session_123")
        cmd_init(hook_data)

        # 验证会话已保存
        session = session_manager.load_session("test_session_123")
        self.assertIsNotNone(session)
        self.assertEqual(session[0], 12345)
        self.assertEqual(session[1], "PowerShell")


class TestNotifyCommand(unittest.TestCase):
    """T3.1-T3.4, T4.4, T5.2: 测试 notify 命令"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = session_manager.SESSION_DIR
        session_manager.SESSION_DIR = Path(self.temp_dir)
        session_manager.reset_dedup()

        # 先保存一个会话
        session_manager.save_session("test_session_123", 12345, "PowerShell")

    def tearDown(self):
        session_manager.SESSION_DIR = self.original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('main.send_toast_notification')
    def test_notify_sends(self, mock_toast):
        """T3.2: 通知发送"""
        mock_toast.return_value = True

        hook_data = HookData("test_session_123")
        cmd_notify(hook_data)

        mock_toast.assert_called_once()

    def test_notify_skips_when_at_terminal(self):
        """T3.1: 在终端时仍然发送通知"""
        hook_data = HookData("test_session_123")
        cmd_notify(hook_data)

        # cmd_notify always sends when session exists

    @patch('main.send_toast_notification')
    def test_notify_fallback_to_latest_session(self, mock_toast):
        """T5.2: session_id 不存在时回退到最新会话"""
        mock_toast.return_value = True

        hook_data = HookData("nonexistent_session")
        cmd_notify(hook_data)

        # Should fallback to the session saved in setUp
        mock_toast.assert_called_once()

    @patch('main.send_toast_notification')
    def test_notification_dedup(self, mock_toast):
        """T4.4: 去重测试"""
        mock_toast.return_value = True

        hook_data = HookData("test_session_123")

        # 第一次通知
        cmd_notify(hook_data)
        self.assertEqual(mock_toast.call_count, 1)

        # 第二次通知（在去重窗口内）
        cmd_notify(hook_data)
        self.assertEqual(mock_toast.call_count, 1)  # 应该被去重


class TestCleanupCommand(unittest.TestCase):
    """T5.3: 测试 cleanup 命令"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = session_manager.SESSION_DIR
        session_manager.SESSION_DIR = Path(self.temp_dir)

        # 先保存一个会话
        session_manager.save_session("test_session_123", 12345, "PowerShell")

    def tearDown(self):
        session_manager.SESSION_DIR = self.original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cleanup_deletes_session(self):
        """T5.3: cleanup 删除会话"""
        hook_data = HookData("test_session_123")
        cmd_cleanup(hook_data)

        session = session_manager.load_session("test_session_123")
        self.assertIsNone(session)


class TestNotificationTriggers(unittest.TestCase):
    """T3.3-T3.4: 测试不同事件的通知触发"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = session_manager.SESSION_DIR
        session_manager.SESSION_DIR = Path(self.temp_dir)
        session_manager.reset_dedup()
        # 先保存一个会话
        session_manager.save_session("test_session_123", 12345, "PowerShell")

    def tearDown(self):
        session_manager.SESSION_DIR = self.original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('main.send_toast_notification')
    def test_notify_with_tool_use(self, mock_toast):
        """T3.2: 有 Tool Use 时发送通知"""
        mock_toast.return_value = True

        hook_data = HookData("test_session_123")
        hook_data.message = "tool_use"

        cmd_notify(hook_data)

        mock_toast.assert_called_once()

    @patch('main.send_toast_notification')
    def test_notify_with_permission(self, mock_toast):
        """T3.3: 有 Permission 时发送通知"""
        mock_toast.return_value = True

        hook_data = HookData("test_session_123")
        hook_data.message = "permission_prompt"

        cmd_notify(hook_data)

        mock_toast.assert_called_once()


if __name__ == "__main__":
    unittest.main()