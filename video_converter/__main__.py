"""
应用程序入口点（命令行与交互模式）
"""
import argparse
import logging
import os
import sys

from video_converter.core.converter import ConversionConfig, VideoConverter

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="视频格式转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python -m video_converter input.mkv --format mp4
  python -m video_converter /path/to/videos --format mp4 --parallel
  python -m video_converter input.avi --format mp4 --no-parallel
        """
    )

    # 输入路径可选；为空则进入交互模式
    parser.add_argument(
        "input",
        nargs="?",
        help="输入文件或文件夹路径（留空进入交互模式）"
    )

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

def cli_mode(args):
    """命令行模式"""
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # 创建配置和转换器
    config = ConversionConfig(max_workers=args.max_workers)
    converter = VideoConverter(config)

    input_path = args.input
    target_format = args.format

    if input_path is None:
        logging.error("请提供输入文件或文件夹路径，或者不带参数进入交互模式。")
        sys.exit(1)

    if os.path.isdir(input_path):
        results = converter.convert_folder(input_path, target_format, args.parallel)

        # 显示统计信息
        stats = converter.get_conversion_stats(results)
        logging.info(f"转换完成 - 成功: {stats['successful']}, 失败: {stats['failed']}, 成功率: {stats['success_rate']:.1f}%")

        # 如果有失败的文件，退出码为1
        if stats['failed'] > 0:
            sys.exit(1)

    elif os.path.isfile(input_path):
        result = converter.convert_video(input_path, target_format)
        if not result.success:
            logging.error(f"转换失败: {result.error_message}")
            sys.exit(1)
    else:
        logging.error(f"无效的路径: {input_path}")
        sys.exit(1)

def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 没有提供输入路径，使用交互模式
    if args.input is None:
        interactive_mode()
    else:
        cli_mode(args)

if __name__ == "__main__":
    main()
