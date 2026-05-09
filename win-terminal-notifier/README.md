# win-terminal-notifier

> Windows notification tool for Claude Code — alerts you when you step away from the terminal.
>
> Windows 终端离开通知器 —— 当你离开终端时，通过 Windows Toast 通知提醒你 Claude Code 需要确认。

---

## Features / 功能

- **Auto-detect leave** — detects when you switch away from terminal (CMD, PowerShell, Windows Terminal)
- **Windows Toast notification** — pops up when Claude Code needs your confirmation
- **Auto-focus** — click the notification to jump back to the terminal
- **2-second dedup** — prevents notification spam
- **Lightweight** — pure Python + Windows API (ctypes), no heavy dependencies

---

## Prerequisites / 前置条件

- **OS**: Windows 10+ (for Toast notification support)
- **Python**: 3.8+
- **Claude Code**: installed and configured
- **PowerShell**: available (for notification fallback)

---

## Installation / 安装

### Via pip (from local source)

```bash
git clone https://github.com/{your-username}/win-terminal-notifier.git
cd win-terminal-notifier
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

### Verify

```bash
python main.py --version
# win-terminal-notifier 0.1.0
```

---

## Integration with Claude Code / 集成到 Claude Code

Add the following hooks to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python \"{path_to}/win-terminal-notifier/main.py\" init"
      }]
    }],
    "Notification": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python \"{path_to}/win-terminal-notifier/main.py\" notify"
      }]
    }],
    "Stop": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python \"{path_to}/win-terminal-notifier/main.py\" cleanup"
      }]
    }]
  }
}
```

Replace `{path_to}` with the absolute path to the project directory.

> **Tip**: For better performance, use your full Python interpreter path (e.g., `C:/Users/yourname/AppData/Local/.../python.exe`).

---

## CLI Commands / 命令说明

| Command / 命令 | Description / 说明 |
|----------------|-------------------|
| `init`        | Record the current terminal window (called on SessionStart) / 记录当前终端窗口 |
| `notify`      | Send a notification when there's a pending request (called on Notification hook) / 有待确认时发通知 |
| `task_done`   | Notify when a background task completes / 后台任务完成时通知 |
| `auto`        | Auto-detect if user input needs confirmation and notify / 自动检测是否需要确认并通知 |
| `cleanup`     | Clean up session data (called on Stop) / 清理会话记录 |

---

## Running Tests / 运行测试

```bash
cd win-terminal-notifier
pip install pytest
pytest tests/ -v
```

Test coverage includes:

- **Window monitoring** — foreground window detection, terminal identification (CMD, PowerShell, Windows Terminal, Chrome, VS Code)
- **Leave detection** — switching away from / back to terminal
- **Notification** — toast sending, window focusing, deduplication
- **Session management** — save, load, delete, fallback
- **Integration** — end-to-end Claude Code hook simulation

---

## Project Structure / 项目结构

```
win-terminal-notifier/
├── LICENSE
├── README.md               # This file
├── pyproject.toml           # Package config
├── requirements.txt         # Dependencies
├── main.py                  # CLI entrypoint
├── window_monitor.py        # Window monitoring (Win32 API via ctypes)
├── session_manager.py       # Session persistence & dedup
├── notifier.py              # Toast notification & window focusing
├── test_msgbox.ps1          # PowerShell test helper
└── tests/
    ├── test_window_monitor.py
    ├── test_session_manager.py
    ├── test_notifier.py
    └── test_integration.py
```

---

## How It Works / 工作原理

1. **SessionStart** → `init` records the current terminal window (handle, title, process, PID) to a JSON file in `%TEMP%\win_terminal_notifier\`
2. **Notification hook** → `notify` checks if you've left the terminal window. If yes, sends a Windows Toast via PowerShell MessageBox
3. **Auto-focus** → after sending the notification, brings the terminal window to foreground
4. **Dedup** → skips notifications that fire within 2 seconds of the last one
5. **Stop** → `cleanup` removes the session file

Inspiration: [cc-notifier](https://github.com/1rgs/cc-notifier)

---

## License / 许可证

MIT
