import os
import sys
import datetime
import subprocess
import logging
import argparse
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


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="视频格式转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python 格式转换.py input.mkv --format mp4
  python 格式转换.py /path/to/videos --format mp4 --parallel
  python 格式转换.py input.avi --format mp4 --no-parallel
        """
    )
    
    parser.add_argument("input", help="输入文件或文件夹路径")
    parser.add_argument(
        "-f", "--format", 
        default="mp4",
        choices=ConversionConfig().supported_formats or [],
        help="目标视频格式 (默认: mp4)"
    )
    parser.add_argument(
        "--parallel", 
        action="store_true", 
        default=True,
        help="使用并行处理 (默认启用)"
    )
    parser.add_argument(
        "--no-parallel", 
        action="store_false", 
        dest="parallel",
        help="禁用并行处理"
    )
    parser.add_argument(
        "--max-workers", 
        type=int, 
        default=4,
        help="最大并行工作线程数 (默认: 4)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    
    return parser


def interactive_mode():
    """交互模式"""
    print("=== 视频格式转换工具 ===")
    
    config = ConversionConfig()
    converter = VideoConverter(config)
    
    # 获取目标格式
    print(f"支持的格式: {', '.join(config.supported_formats or [])}")
    while True:
        target_format = input("请输入目标格式: ").strip().lower()
        if target_format in (config.supported_formats or []):
            break
        print(f"不支持的格式，请选择: {', '.join(config.supported_formats or [])}")
    
    # 获取输入路径
    while True:
        input_path = input("请输入视频文件或文件夹路径: ").strip().strip("'").strip('"')
        if os.path.exists(input_path):
            break
        print("路径不存在，请重新输入")
    
    # 处理转换
    if os.path.isdir(input_path):
        use_parallel = input("是否使用并行处理? (y/n, 默认y): ").strip().lower()
        use_parallel = use_parallel != 'n'
        
        results = converter.convert_folder(input_path, target_format, use_parallel)
        
        # 显示统计信息
        stats = converter.get_conversion_stats(results)
        print(f"\n=== 转换完成 ===")
        print(f"总文件数: {stats['total_files']}")
        print(f"成功: {stats['successful']}")
        print(f"失败: {stats['failed']}")
        print(f"成功率: {stats['success_rate']:.1f}%")
        print(f"总用时: {stats['total_processing_time']:.2f}秒")
        
        if stats['failed'] > 0:
            print("\n失败的文件:")
            for result in results:
                if not result.success:
                    print(f"  - {result.input_path}: {result.error_message}")
                    
    elif os.path.isfile(input_path):
        result = converter.convert_video(input_path, target_format)
        if result.success:
            print(f"转换成功: {result.output_path}")
        else:
            print(f"转换失败: {result.error_message}")
    else:
        print("无效的路径")


def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 没有命令行参数，使用交互模式
        interactive_mode()
        return
    
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # 创建配置和转换器
    config = ConversionConfig(max_workers=args.max_workers)
    converter = VideoConverter(config)
    
    input_path = args.input
    target_format = args.format
    
    if os.path.isdir(input_path):
        results = converter.convert_folder(input_path, target_format, args.parallel)
        
        # 显示统计信息
        stats = converter.get_conversion_stats(results)
        logger.info(f"转换完成 - 成功: {stats['successful']}, 失败: {stats['failed']}, 成功率: {stats['success_rate']:.1f}%")
        
        # 如果有失败的文件，退出码为1
        if stats['failed'] > 0:
            sys.exit(1)
            
    elif os.path.isfile(input_path):
        result = converter.convert_video(input_path, target_format)
        if not result.success:
            logger.error(f"转换失败: {result.error_message}")
            sys.exit(1)
    else:
        logger.error(f"无效的路径: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()