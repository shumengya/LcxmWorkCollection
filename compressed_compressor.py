#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版图片批量压缩脚本
直接运行即可压缩当前目录下的所有图片
"""

import os
from PIL import Image, ImageFile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 允许处理截断的图片
ImageFile.LOAD_TRUNCATED_IMAGES = True

def compress_image(input_path, output_path, quality=85):
    """
    压缩单张图片
    """
    try:
        original_size = os.path.getsize(input_path)
        
        with Image.open(input_path) as img:
            # 处理透明背景
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存压缩图片
            img.save(output_path, 
                    format='JPEG',
                    quality=quality,
                    optimize=True,
                    progressive=True)
        
        compressed_size = os.path.getsize(output_path)
        return True, original_size, compressed_size
        
    except Exception as e:
        print(f"❌ 压缩失败 {os.path.basename(input_path)}: {str(e)}")
        return False, 0, 0

def format_size(size_bytes):
    """
    格式化文件大小
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def process_single_image_simple(args):
    """
    处理单张图片的包装函数，用于多线程
    """
    file_path, output_file, quality = args
    return compress_image(str(file_path), str(output_file), quality)

def main():
    """
    主函数 - 简化版批量压缩
    """
    print("🖼️  图片批量压缩工具 (多线程版)")
    print("=" * 40)
    
    # 当前目录
    current_dir = Path('.')
    output_dir = current_dir / "compressed"
    output_dir.mkdir(exist_ok=True)
    
    # 支持的图片格式
    supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    # 递归查找图片文件，忽略 compressed 文件夹
    image_files = []
    for file_path in current_dir.rglob('*'):
        # 检查文件路径是否在 compressed 文件夹内
        if 'compressed' in file_path.parts:
            continue
        if file_path.is_file() and file_path.suffix.lower() in supported_formats:
            image_files.append(file_path)
    
    if not image_files:
        print("❌ 当前目录及子文件夹下没有找到支持的图片文件")
        print(f"支持的格式: {', '.join(supported_formats)}")
        input("按回车键退出...")
        return
    
    # 设置线程数
    max_workers = min(32, (os.cpu_count() or 1) + 4)
    
    print(f"📁 找到 {len(image_files)} 个图片文件")
    print(f"📂 输出目录: {output_dir}")
    print(f"🎯 压缩质量: 85 (高质量)")
    print(f"🚀 线程数: {max_workers}")
    print("-" * 40)
    
    # 询问用户是否继续
    choice = input("是否开始压缩? (y/n): ").lower().strip()
    if choice not in ['y', 'yes', '是', '']:
        print("❌ 已取消压缩")
        return
    
    print("\n🚀 开始压缩...")
    
    # 统计信息
    success_count = 0
    total_original_size = 0
    total_compressed_size = 0
    completed_count = 0
    
    # 准备任务列表
    tasks = []
    for file_path in image_files:
        # 计算相对路径，保持文件夹结构
        relative_path = file_path.relative_to(current_dir)
        output_file = output_dir / relative_path.parent / f"{file_path.stem}.jpg"
        
        # 创建输出子目录
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        tasks.append((file_path, output_file, 85, relative_path))
    
    # 使用线程池并行处理
    print_lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {}
        for file_path, output_file, quality, relative_path in tasks:
            future = executor.submit(process_single_image_simple, (file_path, output_file, quality))
            future_to_task[future] = (file_path, output_file, relative_path)
        
        # 处理完成的任务
        for future in as_completed(future_to_task):
            file_path, output_file, relative_path = future_to_task[future]
            
            try:
                success, original_size, compressed_size = future.result()
                
                with print_lock:
                    completed_count += 1
                    
                    if success:
                        success_count += 1
                        total_original_size += original_size
                        total_compressed_size += compressed_size
                        
                        compression_ratio = (1 - compressed_size / original_size) * 100
                        print(f"[{completed_count}/{len(image_files)}] ✅ {relative_path}: {format_size(original_size)} → {format_size(compressed_size)} (压缩 {compression_ratio:.1f}%)")
                    else:
                        print(f"[{completed_count}/{len(image_files)}] ❌ {relative_path}: 处理失败")
                        
            except Exception as e:
                with print_lock:
                    completed_count += 1
                    print(f"[{completed_count}/{len(image_files)}] ❌ {relative_path}: 发生异常 - {str(e)}")
    
    # 显示结果
    print("\n" + "=" * 40)
    print("📊 压缩完成!")
    print(f"✅ 成功: {success_count}/{len(image_files)} 个文件")
    
    if total_original_size > 0:
        total_compression_ratio = (1 - total_compressed_size / total_original_size) * 100
        saved_space = total_original_size - total_compressed_size
        
        print(f"📏 原始大小: {format_size(total_original_size)}")
        print(f"📦 压缩大小: {format_size(total_compressed_size)}")
        print(f"📉 压缩率: {total_compression_ratio:.1f}%")
        print(f"💾 节省空间: {format_size(saved_space)}")
        
        if total_compression_ratio > 50:
            print("🎉 压缩效果很好!")
        elif total_compression_ratio > 30:
            print("👍 压缩效果不错!")
        else:
            print("ℹ️  压缩效果一般，可能图片已经过压缩")
    
    print(f"\n📂 压缩后的图片保存在: {output_dir}")
    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        input("按回车键退出...")