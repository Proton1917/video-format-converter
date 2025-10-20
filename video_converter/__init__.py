"""
Python视频格式转换工具包

提供视频格式转换和处理功能，支持命令行和HTML界面模板。
"""

__version__ = "1.0.0"
name = "video_converter"

from video_converter.core.converter import VideoConverter, ConversionConfig, ConversionResult
