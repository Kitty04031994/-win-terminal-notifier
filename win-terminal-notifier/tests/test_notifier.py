"""
通知模块测试
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifier import send_toast_notification, focus_window, send_notification_with_action


class TestSendToastNotification(unittest.TestCase):
    """T4.1: 测试发送 Toast 通知"""

    @patch('subprocess.run')
    def test_send_toast_notification_success(self, mock_run):
        """T4.1: 能发送通知"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = send_toast_notification("测试标题", "测试内容")

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_send_toast_notification_failure(self, mock_run):
        """T4.1: 发送失败返回 False"""
        mock_run.side_effect = Exception("PowerShell 错误")

        result = send_toast_notification("测试标题", "测试内容")

        self.assertFalse(result)


class TestFocusWindow(unittest.TestCase):
    """T4.2: 测试窗口聚焦"""

    @patch('notifier.ShowWindow')
    @patch('notifier.SetForegroundWindow')
    def test_focus_window_success(self, mock_set_fg, mock_show):
        """T4.2: 能聚焦窗口"""
        mock_set_fg.return_value = 1  # 非零表示成功
        mock_show.return_value = 1

        result = focus_window(12345)

        self.assertTrue(result)
        mock_show.assert_called_once()
        mock_set_fg.assert_called_once()

    @patch('notifier.SetForegroundWindow')
    def test_focus_window_invalid_handle(self, mock_set_fg):
        """T4.2: 无效句柄返回 False"""
        result = focus_window(0)

        self.assertFalse(result)
        mock_set_fg.assert_not_called()

    @patch('notifier.SetForegroundWindow')
    def test_focus_window_failure(self, mock_set_fg):
        """T4.2: 聚焦失败返回 False"""
        mock_set_fg.return_value = 0  # 失败

        result = focus_window(12345)

        self.assertFalse(result)


class TestNotificationWithAction(unittest.TestCase):
    """T4.1-T4.3: 测试带操作的通知"""

    @patch('notifier.send_toast_notification')
    @patch('notifier.focus_window')
    def test_send_notification_with_action(self, mock_focus, mock_toast):
        """T4.1-T4.3: 发送通知并聚焦"""
        mock_toast.return_value = True
        mock_focus.return_value = True

        send_notification_with_action("标题", "内容", 12345)

        mock_toast.assert_called_once_with("标题", "内容")
        mock_focus.assert_called_once_with(12345)

    @patch('notifier.send_toast_notification')
    @patch('notifier.focus_window')
    def test_send_notification_without_focus_on_failure(self, mock_focus, mock_toast):
        """T4.1: 发送失败不尝试聚焦"""
        mock_toast.return_value = False

        send_notification_with_action("标题", "内容", 12345)

        mock_focus.assert_not_called()


if __name__ == "__main__":
    unittest.main()