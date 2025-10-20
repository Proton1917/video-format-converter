#!/usr/bin/env python3
"""
启动本地视频转换 Web 服务并自动打开浏览器。
"""

from __future__ import annotations

import argparse
import threading
import time
import webbrowser

import uvicorn


def _launch_browser(url: str, delay: float) -> None:
    """稍后打开浏览器，避免服务器尚未完成启动。"""
    time.sleep(max(delay, 0.0))
    webbrowser.open(url)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="启动视频转换 Web 服务（FastAPI + 前端页面）",
    )
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="监听端口 (默认: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="启动后不自动打开浏览器",
    )
    parser.add_argument(
        "--open-delay",
        type=float,
        default=1.5,
        help="打开浏览器前的延迟秒数 (默认: 1.5)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="uvicorn 日志级别 (默认: info)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    url = f"http://{args.host}:{args.port}/"
    print(f"[video-converter] 启动服务中，完成后可访问: {url}")

    if not args.no_browser:
        threading.Thread(
            target=_launch_browser,
            args=(url, args.open_delay),
            daemon=True,
        ).start()

    uvicorn.run(
        "video_converter.webapp:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
