# 视频格式转换工具

一个强大的Python视频格式转换工具，支持多种视频格式的批量转换。

## 功能特性

- 🎥 支持多种视频格式：mp4, mkv, avi, mov, flv, wmv, webm, mpeg, m4v
- ⚡ 并行处理支持，提高转换效率
- 📊 实时进度显示
- 📝 详细的日志记录
- 🔄 智能格式检测，跳过已是目标格式的文件
- 💪 两级转换策略：先尝试快速流复制，失败则重新编码
- 🎯 命令行和交互式两种使用模式
- 🖥️ 内置 FastAPI + HTML 界面，一键脚本即可体验 Web 端操作

## 依赖要求

- Python 3.7+
- FFmpeg (需要在系统PATH中)
- tqdm (进度条显示)
- FastAPI / Uvicorn / python-multipart（用于 Web 服务）

## 安装

1. 确保已安装 FFmpeg：
   ```bash
   # macOS (使用 Homebrew)
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # Windows (使用 Chocolatey)
   choco install ffmpeg
   ```

2. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 命令行模式

以下示例既可以使用 `python -m video_converter`（推荐方式），也可以直接运行仓库中的 `python video_converter.py`：

```bash
# 转换单个文件
python -m video_converter input.mkv --format mp4

# 批量转换文件夹中的所有视频
python -m video_converter /path/to/videos --format mp4

# 禁用并行处理
python -m video_converter /path/to/videos --format mp4 --no-parallel

# 设置最大工作线程数
python -m video_converter /path/to/videos --format mp4 --max-workers 8

# 设置日志级别
python -m video_converter input.mkv --format mp4 --log-level DEBUG
```

### 交互式模式

直接运行脚本进入交互模式：
```bash
python -m video_converter
# 或者
python video_converter.py
```

然后按提示输入目标格式和文件路径。

### Web 界面模式

```bash
python serve_app.py
# 或安装后使用全局命令
video-converter-serve
```

上述命令会启动本地 FastAPI 服务（默认 `http://127.0.0.1:8000/`），并自动在浏览器中打开内置的 HTML 界面。界面支持拖拽/多选文件上传，服务端会调用 `VideoConverter` 转换后立即返回新视频并自动触发下载。

常用参数：
- `--no-browser`：仅启动服务，不自动打开浏览器。
- `--host/--port`：自定义监听地址与端口。
- `--open-delay`：延迟打开浏览器，避免启动过快导致页面未加载成功。

## 示例

```bash
# 将 MKV 文件转换为 MP4
python -m video_converter movie.mkv --format mp4

# 批量转换文件夹，使用4个线程并行处理
python -m video_converter ./videos --format mp4 --max-workers 4

# 查看详细的转换过程
python -m video_converter movie.avi --format mp4 --log-level DEBUG
```

## 特性说明

### 智能转换策略
1. **格式检测**：自动检测文件是否已经是目标格式，跳过不必要的转换
2. **快速转换**：首先尝试使用流复制 (`-c copy`)，速度最快
3. **重新编码**：如果流复制失败，则使用指定编码器重新编码

### 并行处理
- 默认启用并行处理，充分利用多核CPU
- 可通过 `--max-workers` 调整线程数
- 使用 `--no-parallel` 可禁用并行处理

### 日志记录
- 自动生成 `video_conversion.log` 日志文件
- 支持多种日志级别：DEBUG, INFO, WARNING, ERROR
- 终端和文件同时输出日志

## 配置选项

可以通过修改代码中的 `ConversionConfig` 类来自定义：
- 支持的视频格式
- 默认视频编码器 (默认: libx264)
- 默认音频编码器 (默认: aac)
- 最大工作线程数 (默认: 4)

## HTML 界面模板

Web 服务默认托管在 `video_converter/resources/gui.html`，你也可以单独使用该页面：

- `serve_app.py` 会自动挂载该文件，并提供 `/api/convert`、`/api/formats` 等后端接口。
- 直接用浏览器打开文件时，可以体验前端交互，但需要自行实现对应的后端 API。
- 页面逻辑使用 `fetch` 上传文件并接收转换后的内容，方便与任意 Web 框架对接。
- 如果需要实时进度，可扩展 FastAPI 服务，使用 WebSocket 或 SSE 主动推送状态。

## 通过pip安装

可以使用pip直接从源码安装命令行工具：

```bash
# 安装到本地环境
pip install -e .

# 或构建后安装
pip install .
```

安装完成后可直接使用全局命令行入口：

```bash
# CLI 模式
video-converter input.mkv --format mp4

# 交互模式（运行后按提示输入）
video-converter

# Web 界面模式
video-converter-serve
```
