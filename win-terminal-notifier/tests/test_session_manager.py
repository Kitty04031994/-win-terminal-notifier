"""
会话管理模块测试
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 需要先 mock SESSION_DIR 以避免实际文件操作
from session_manager import (
    save_session,
    load_session,
    delete_session,
    should_send_notification,
    reset_dedup,
    DEDUP_WINDOW_SECONDS,
)
import session_manager


class TestSessionSaveLoad(unittest.TestCase):
    """T2.1: 测试会话保存和加载"""

    def setUp(self):
        # 使用临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = session_manager.SESSION_DIR
        session_manager.SESSION_DIR = Path(self.temp_dir)

    def tearDown(self):
        # 恢复并清理
        session_manager.SESSION_DIR = self.original_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_session(self):
        """T2.1: 保存后能正确读取"""
        session_id = "test_session_123"

        save_session(session_id, 12345, "PowerShell")
        session = load_session(session_id)

        self.assertIsNotNone(session)
        self.assertEqual(session[0], 12345)
        self.assertEqual(session[1], "PowerShell")

    def test_load_nonexistent_session(self):
        """T2.1: 不存在的会话返回 None"""
        session = load_session("nonexistent_session")
        self.assertIsNone(session)

    def test_delete_session(self):
        """T2.1: 删除会话后无法加载"""
        session_id = "test_session_456"

        save_session(session_id, 99999, "CMD")
        delete_session(session_id)

        session = load_session(session_id)
        self.assertIsNone(session)


class TestNotificationDedup(unittest.TestCase):
    """T4.4: 测试通知去重"""

    def setUp(self):
        reset_dedup()

    def test_first_notification_allowed(self):
        """T4.4: 首次通知应该发送"""
        result = should_send_notification()
        self.assertTrue(result)

    def test_duplicate_within_window_rejected(self):
        """T4.4: 2秒内重复通知应拒绝"""
        should_send_notification()  # 第一次
        result = should_send_notification()  # 第二次

        self.assertFalse(result)

    def test_notification_after_window_allowed(self):
        """T4.4: 超过2秒后应允许发送"""
        should_send_notification()  # 第一次

        # 模拟时间流逝 - 修改内部时间
        session_manager._last_notification_time = datetime.now() - timedelta(seconds=DEDUP_WINDOW_SECONDS + 1)

        result = should_send_notification()
        self.assertTrue(result)


class TestIsAwayFromTerminalLogic(unittest.TestCase):
    """T2.2-T2.5: 测试离开检测逻辑"""

    @patch('window_monitor.get_foreground_window')
    @patch('window_monitor.get_window_process_name')
    @patch('window_monitor.is_terminal_window')
    def test_is_away_different_window(self, mock_terminal, mock_process, mock_foreground):
        """T2.2: 切换到非终端应返回 True"""
        from window_monitor import is_away_from_terminal

        mock_foreground.return_value = (99999, "Google Chrome")
        mock_process.return_value = "chrome.exe"
        mock_terminal.return_value = False

        result = is_away_from_terminal(12345, "PowerShell")

        self.assertTrue(result)

    @patch('window_monitor.get_foreground_window')
    @patch('window_monitor.get_window_process_name')
    @patch('window_monitor.is_terminal_window')
    def test_is_away_back_to_terminal(self, mock_terminal, mock_process, mock_foreground):
        """T2.5: 回到终端返回 False"""
        from window_monitor import is_away_from_terminal

        mock_foreground.return_value = (12345, "PowerShell")
        mock_process.return_value = "powershell.exe"
        mock_terminal.return_value = True

        result = is_away_from_terminal(12345, "PowerShell")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()