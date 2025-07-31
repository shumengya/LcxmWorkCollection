#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片水印添加工具
支持单张图片和批量处理，使用多线程提高处理效率
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import argparse
from typing import List, Tuple, Optional

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

# 线程锁用于打印
print_lock = threading.Lock()

def safe_print(message):
    """线程安全的打印函数"""
    with print_lock:
        print(message)

def get_background_brightness(img: Image.Image, margin: int = 20) -> float:
    """
    获取图片右下角区域的平均亮度
    
    Args:
        img: PIL图片对象
        margin: 边距
    
    Returns:
        亮度值 (0-255)
    """
    # 转换为灰度图像以计算亮度
    gray_img = img.convert('L')
    
    # 获取右下角区域
    width, height = gray_img.size
    sample_width = min(100, width // 4)  # 采样区域宽度
    sample_height = min(50, height // 4)  # 采样区域高度
    
    # 计算采样区域的坐标
    left = width - sample_width - margin
    top = height - sample_height - margin
    right = width - margin
    bottom = height - margin
    
    # 确保坐标在有效范围内
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)
    
    # 裁剪右下角区域
    sample_region = gray_img.crop((left, top, right, bottom))
    
    # 计算平均亮度
    pixels = list(sample_region.getdata())
    if pixels:
        avg_brightness = sum(pixels) / len(pixels)
    else:
        avg_brightness = 128  # 默认中等亮度
    
    return avg_brightness

def add_watermark(input_path: str, output_path: str, watermark_text: str = "灵创新媒", 
                 font_size: int = 0, opacity: int = 128, margin: int = 20) -> Tuple[bool, str]:
    """
    为单张图片添加水印
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        watermark_text: 水印文字
        font_size: 字体大小 (0表示自动根据图片尺寸计算)
        opacity: 透明度 (0-255)
        margin: 边距
    
    Returns:
        (成功标志, 错误信息)
    """
    try:
        # 打开原图
        with Image.open(input_path) as img:
            # 转换为RGBA模式以支持透明度
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 自动计算字体大小（如果font_size为0）
            if font_size == 0:
                # 根据图片的最小边长来计算字体大小
                min_dimension = min(img.width, img.height)
                font_size = max(20, min_dimension // 15)  # 最小20像素，最大为最小边长的1/15
            
            # 创建透明图层用于绘制水印
            watermark_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)
            
            # 尝试使用系统字体，如果失败则使用默认字体
            try:
                # Windows系统字体路径
                font_paths = [
                    'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
                    'C:/Windows/Fonts/simhei.ttf',  # 黑体
                    'C:/Windows/Fonts/simsun.ttc',  # 宋体
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        break
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # 获取文字尺寸
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 计算水印位置（右下角，向上调整一些）
            x = img.width - text_width - margin
            y = img.height - text_height - margin * 3  # 向上调整，增加边距
            
            # 检测背景亮度并选择合适的水印颜色
            bg_brightness = get_background_brightness(img, margin)
            if bg_brightness > 128:  # 背景偏亮，使用黑色水印
                watermark_color = (0, 0, 0, 200)  # 增加不透明度，使颜色更深
            else:  # 背景偏暗，使用白色水印
                watermark_color = (255, 255, 255, 200)  # 增加不透明度，使颜色更深
            
            # 绘制水印文字
            draw.text((x, y), watermark_text, font=font, fill=watermark_color)
            
            # 合并图层
            watermarked_img = Image.alpha_composite(img, watermark_layer)
            
            # 如果原图不是RGBA格式，转换回原格式
            original_img = Image.open(input_path)
            if original_img.mode != 'RGBA':
                watermarked_img = watermarked_img.convert(original_img.mode)
            
            # 保存图片
            watermarked_img.save(output_path, quality=95, optimize=True)
            
        return True, ""
        
    except Exception as e:
        return False, str(e)

def process_single_image(args) -> Tuple[str, bool, str]:
    """
    处理单张图片的包装函数，用于多线程
    
    Args:
        args: (input_path, output_path, watermark_text, font_size, opacity, margin)
    
    Returns:
        (文件名, 成功标志, 错误信息)
    """
    input_path, output_path, watermark_text, font_size, opacity, margin = args
    filename = os.path.basename(input_path)
    
    success, error_msg = add_watermark(input_path, output_path, watermark_text, 
                                     font_size, opacity, margin)
    
    if success:
        safe_print(f"✅ 已处理: {filename}")
    else:
        safe_print(f"❌ 处理失败 {filename}: {error_msg}")
    
    return filename, success, error_msg

def get_image_files(directory: str) -> List[str]:
    """
    递归获取目录下所有图片文件，过滤掉compressed文件夹
    
    Args:
        directory: 目录路径
    
    Returns:
        图片文件路径列表
    """
    image_files = []
    
    for root, dirs, files in os.walk(directory):
        # 过滤掉compressed文件夹
        if 'compressed' in dirs:
            dirs.remove('compressed')
        
        for file in files:
            if Path(file).suffix.lower() in SUPPORTED_FORMATS:
                image_files.append(os.path.join(root, file))
    
    return image_files

def process_directory(input_dir: str, output_dir: str, watermark_text: str = "灵创新媒",
                     font_size: int = 0, opacity: int = 128, margin: int = 20,
                     max_workers: int = 4) -> None:
    """
    批量处理目录下的所有图片
    
    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        watermark_text: 水印文字
        font_size: 字体大小
        opacity: 透明度
        margin: 边距
        max_workers: 最大线程数
    """
    # 获取所有图片文件
    image_files = get_image_files(input_dir)
    
    if not image_files:
        print(f"❌ 在目录 {input_dir} 中未找到支持的图片文件")
        return
    
    print(f"📁 找到 {len(image_files)} 个图片文件")
    print(f"🚀 开始批量处理，使用 {max_workers} 个线程...")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 准备任务参数
    tasks = []
    for input_path in image_files:
        # 保持相对路径结构
        rel_path = os.path.relpath(input_path, input_dir)
        output_path = os.path.join(output_dir, rel_path)
        
        # 创建输出文件的目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        tasks.append((input_path, output_path, watermark_text, font_size, opacity, margin))
    
    # 多线程处理
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {executor.submit(process_single_image, task): task for task in tasks}
        
        # 处理完成的任务
        for future in as_completed(future_to_task):
            filename, success, error_msg = future.result()
            if success:
                success_count += 1
            else:
                failed_count += 1
    
    print(f"\n📊 处理完成!")
    print(f"✅ 成功: {success_count} 个文件")
    print(f"❌ 失败: {failed_count} 个文件")
    print(f"📁 输出目录: {output_dir}")

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='图片水印添加工具')
    parser.add_argument('input', help='输入文件或目录路径')
    parser.add_argument('-o', '--output', help='输出文件或目录路径')
    parser.add_argument('-t', '--text', default='灵创新媒', help='水印文字 (默认: 灵创新媒)')
    parser.add_argument('-s', '--size', type=int, default=0, help='字体大小 (0表示自动计算, 默认: 0)')
    parser.add_argument('-a', '--alpha', type=int, default=128, help='透明度 0-255 (默认: 128)')
    parser.add_argument('-m', '--margin', type=int, default=20, help='边距 (默认: 20)')
    parser.add_argument('-w', '--workers', type=int, default=4, help='线程数 (默认: 4)')
    
    # 如果没有命令行参数，自动处理当前目录下所有文件夹
    if len(sys.argv) == 1:
        print("=" * 50)
        print("🎨 图片水印添加工具 - 自动模式")
        print("=" * 50)
        print("正在自动处理当前目录下除compressed外的所有文件夹...")
        print()
        
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "compressed")
        
        # 获取当前目录下的所有文件夹（排除compressed）
        folders_to_process = []
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)
            if os.path.isdir(item_path) and item.lower() != "compressed":
                folders_to_process.append(item_path)
        
        if not folders_to_process:
            print("❌ 当前目录下没有找到需要处理的文件夹")
            input("\n按回车键退出...")
            return
        
        print(f"📁 找到 {len(folders_to_process)} 个文件夹需要处理")
        
        # 处理每个文件夹
        total_success = 0
        total_failed = 0
        
        for folder_path in folders_to_process:
            folder_name = os.path.basename(folder_path)
            print(f"\n📂 正在处理文件夹: {folder_name}")
            
            # 获取该文件夹下的图片文件
            image_files = get_image_files(folder_path)
            
            if not image_files:
                print(f"   ⚠️ 文件夹 {folder_name} 中没有找到图片文件")
                continue
            
            print(f"   📸 找到 {len(image_files)} 个图片文件")
            
            # 处理该文件夹
            folder_output_dir = os.path.join(output_dir, folder_name)
            
            # 准备任务参数
            tasks = []
            for input_path in image_files:
                rel_path = os.path.relpath(input_path, folder_path)
                output_path = os.path.join(folder_output_dir, rel_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                tasks.append((input_path, output_path, "灵创新媒", 0, 128, 20))
            
            # 多线程处理
            success_count = 0
            failed_count = 0
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_task = {executor.submit(process_single_image, task): task for task in tasks}
                
                for future in as_completed(future_to_task):
                    filename, success, error_msg = future.result()
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
            
            print(f"   ✅ 成功: {success_count} 个文件")
            if failed_count > 0:
                print(f"   ❌ 失败: {failed_count} 个文件")
            
            total_success += success_count
            total_failed += failed_count
        
        print(f"\n📊 总体处理完成!")
        print(f"✅ 总成功: {total_success} 个文件")
        if total_failed > 0:
            print(f"❌ 总失败: {total_failed} 个文件")
        print(f"📁 输出目录: {output_dir}")
        
        input("\n按回车键退出...")
    
    else:
        # 命令行模式
        args = parser.parse_args()
        
        if not os.path.exists(args.input):
            print(f"❌ 输入路径不存在: {args.input}")
            return
        
        # 设置默认输出路径
        if not args.output:
            if os.path.isfile(args.input):
                args.output = os.path.splitext(args.input)[0] + "_watermarked" + os.path.splitext(args.input)[1]
            else:
                # 目录处理，默认输出到当前工作目录的compressed文件夹
                args.output = os.path.join(os.getcwd(), "compressed")
        
        # 处理图片
        if os.path.isfile(args.input):
            # 单文件处理
            success, error_msg = add_watermark(args.input, args.output, args.text, 
                                             args.size, args.alpha, args.margin)
            if success:
                print(f"✅ 处理完成: {args.output}")
            else:
                print(f"❌ 处理失败: {error_msg}")
        else:
            # 目录处理
            process_directory(args.input, args.output, args.text, 
                            args.size, args.alpha, args.margin, args.workers)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        input("按回车键退出...")