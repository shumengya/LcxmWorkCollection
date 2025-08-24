import os
import json
import uuid
from datetime import datetime
from pathlib import Path

def get_file_size(file_path):
    """获取文件大小并格式化"""
    try:
        size_bytes = os.path.getsize(file_path)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
    except:
        return "未知大小"

def scan_software_folder(downloads_path):
    """扫描downloads文件夹并生成软件配置"""
    software_list = []
    
    # 遍历downloads文件夹中的每个子文件夹
    for folder_name in os.listdir(downloads_path):
        folder_path = os.path.join(downloads_path, folder_name)
        
        # 跳过非文件夹
        if not os.path.isdir(folder_path):
            continue
            
        print(f"正在扫描软件: {folder_name}")
        
        # 创建软件配置模板
        software_config = {
            "id": str(uuid.uuid4()),
            "game_id": folder_name,
            "name": folder_name,
            "description": f"{folder_name}游戏描述",
            "version": "1.0.0",
            "developer": "开发者名称",
            "category": "游戏",
            "platforms": [],
            "tags": ["游戏"],
            "images": [],
            "download_links": {},
            "file_sizes": {},
            "system_requirements": "性能要好一点",
            "download_disabled": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "downloads": 0
        }
        
        # 扫描图片文件
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in image_extensions:
                    software_config["images"].append(f"downloads/{folder_name}/{file}")
        
        # 检查是否有视频文件
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv']
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in video_extensions:
                    software_config["video"] = f"downloads/{folder_name}/{file}"
                    break
        
        # 扫描平台文件夹
        platform_folders = ['Windows', 'macOS', 'Linux', 'Android', 'iOS']
        for platform in platform_folders:
            platform_path = os.path.join(folder_path, platform)
            if os.path.exists(platform_path) and os.path.isdir(platform_path):
                software_config["platforms"].append(platform)
                software_config["download_links"][platform] = {}
                
                # 查找平台下的安装包文件
                for file in os.listdir(platform_path):
                    file_path = os.path.join(platform_path, file)
                    if os.path.isfile(file_path):
                        software_config["download_links"][platform]["local"] = f"downloads/{folder_name}/{platform}/{file}"
                        software_config["file_sizes"][platform] = get_file_size(file_path)
                        break
                
                # 如果没有找到文件，设置为空
                if platform not in software_config["file_sizes"]:
                    software_config["file_sizes"][platform] = "无本地文件"
        
        # 如果没有找到任何平台，默认添加Windows
        if not software_config["platforms"]:
            software_config["platforms"] = ["Windows"]
            software_config["download_links"]["Windows"] = {}
            software_config["file_sizes"]["Windows"] = "无本地文件"
        
        software_list.append(software_config)
        print(f"完成扫描: {folder_name}")
    
    return software_list

def main():
    # 设置路径 - 自动检测当前工作目录
    base_path = os.getcwd()
    downloads_path = os.path.join(base_path, "downloads")
    output_file = os.path.join(base_path, "software_new.json")
    
    print(f"当前工作目录: {base_path}")
    print(f"downloads路径: {downloads_path}")
    
    # 检查downloads文件夹是否存在
    if not os.path.exists(downloads_path):
        print(f"错误: downloads文件夹不存在于 {downloads_path}")
        print("请确保在包含downloads文件夹的目录中运行此脚本")
        return
    
    print("开始扫描downloads文件夹...")
    
    # 扫描软件文件夹
    software_list = scan_software_folder(downloads_path)
    
    # 生成JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(software_list, f, ensure_ascii=False, indent=2)
    
    print(f"\n扫描完成！生成了 {len(software_list)} 个软件配置")
    print(f"新的配置文件已保存到: {output_file}")
    print("\n扫描到的软件:")
    for software in software_list:
        print(f"- {software['name']} (ID: {software['game_id']})")
        print(f"  平台: {', '.join(software['platforms'])}")
        print(f"  图片数量: {len(software['images'])}")
        if 'video' in software:
            print(f"  包含视频: {software['video']}")
        print()

if __name__ == "__main__":
    main()