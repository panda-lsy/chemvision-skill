"""ChemVision Skill 服务生命周期管理

安全的后台进程管理，不干扰 QwenPaw 主进程。
不使用任何 HTTP 请求（避免安全扫描误报），仅通过 PID 文件和端口检测管理。

用法:
    python manage.py start    # 后台启动服务
    python manage.py stop     # 优雅停止服务
    python manage.py restart  # 重启
    python manage.py status   # 查看状态
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

# PID 文件存放位置（与 manage.py 同目录）
PID_FILE = Path(__file__).parent / ".chemskill.pid"
LOG_FILE = Path(__file__).parent / ".chemskill.log"
PORT = 8899


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _write_pid(pid: int) -> None:
    PID_FILE.write_text(str(pid))


def _remove_pid() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def _is_running(pid: int) -> bool:
    """检查进程是否存活（不发网络请求）"""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def _port_open(port: int, timeout: float = 1.0) -> bool:
    """检查端口是否在监听（纯 socket，不发 HTTP 请求）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def start() -> dict:
    """后台启动化学服务"""
    existing_pid = _read_pid()
    if existing_pid and _is_running(existing_pid):
        if _port_open(PORT):
            return {"status": "already_running", "pid": existing_pid, "port": PORT}
        # 进程在但端口没开，可能还在启动中
        return {"status": "starting", "pid": existing_pid, "port": PORT}

    _remove_pid()

    log_fd = open(LOG_FILE, "a", encoding="utf-8")

    if sys.platform == "win32":
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        proc = subprocess.Popen(
            [sys.executable, "-m", "chemskill.server"],
            cwd=str(Path(__file__).parent),
            stdout=log_fd,
            stderr=log_fd,
            creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "chemskill.server"],
            cwd=str(Path(__file__).parent),
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True,
            close_fds=True,
        )

    _write_pid(proc.pid)

    # 等待端口就绪（最多 10 秒）
    for _ in range(20):
        time.sleep(0.5)
        if _port_open(PORT):
            return {"status": "started", "pid": proc.pid, "port": PORT}

    return {"status": "started_pending", "pid": proc.pid, "port": PORT, "note": "服务启动中，稍后会就绪"}


def stop() -> dict:
    """停止化学服务"""
    pid = _read_pid()
    if not pid:
        return {"status": "not_running", "note": "未找到 PID 文件"}

    if not _is_running(pid):
        _remove_pid()
        return {"status": "not_running", "note": f"进程 {pid} 已不存在"}

    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            if _is_running(pid):
                os.kill(pid, signal.SIGKILL)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    _remove_pid()
    return {"status": "stopped", "pid": pid}


def status() -> dict:
    """查询服务状态（不发 HTTP 请求）"""
    pid = _read_pid()
    if not pid:
        return {"status": "not_running", "pid_file": False}

    if not _is_running(pid):
        _remove_pid()
        return {"status": "not_running", "pid": pid, "note": "进程已退出"}

    if _port_open(PORT):
        return {"status": "running", "pid": pid, "port": PORT}

    return {"status": "running_unverified", "pid": pid, "port": PORT, "note": "进程存活但端口未就绪"}


def restart() -> dict:
    stop_result = stop()
    time.sleep(1)
    start_result = start()
    return {"stop": stop_result, "start": start_result}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python manage.py [start|stop|restart|status]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    actions = {"start": start, "stop": stop, "restart": restart, "status": status}

    if cmd not in actions:
        print(f"未知命令: {cmd}，可选: {', '.join(actions.keys())}")
        sys.exit(1)

    result = actions[cmd]()
    print(json.dumps(result, indent=2, ensure_ascii=False))
