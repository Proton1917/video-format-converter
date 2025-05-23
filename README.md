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

## 依赖要求

- Python 3.7+
- FFmpeg (需要在系统PATH中)
- tqdm (进度条显示)

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

```bash
# 转换单个文件
python video_converter.py input.mkv --format mp4

# 批量转换文件夹中的所有视频
python video_converter.py /path/to/videos --format mp4

# 禁用并行处理
python video_converter.py /path/to/videos --format mp4 --no-parallel

# 设置最大工作线程数
python video_converter.py /path/to/videos --format mp4 --max-workers 8

# 设置日志级别
python video_converter.py input.mkv --format mp4 --log-level DEBUG
```

### 交互式模式

直接运行脚本进入交互模式：
```bash
python video_converter.py
```

然后按提示输入目标格式和文件路径。

## 示例

```bash
# 将 MKV 文件转换为 MP4
python video_converter.py movie.mkv --format mp4

# 批量转换文件夹，使用4个线程并行处理
python video_converter.py ./videos --format mp4 --max-workers 4

# 查看详细的转换过程
python video_converter.py movie.avi --format mp4 --log-level DEBUG
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

## 注意事项

1. 确保有足够的磁盘空间存储转换后的文件
2. 转换后的文件会添加时间戳后缀，不会覆盖原文件
3. 大文件转换可能需要较长时间，请耐心等待
4. 如果转换失败，请检查 FFmpeg 是否正确安装

## 许可证

MIT License
