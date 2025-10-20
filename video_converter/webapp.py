"""
FastAPI 应用：提供文件上传转换接口并托管前端页面。
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from video_converter.core.converter import ConversionConfig, VideoConverter

logger = logging.getLogger(__name__)

PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCES_DIR = PACKAGE_ROOT / "resources"
GUI_FILE = RESOURCES_DIR / "gui.html"

VIDEO_MIME_TYPES: Dict[str, str] = {
    "mp4": "video/mp4",
    "mkv": "video/x-matroska",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "flv": "video/x-flv",
    "wmv": "video/x-ms-wmv",
    "webm": "video/webm",
    "mpeg": "video/mpeg",
    "m4v": "video/x-m4v",
}


def create_app() -> FastAPI:
    """创建 FastAPI 应用。"""
    app = FastAPI(title="Video Converter API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if RESOURCES_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=RESOURCES_DIR),
            name="static",
        )

    @app.get("/", response_class=FileResponse)
    async def index() -> Response:
        """返回前端页面。"""
        if not GUI_FILE.exists():
            raise HTTPException(status_code=404, detail="前端页面缺失")
        return FileResponse(GUI_FILE)

    @app.get("/api/formats")
    async def list_formats() -> JSONResponse:
        """返回支持的视频格式列表。"""
        config = ConversionConfig()
        return JSONResponse(
            {
                "default": config.supported_formats[0] if config.supported_formats else "mp4",
                "formats": config.supported_formats or [],
            }
        )

    @app.post("/api/convert")
    async def convert_video(
        background: BackgroundTasks,
        file: UploadFile = File(...),
        target_format: str = Form("mp4"),
        max_workers: int = Form(4),
        use_parallel: bool = Form(True),
        output_folder: Optional[str] = Form(None),
    ) -> FileResponse:
        """上传视频并转换成指定格式，返回转换后的文件。"""
        target_format = target_format.lower().strip()
        config = ConversionConfig(max_workers=max_workers)

        if target_format not in (config.supported_formats or []):
            raise HTTPException(status_code=400, detail=f"不支持的目标格式: {target_format}")

        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名缺失")

        temp_dir = Path(tempfile.mkdtemp(prefix="video_converter_"))
        input_path = temp_dir / file.filename

        logger.info("接收到文件: %s -> %s", file.filename, input_path)

        # 将上传内容写入临时文件
        try:
            with open(input_path, "wb") as buffer:
                while chunk := await file.read(8 * 1024 * 1024):
                    buffer.write(chunk)
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error("写入临时文件失败: %s", exc)
            raise HTTPException(status_code=500, detail="写入临时文件失败") from exc
        finally:
            await file.close()

        # 定义转换函数，在线程池中执行
        requested_output_dir: Optional[Path] = None
        if output_folder:
            candidate = Path(output_folder).expanduser()
            if candidate.exists() and candidate.is_dir():
                requested_output_dir = candidate
                logger.info("用户指定输出目录: %s", requested_output_dir)
            else:
                logger.warning("忽略无效的输出目录: %s", output_folder)

        if not use_parallel:
            logger.info("收到禁用并行参数，单文件转换将顺序执行")

        def _do_convert() -> Path:
            converter = VideoConverter(ConversionConfig(max_workers=max_workers))
            result = converter.convert_video(str(input_path), target_format=target_format)
            if not result.success or not result.output_path:
                msg = result.error_message or "转换失败"
                raise HTTPException(status_code=500, detail=msg)
            output = Path(result.output_path)
            if requested_output_dir:
                destination = requested_output_dir / output.name
                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(output), destination)
                    logger.info("输出文件已移动到 %s", destination)
                    return destination
                except Exception as move_exc:  # noqa: BLE001
                    logger.warning("移动输出文件失败，使用默认位置: %s", move_exc)
            return output

        try:
            output_path = await run_in_threadpool(_do_convert)
        except HTTPException:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        except Exception as exc:  # noqa: BLE001
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.exception("转换失败: %s", exc)
            raise HTTPException(status_code=500, detail="服务器转换失败") from exc

        media_type = VIDEO_MIME_TYPES.get(target_format, "application/octet-stream")
        download_name = output_path.name

        # 转换完成后再删除临时目录
        background.add_task(shutil.rmtree, temp_dir, ignore_errors=True)

        logger.info("转换完成: %s -> %s", input_path.name, download_name)

        return FileResponse(
            path=output_path,
            media_type=media_type,
            filename=download_name,
            background=background,
        )

    return app


app = create_app()

__all__ = ["app", "create_app"]
