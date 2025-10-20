"""
视频转换核心模块
"""

import os
import sys
import datetime
import subprocess
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import shutil
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ConversionConfig:
    """视频转换配置类"""
    supported_formats: Optional[List[str]] = None
    supported_extensions: Optional[List[str]] = None
    default_video_codec: str = "libx264"
    default_audio_codec: str = "aac"
    max_workers: int = 4
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ["mp4", "mkv", "avi", "mov", "flv", "wmv", "webm", "mpeg", "m4v"]
        if self.supported_extensions is None:
            self.supported_extensions = [f".{fmt}" for fmt in self.supported_formats]

@dataclass
class ConversionResult:
    """转换结果类"""
    success: bool
    input_path: str
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None

class VideoConverter:
    """视频格式转换器类"""
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        self.config = config or ConversionConfig()
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """检查ffmpeg是否可用"""
        if not shutil.which("ffmpeg"):
            logger.error("ffmpeg未找到，请确保已安装ffmpeg并添加到PATH中")
            sys.exit(1)
        return True
    
    def _is_same_format(self, input_path: str, target_format: str) -> bool:
        """检查输入文件是否已经是目标格式"""
        _, file_ext = os.path.splitext(input_path)
        return file_ext.lower().lstrip('.') == target_format.lower()
    
    def _generate_output_path(self, input_path: str, target_format: str) -> str:
        """生成输出文件路径"""
        file_root, _ = os.path.splitext(input_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{file_root}_{timestamp}.{target_format}"
    
    def _run_ffmpeg_command(self, cmd: List[str], input_path: str) -> bool:
        """执行ffmpeg命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"ffmpeg命令执行成功: {' '.join(cmd)}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg命令执行失败: {e.stderr}")
            return False
    
    def convert_video(self, input_path: str, target_format: str = "mp4") -> ConversionResult:
        """
        转换单个视频文件到指定格式
        Args:
            input_path (str): 输入视频文件路径
            target_format (str): 目标视频格式
        Returns:
            ConversionResult: 转换结果
        """
        start_time = datetime.datetime.now()
        
        # 验证目标格式
        if target_format not in (self.config.supported_formats or []):
            error_msg = f"不支持的目标格式: {target_format}. 支持的格式: {', '.join(self.config.supported_formats or [])}"
            logger.error(error_msg)
            return ConversionResult(False, input_path, error_message=error_msg)

        # 验证输入文件
        if not os.path.isfile(input_path):
            error_msg = f"文件不存在: {input_path}"
            logger.error(error_msg)
            return ConversionResult(False, input_path, error_message=error_msg)

        # 检查是否已经是目标格式
        if self._is_same_format(input_path, target_format):
            info_msg = f"跳过转换 {input_path}: 已经是 {target_format} 格式"
            logger.info(info_msg)
            return ConversionResult(True, input_path, output_path=input_path, error_message=info_msg)

        # 生成输出文件路径
        output_file = self._generate_output_path(input_path, target_format)
        
        # 尝试直接复制流（速度更快）
        logger.info(f"开始转换 {input_path} 到 {output_file}")
        copy_cmd = ["ffmpeg", "-i", input_path, "-c", "copy", "-y", output_file]
        
        if self._run_ffmpeg_command(copy_cmd, input_path):
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(f"转换完成: {output_file} (用时: {processing_time:.2f}秒)")
            return ConversionResult(True, input_path, output_file, processing_time=processing_time)
        
        # 如果直接复制失败，尝试重新编码
        logger.warning(f"直接转换失败，开始重新编码 {input_path}")
        encode_cmd = [
            "ffmpeg", "-i", input_path, 
            "-c:v", self.config.default_video_codec, 
            "-c:a", self.config.default_audio_codec, 
            "-y", output_file
        ]
        
        if self._run_ffmpeg_command(encode_cmd, input_path):
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(f"重新编码完成: {output_file} (用时: {processing_time:.2f}秒)")
            return ConversionResult(True, input_path, output_file, processing_time=processing_time)
        else:
            error_msg = f"转换失败: {input_path}"
            logger.error(error_msg)
            return ConversionResult(False, input_path, error_message=error_msg)
    
    def convert_folder(self, folder_path: str, target_format: str = "mp4", use_parallel: bool = True) -> List[ConversionResult]:
        """
        转换文件夹中的所有视频文件
        Args:
            folder_path (str): 文件夹路径
            target_format (str): 目标格式
            use_parallel (bool): 是否使用并行处理
        Returns:
            List[ConversionResult]: 转换结果列表
        """
        if not os.path.isdir(folder_path):
            error_msg = f"文件夹不存在: {folder_path}"
            logger.error(error_msg)
            return [ConversionResult(False, folder_path, error_message=error_msg)]
        
        # 收集所有视频文件
        video_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[-1].lower()
                if file_ext in (self.config.supported_extensions or []):
                    video_files.append(file_path)
        
        if not video_files:
            logger.warning(f"在 {folder_path} 中未找到支持的视频文件")
            return []
        
        logger.info(f"找到 {len(video_files)} 个视频文件")
        results = []
        
        if use_parallel and len(video_files) > 1:
            # 并行处理
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.convert_video, file_path, target_format): file_path 
                    for file_path in video_files
                }
                
                with tqdm(total=len(video_files), desc="转换进度") as pbar:
                    for future in as_completed(future_to_file):
                        result = future.result()
                        results.append(result)
                        pbar.update(1)
                        
                        if result.success:
                            pbar.set_postfix({"最近完成": os.path.basename(result.input_path)})
        else:
            # 顺序处理
            with tqdm(video_files, desc="转换进度") as pbar:
                for file_path in pbar:
                    pbar.set_postfix({"当前": os.path.basename(file_path)})
                    result = self.convert_video(file_path, target_format)
                    results.append(result)
        
        return results
    
    def get_conversion_stats(self, results: List[ConversionResult]) -> Dict[str, float]:
        """获取转换统计信息"""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        total_time = sum(r.processing_time for r in successful if r.processing_time)
        
        return {
            "total_files": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100 if results else 0,
            "total_processing_time": total_time,
            "average_time_per_file": total_time / len(successful) if successful else 0
        }
