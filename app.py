from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, Response
from flask_cors import CORS
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid
import time
from collections import defaultdict
import threading
from PIL import Image, ImageDraw, ImageFont, ImageFile
import tempfile
import shutil

# 允许处理截断的图片
ImageFile.LOAD_TRUNCATED_IMAGES = True

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
CORS(app, origins=['*'], methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# 速率限制存储
rate_limit_storage = defaultdict(list)
rate_limit_lock = threading.Lock()

# 下载计数防刷存储 - 记录每个IP对每个软件的最后下载时间
download_count_storage = defaultdict(dict)  # {ip: {software_id: last_download_time}}
download_count_lock = threading.Lock()

# 配置文件上传
UPLOAD_FOLDER = 'static/uploads'
DOWNLOAD_FOLDER = 'static/downloads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}
ALLOWED_INSTALL_EXTENSIONS = {'exe', 'msi', 'dmg', 'pkg', 'deb', 'rpm', 'appimage', 'apk', 'ipa', 'zip', 'tar.gz', 'tar.bz2'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB 最大文件大小

# 数据文件路径
DATA_FILE = 'data/software.json'
SETTINGS_FILE = 'data/settings.json'

def init_data_files():
    """初始化数据文件和目录"""
    os.makedirs('data', exist_ok=True)
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('static/downloads', exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    

    
    if not os.path.exists(SETTINGS_FILE):
        # 默认网站设置
        default_settings = {
            "site_name": "灵创作品集",
            "brand_name": "灵创新媒",
            "site_logo": "uploads/lcxm.jpg",
            "visit_count": 0,
            "site_description": "欢迎加入灵创新媒！",
            "site_slogan": "灵感和创造，是实现梦想的翅膀",
            "icp_number": "蜀ICP备2025151694号",
            "gallery_title": "作品展示",
            "category_tags_title": "分类与标签",
            "featured_title": "精选作品",
            "updated_at": datetime.now().isoformat()
        }
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)

def load_software_data():
    """加载软件数据"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_software_data(data):
    """保存软件数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def load_settings():
    """加载网站设置"""
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # 确保visit_count字段存在
            if 'visit_count' not in settings:
                settings['visit_count'] = 0
            return settings
    except:
        return {
            "site_name": "灵创作品集",
            "brand_name": "灵创新媒",
            "site_logo": "uploads/lcxm.jpg",
            "site_description": "欢迎加入灵创新媒！",
            "site_slogan": "灵感和创造，是实现梦想的翅膀",
            "icp_number": "蜀ICP备2025151694号",
            "gallery_title": "作品展示",
            "category_tags_title": "分类与标签",
            "featured_title": "精选作品",
            "visit_count": 0
        }

def save_settings(settings):
    """保存网站设置"""
    settings['updated_at'] = datetime.now().isoformat()
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_install_file(filename):
    """检查安装文件扩展名是否允许"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    # 处理 .tar.gz 和 .tar.bz2 等复合扩展名
    if filename.lower().endswith(('.tar.gz', '.tar.bz2')):
        return True
    return ext in ALLOWED_INSTALL_EXTENSIONS

def allowed_video_file(filename):
    """检查是否为允许的视频文件类型"""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_VIDEO_EXTENSIONS

def get_background_brightness(img, margin=20):
    """获取图片右下角区域的平均亮度"""
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

def add_watermark_to_image(img, watermark_text="灵创新媒", font_size=0, margin=20):
    """为图片添加水印"""
    try:
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
        
        return watermarked_img
        
    except Exception as e:
        print(f"添加水印失败: {str(e)}")
        return img

def compress_and_watermark_image(input_path, output_path, quality=85, watermark_text="灵创新媒"):
    """压缩图片并添加水印"""
    try:
        with Image.open(input_path) as img:
            # 添加水印
            watermarked_img = add_watermark_to_image(img, watermark_text)
            
            # 处理透明背景
            if watermarked_img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', watermarked_img.size, (255, 255, 255))
                if watermarked_img.mode == 'P':
                    watermarked_img = watermarked_img.convert('RGBA')
                background.paste(watermarked_img, mask=watermarked_img.split()[-1] if watermarked_img.mode == 'RGBA' else None)
                watermarked_img = background
            elif watermarked_img.mode != 'RGB':
                watermarked_img = watermarked_img.convert('RGB')
            
            # 保存压缩图片
            watermarked_img.save(output_path, 
                               format='JPEG',
                               quality=quality,
                               optimize=True,
                               progressive=True)
        
        return True
        
    except Exception as e:
        print(f"压缩和水印处理失败: {str(e)}")
        return False

def save_software_video(file, software_name, software_id=None, game_id=None):
    """保存软件视频文件"""
    if not file or not allowed_video_file(file.filename):
        return None
    
    # 确定目录名
    if game_id:
        dir_name = game_id
    elif software_id:
        dir_name = software_id
    else:
        dir_name = secure_filename(software_name)
    
    # 创建目录
    video_dir = os.path.join('static', 'downloads', dir_name)
    os.makedirs(video_dir, exist_ok=True)
    
    # 保存为 video.mp4
    video_path = os.path.join(video_dir, 'video.mp4')
    file.save(video_path)
    
    # 返回相对路径
    return os.path.relpath(video_path, 'static').replace('\\', '/')

def delete_software_video(software_name, software_id=None, game_id=None):
    """删除软件视频文件"""
    # 确定目录名
    if game_id:
        dir_name = game_id
    elif software_id:
        dir_name = software_id
    else:
        dir_name = secure_filename(software_name)
    
    video_path = os.path.join('static', 'downloads', dir_name, 'video.mp4')
    if os.path.exists(video_path):
        os.remove(video_path)

def get_download_path(software_name, platform, software_id=None, game_id=None):
    """获取下载文件路径"""
    # 优先使用游戏ID，如果没有则使用软件名
    if game_id and game_id.strip():
        folder_name = game_id.strip()
    else:
        safe_name = secure_filename(software_name)
        # 如果有软件ID，使用ID确保唯一性
        if software_id:
            folder_name = f"{safe_name}_{software_id[:8]}"
        else:
            folder_name = safe_name
    
    download_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], folder_name, platform)
    os.makedirs(download_dir, exist_ok=True)
    return download_dir

def get_software_image_path(software_name, software_id=None, game_id=None):
    """获取软件图片存储路径"""
    # 优先使用游戏ID，如果没有则使用软件名
    if game_id and game_id.strip():
        folder_name = game_id.strip()
    else:
        safe_name = secure_filename(software_name)
        # 如果有软件ID，使用ID确保唯一性
        if software_id:
            folder_name = f"{safe_name}_{software_id[:8]}"
        else:
            folder_name = safe_name
    
    image_dir = os.path.join(app.config['DOWNLOAD_FOLDER'], folder_name)
    os.makedirs(image_dir, exist_ok=True)
    return image_dir

def save_software_images(files, software_name, software_id=None, game_id=None, add_watermark=True):
    """保存软件图片到专属文件夹，按image1.jpg格式命名（包含压缩和水印处理）"""
    image_paths = []
    image_dir = get_software_image_path(software_name, software_id, game_id)
    
    # 清理旧的图片文件
    for i in range(1, 21):  # 最多清理20张旧图片
        for ext in ['png', 'jpg', 'jpeg', 'gif']:
            old_file = os.path.join(image_dir, f'image{i}.{ext}')
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except:
                    pass
    
    # 保存新图片
    for i, file in enumerate(files, 1):
        if file and file.filename and allowed_file(file.filename):
            # 统一使用jpg格式（压缩后的格式）
            filename = f'image{i}.jpg'
            file_path = os.path.join(image_dir, filename)
            
            # 创建临时文件保存原始图片
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_path = temp_file.name
                file.save(temp_path)
            
            try:
                if add_watermark:
                    # 压缩并添加水印
                    if compress_and_watermark_image(temp_path, file_path, quality=85, watermark_text="灵创新媒"):
                        # 返回相对于static的路径
                        relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                        image_paths.append(relative_path)
                    else:
                        # 如果处理失败，直接保存原文件
                        shutil.copy2(temp_path, file_path)
                        relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                        image_paths.append(relative_path)
                else:
                    # 不添加水印，只压缩
                    try:
                        with Image.open(temp_path) as img:
                            # 转换为RGB模式（如果是RGBA或其他模式）
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = background
                            elif img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # 保存为JPG格式并压缩
                            img.save(file_path, 'JPEG', quality=85, optimize=True)
                            relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                            image_paths.append(relative_path)
                    except Exception:
                        # 如果处理失败，直接保存原文件
                        shutil.copy2(temp_path, file_path)
                        relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                        image_paths.append(relative_path)
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    
    return image_paths

def cleanup_old_files(download_dir):
    """清理旧的安装文件"""
    if os.path.exists(download_dir):
        for file in os.listdir(download_dir):
            file_path = os.path.join(download_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def can_increment_download_count(software_id, client_ip):
    """检查是否可以增加下载计数（防刷机制）"""
    current_time = time.time()
    
    with download_count_lock:
        # 获取该IP对该软件的最后下载时间
        last_download_time = download_count_storage[client_ip].get(software_id, 0)
        
        # 如果距离上次下载不足1分钟，则不允许增加计数
        if current_time - last_download_time < 60.0:
            return False
        
        # 更新最后下载时间
        download_count_storage[client_ip][software_id] = current_time
        
        # 清理过期记录（超过1小时的记录）
        expired_time = current_time - 3600
        for ip in list(download_count_storage.keys()):
            for sid in list(download_count_storage[ip].keys()):
                if download_count_storage[ip][sid] < expired_time:
                    del download_count_storage[ip][sid]
            if not download_count_storage[ip]:
                del download_count_storage[ip]
        
        return True

def rate_limit(max_requests=60, window=60):
    """速率限制装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            current_time = time.time()
            
            with rate_limit_lock:
                # 清理过期的请求记录
                rate_limit_storage[client_ip] = [
                    req_time for req_time in rate_limit_storage[client_ip]
                    if current_time - req_time < window
                ]
                
                # 检查是否超出速率限制
                if len(rate_limit_storage[client_ip]) >= max_requests:
                    return jsonify({
                        'success': False,
                        'error': '请求过于频繁，请稍后再试',
                        'code': 429
                    }), 429
                
                # 记录当前请求
                rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

def get_platform_file_sizes(software_data):
    """获取各平台文件大小"""
    file_sizes = {}
    for platform in software_data.get('platforms', []):
        download_links = software_data.get('download_links', {}).get(platform, {})
        local_file = download_links.get('local')
        
        if local_file:
            try:
                file_path = os.path.join('static', local_file)
                if os.path.exists(file_path):
                    size_bytes = os.path.getsize(file_path)
                    file_sizes[platform] = format_file_size(size_bytes)
                else:
                    file_sizes[platform] = "文件不存在"
            except:
                file_sizes[platform] = "未知"
        else:
            file_sizes[platform] = "无本地文件"
    
    return file_sizes

def get_base_url():
    """获取正确的基础URL，支持域名访问"""
    # 检查是否通过反向代理
    if request.headers.get('X-Forwarded-Host'):
        scheme = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('X-Forwarded-Host')
        return f"{scheme}://{host}"
    
    # 检查Host头
    if request.headers.get('Host') and not request.headers.get('Host').startswith('127.0.0.1') and not request.headers.get('Host').startswith('localhost'):
        scheme = 'https' if request.is_secure else 'http'
        return f"{scheme}://{request.headers.get('Host')}"
    
    # 默认返回request.url_root
    return request.url_root.rstrip('/')

@app.route('/')
def index():
    """首页 - 显示所有软件（带分页）"""
    # 增加访问人数统计
    settings = load_settings()
    visit_count = settings.get('visit_count', 0) + 1
    settings['visit_count'] = visit_count
    settings['updated_at'] = datetime.now().isoformat()
    save_settings(settings)
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    category = request.args.get('category', '', type=str)
    platform = request.args.get('platform', '', type=str)
    sort = request.args.get('sort', '', type=str)
    
    # 检测是否为移动设备
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad'])
    
    # 设置每页显示数量
    per_page = 3 if is_mobile else 6
    
    software_list = load_software_data()
    
    # 筛选数据
    filtered_list = software_list
    
    if search:
        search_lower = search.lower().strip()
        filtered_list = []
        
        for s in software_list:
            # 创建搜索目标文本
            search_targets = [
                s['name'].lower(),
                s['developer'].lower(), 
                s['description'].lower(),
                s.get('game_id', '').lower()
            ]
            
            # 添加标签搜索
            if s.get('tags'):
                search_targets.extend([tag.lower() for tag in s['tags']])
            
            # 多种搜索方式
            match_found = False
            
            # 1. 直接包含匹配
            for target in search_targets:
                if search_lower in target:
                    match_found = True
                    break
            
            # 2. 忽略空格和特殊字符的匹配
            if not match_found:
                clean_search = ''.join(c for c in search_lower if c.isalnum())
                for target in search_targets:
                    clean_target = ''.join(c for c in target if c.isalnum())
                    if clean_search in clean_target:
                        match_found = True
                        break
            
            # 3. 拆分词语匹配（支持多关键词）
            if not match_found:
                search_words = search_lower.split()
                if len(search_words) > 1:
                    for target in search_targets:
                        if all(word in target for word in search_words):
                            match_found = True
                            break
            
            if match_found:
                filtered_list.append(s)
    
    if category:
        filtered_list = [s for s in filtered_list if s['category'].lower() == category.lower()]
    
    if platform:
        filtered_list = [s for s in filtered_list if platform in s['platforms']]
    
    # 排序处理
    if sort == 'downloads':
        filtered_list.sort(key=lambda x: x.get('downloads', 0), reverse=True)
    elif sort == 'created_at':
        filtered_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort == 'updated_at':
        filtered_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    elif sort == 'platforms':
        filtered_list.sort(key=lambda x: len(x.get('platforms', [])), reverse=True)
    else:
        # 默认按更新时间排序
        filtered_list.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
    # 分页计算
    total = len(filtered_list)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    paginated_list = filtered_list[start:end]
    
    settings = load_settings()
    
    return render_template('index.html', 
                         software_list=paginated_list,
                         total_software_list=software_list,  # 完整的软件列表用于筛选选项
                         settings=settings,
                         current_page=page,
                         total_pages=total_pages,
                         has_prev=page > 1,
                         has_next=page < total_pages,
                         prev_page=page - 1 if page > 1 else None,
                         next_page=page + 1 if page < total_pages else None,
                         search=search,
                         category=category,
                         platform=platform,
                         sort=sort,
                         total_software=len(software_list),
                         filtered_total=total)

@app.route('/software/<software_id>')
def software_detail(software_id):
    """软件详情页面"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    if not software:
        flash('软件不存在', 'error')
        return redirect(url_for('index'))
    return render_template('software_detail.html', software=software, base_url=get_base_url())

@app.route('/admin')
def admin_dashboard():
    """管理员后台首页 - 需要安全验证"""
    # 检查URL中是否包含安全标识
    if request.args.get('token') != 'lcxm1314520':
        # 如果没有正确的token，返回404错误
        from flask import abort
        abort(404)
    
    software_list = load_software_data()
    return render_template('admin/dashboard.html', software_list=software_list)

def check_admin_access():
    """检查管理员访问权限"""
    if request.args.get('token') != 'lcxm1314520':
        from flask import abort
        abort(404)

@app.route('/admin/software/add', methods=['GET', 'POST'])
def admin_add_software():
    """添加软件 - 需要安全验证"""
    check_admin_access()
    if request.method == 'POST':
        try:
            # 获取表单数据
            software_data = {
                'id': str(uuid.uuid4()),
                'game_id': request.form.get('game_id', '').strip(),  # 新增游戏ID字段
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'version': request.form.get('version'),
                'developer': request.form.get('developer'),
                'category': request.form.get('category'),
                'platforms': request.form.getlist('platforms'),
                'tags': [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()],
                'images': [],
                'cover_image': '',  # 新增封面图片字段
                'video': None,
                'download_links': {},
                'file_sizes': {},
                'system_requirements': request.form.get('system_requirements', ''),
                'download_disabled': request.form.get('download_disabled') == 'on',  # 新增禁用下载字段
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'downloads': 0
            }
            
            # 处理上传的多张图片
            if 'images' in request.files:
                files = request.files.getlist('images')
                # 检查是否添加水印
                add_watermark = request.form.get('add_watermark') != 'off'
                image_paths = save_software_images(files, software_data['name'], software_data['id'], software_data.get('game_id'), add_watermark)
                software_data['images'] = image_paths
                
                # 设置封面图片
                cover_image_index = request.form.get('cover_image_index', '0')
                try:
                    cover_index = int(cover_image_index)
                    if 0 <= cover_index < len(image_paths):
                        software_data['cover_image'] = image_paths[cover_index]
                    elif image_paths:
                        software_data['cover_image'] = image_paths[0]  # 默认第一张
                except (ValueError, IndexError):
                    if image_paths:
                        software_data['cover_image'] = image_paths[0]  # 默认第一张
            
            # 处理视频上传
            if 'video' in request.files:
                video_file = request.files['video']
                if video_file and video_file.filename:
                    video_path = save_software_video(video_file, software_data['name'], software_data['id'], software_data.get('game_id'))
                    if video_path:
                        software_data['video'] = video_path
            
            # 处理安装文件上传和下载链接
            for platform in software_data['platforms']:
                software_data['download_links'][platform] = {}
                
                # 处理本地文件上传
                install_file_key = f'install_file_{platform}'
                if install_file_key in request.files:
                    file = request.files[install_file_key]
                    if file and file.filename and allowed_install_file(file.filename):
                        # 获取下载目录
                        download_dir = get_download_path(software_data['name'], platform, software_data['id'], software_data.get('game_id'))
                        # 清理旧文件
                        cleanup_old_files(download_dir)
                        # 生成新文件名：game_id + 平台 + 扩展名
                        original_ext = os.path.splitext(file.filename)[1]  # 获取原始扩展名
                        game_id = software_data.get('game_id', '').strip()
                        if game_id:
                            filename = f"{game_id}_{platform.lower()}{original_ext}"
                        else:
                            # 如果没有game_id，使用软件名作为备选
                            safe_name = secure_filename(software_data['name'])
                            filename = f"{safe_name}_{platform.lower()}{original_ext}"
                        file_path = os.path.join(download_dir, filename)
                        file.save(file_path)
                        # 设置本地下载链接
                        relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                        software_data['download_links'][platform]['local'] = relative_path
                
                # 处理自定义网盘链接
                custom_names = request.form.getlist(f'custom_name_{platform}')
                custom_urls = request.form.getlist(f'custom_url_{platform}')
                
                for name, url in zip(custom_names, custom_urls):
                    if name.strip() and url.strip():
                        software_data['download_links'][platform][name.strip()] = url.strip()
            
            # 计算各平台文件大小
            software_data['file_sizes'] = get_platform_file_sizes(software_data)
            
            # 保存数据
            software_list = load_software_data()
            software_list.append(software_data)
            save_software_data(software_list)
            
            flash('软件添加成功！', 'success')
            return redirect(url_for('admin_dashboard', token='lcxm1314520'))
            
        except Exception as e:
            flash(f'添加软件失败: {str(e)}', 'error')
    
    return render_template('admin/add_software.html')

@app.route('/admin/software/edit/<software_id>', methods=['GET', 'POST'])
def admin_edit_software(software_id):
    """编辑软件 - 需要安全验证"""
    check_admin_access()
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software:
        flash('软件不存在', 'error')
        return redirect(url_for('admin_dashboard', token='lcxm1314520'))
    
    if request.method == 'POST':
        try:
            # 更新基本信息
            software['game_id'] = request.form.get('game_id', '').strip()  # 更新游戏ID
            software['name'] = request.form.get('name')
            software['description'] = request.form.get('description')
            software['version'] = request.form.get('version')
            software['developer'] = request.form.get('developer')
            software['category'] = request.form.get('category')
            software['platforms'] = request.form.getlist('platforms')
            software['tags'] = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
            software['system_requirements'] = request.form.get('system_requirements', '')
            software['download_disabled'] = request.form.get('download_disabled') == 'on'  # 更新禁用下载字段
            software['updated_at'] = datetime.now().isoformat()
            
            # 确保封面字段存在
            if 'cover_image' not in software:
                software['cover_image'] = ''
            
            # 处理一键删除所有图片
            if request.form.get('delete_all_images') == '1':
                # 删除所有图片文件
                for img_path in software['images']:
                    try:
                        os.remove(os.path.join('static', img_path))
                    except:
                        pass
                software['images'] = []
                software['cover_image'] = ''
            else:
                # 处理要删除的图片
                images_to_delete = request.form.get('images_to_delete', '').split(',')
                for img_path in images_to_delete:
                    if img_path.strip() and img_path.strip() in software['images']:
                        software['images'].remove(img_path.strip())
                        # 删除物理文件
                        try:
                            os.remove(os.path.join('static', img_path.strip()))
                        except:
                            pass
                        # 如果删除的是封面图片，清空封面
                        if software.get('cover_image') == img_path.strip():
                            software['cover_image'] = ''
            
            # 处理新上传的图片
            if 'images' in request.files:
                files = request.files.getlist('images')
                if any(file and file.filename for file in files):
                    # 检查是否添加水印
                    add_watermark = request.form.get('add_watermark') != 'off'
                    # 如果有新图片上传，重新保存所有图片
                    new_image_paths = save_software_images(files, software['name'], software['id'], software.get('game_id'), add_watermark)
                    software['images'] = new_image_paths
                    
                    # 设置封面图片
                    cover_image_index = request.form.get('cover_image_index', '0')
                    try:
                        cover_index = int(cover_image_index)
                        if 0 <= cover_index < len(new_image_paths):
                            software['cover_image'] = new_image_paths[cover_index]
                        elif new_image_paths:
                            software['cover_image'] = new_image_paths[0]  # 默认第一张
                    except (ValueError, IndexError):
                        if new_image_paths:
                            software['cover_image'] = new_image_paths[0]  # 默认第一张
            
            # 处理封面图片选择（不上传新图片时）
            if not any(file and file.filename for file in request.files.getlist('images')):
                cover_image_path = request.form.get('cover_image_select', '')
                if cover_image_path and cover_image_path in software['images']:
                    software['cover_image'] = cover_image_path
                elif not software.get('cover_image') and software['images']:
                    software['cover_image'] = software['images'][0]  # 默认第一张
            
            # 处理视频上传
            if 'video' in request.files:
                video_file = request.files['video']
                if video_file and video_file.filename:
                    # 删除旧视频
                    delete_software_video(software['name'], software['id'], software.get('game_id'))
                    # 保存新视频
                    video_path = save_software_video(video_file, software['name'], software['id'], software.get('game_id'))
                    if video_path:
                        software['video'] = video_path
            
            # 处理删除视频
            if request.form.get('delete_video') == '1':
                delete_software_video(software['name'], software['id'], software.get('game_id'))
                software['video'] = None
            
            # 更新安装文件和下载链接
            for platform in software['platforms']:
                if platform not in software['download_links']:
                    software['download_links'][platform] = {}
                
                # 处理本地文件上传
                install_file_key = f'install_file_{platform}'
                if install_file_key in request.files:
                    file = request.files[install_file_key]
                    if file and file.filename and allowed_install_file(file.filename):
                        # 获取下载目录
                        download_dir = get_download_path(software['name'], platform, software['id'], software.get('game_id'))
                        # 清理旧文件
                        cleanup_old_files(download_dir)
                        # 生成新文件名：game_id + 平台 + 扩展名
                        original_ext = os.path.splitext(file.filename)[1]  # 获取原始扩展名
                        game_id = software.get('game_id', '').strip()
                        if game_id:
                            filename = f"{game_id}_{platform.lower()}{original_ext}"
                        else:
                            # 如果没有game_id，使用软件名作为备选
                            safe_name = secure_filename(software['name'])
                            filename = f"{safe_name}_{platform.lower()}{original_ext}"
                        file_path = os.path.join(download_dir, filename)
                        file.save(file_path)
                        # 设置本地下载链接
                        relative_path = os.path.relpath(file_path, 'static').replace('\\', '/')
                        software['download_links'][platform]['local'] = relative_path
                
                # 清理旧的自定义下载链接（除了local）
                old_links = dict(software['download_links'][platform])
                software['download_links'][platform] = {}
                if 'local' in old_links:
                    software['download_links'][platform]['local'] = old_links['local']
                
                # 处理自定义网盘链接
                custom_names = request.form.getlist(f'custom_name_{platform}')
                custom_urls = request.form.getlist(f'custom_url_{platform}')
                
                for name, url in zip(custom_names, custom_urls):
                    if name.strip() and url.strip():
                        software['download_links'][platform][name.strip()] = url.strip()
            
            # 重新计算各平台文件大小
            software['file_sizes'] = get_platform_file_sizes(software)
            
            # 保存数据
            save_software_data(software_list)
            flash('软件更新成功！', 'success')
            return redirect(url_for('admin_dashboard', token='lcxm1314520'))
            
        except Exception as e:
            flash(f'更新软件失败: {str(e)}', 'error')
    
    return render_template('admin/edit_software.html', software=software)

@app.route('/admin/software/delete/<software_id>', methods=['POST'])
def admin_delete_software(software_id):
    """删除软件及其所有相关文件 - 需要安全验证"""
    # 对于POST请求，检查referer是否来自管理页面
    referer = request.headers.get('Referer', '')
    if 'token=lcxm1314520' not in referer:
        from flask import abort
        abort(404)
    try:
        software_list = load_software_data()
        software = next((s for s in software_list if s['id'] == software_id), None)
        
        if not software:
            flash('软件不存在！', 'error')
            return redirect(url_for('admin_dashboard', token='lcxm1314520'))
        
        # 删除相关文件
        delete_software_files(software)
        
        # 从数据中删除
        software_list = [s for s in software_list if s['id'] != software_id]
        save_software_data(software_list)
        
        flash(f'软件 "{software["name"]}" 及其所有文件删除成功！', 'success')
    except Exception as e:
        flash(f'删除软件失败: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard', token='lcxm1314520'))

def delete_software_files(software):
    """删除软件的所有相关文件"""
    import shutil
    
    # 确定文件夹名称
    game_id = software.get('game_id', '').strip()
    if game_id:
        folder_name = game_id
    else:
        safe_name = secure_filename(software['name'])
        folder_name = f"{safe_name}_{software['id'][:8]}"
    
    # 删除整个软件文件夹
    software_dir = os.path.join('static', 'downloads', folder_name)
    if os.path.exists(software_dir):
        try:
            shutil.rmtree(software_dir)
            print(f"已删除文件夹: {software_dir}")
        except Exception as e:
            print(f"删除文件夹失败 {software_dir}: {str(e)}")
    
    # 删除可能存在的上传文件夹中的图片
    upload_dir = os.path.join('static', 'uploads')
    if os.path.exists(upload_dir):
        for file in os.listdir(upload_dir):
            if file.startswith(folder_name) or file.startswith(software['name']):
                file_path = os.path.join(upload_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"已删除上传文件: {file_path}")
                except Exception as e:
                    print(f"删除上传文件失败 {file_path}: {str(e)}")

@app.route('/api/software')
def api_software_list_old():
    """API: 获取软件列表（旧版本，保持兼容性）"""
    software_list = load_software_data()
    return jsonify(software_list)

@app.route('/api/software/<software_id>')
def api_software_detail(software_id):
    """API: 获取软件详情"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    if software:
        return jsonify(software)
    return jsonify({'error': '软件不存在'}), 404

@app.route('/thanks/<software_id>/<platform>')
def download_thanks(software_id, platform):
    """下载感谢页面"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software:
        flash('软件不存在', 'error')
        return redirect(url_for('index'))
    
    if platform not in software['platforms']:
        flash('不支持该平台', 'error')
        return redirect(url_for('software_detail', software_id=software_id))
    
    # 获取本地下载链接
    download_links = software['download_links'].get(platform, {})
    local_file = download_links.get('local')
    
    if not local_file:
        flash('暂无本地下载文件', 'error')
        return redirect(url_for('software_detail', software_id=software_id))
    
    return render_template('download_thanks.html', 
                         software=software, 
                         platform=platform,
                         download_url=url_for('download_software', 
                                            software_id=software_id, 
                                            platform=platform, 
                                            download_type='local'),
                         base_url=get_base_url())

@app.route('/download/<game_id>/<platform>')
def download_by_game_id(game_id, platform):
    """基于游戏ID的简单下载链接"""
    software_list = load_software_data()
    
    # 查找软件（按游戏ID）
    software = None
    for s in software_list:
        if s.get('game_id', '').lower() == game_id.lower():
            software = s
            break
    
    if not software:
        flash('未找到软件', 'error')
        return redirect(url_for('index'))
    
    if platform.lower() not in [p.lower() for p in software['platforms']]:
        flash('暂无该平台版本', 'error')
        return redirect(url_for('software_detail', software_id=software['id']))
    
    # 找到正确的平台名称（保持大小写）
    actual_platform = None
    for p in software['platforms']:
        if p.lower() == platform.lower():
            actual_platform = p
            break
    
    # 检查是否有本地文件
    download_links = software['download_links'].get(actual_platform, {})
    if not download_links.get('local'):
        flash(f'暂无{actual_platform}平台的本地下载文件', 'error')
        return redirect(url_for('software_detail', software_id=software['id']))
    
    # 跳转到感谢页面
    return redirect(url_for('download_thanks', software_id=software['id'], platform=actual_platform))

@app.route('/get/<software_name>')
@app.route('/get/<software_name>/<platform>')
def simple_download(software_name, platform=None):
    """简单下载链接 - 根据软件名称直接下载"""
    software_list = load_software_data()
    
    # 查找软件（不区分大小写，支持模糊匹配）
    software = None
    software_name_lower = software_name.lower().replace('-', ' ').replace('_', ' ')
    
    for s in software_list:
        if (s['name'].lower() == software_name_lower or 
            s['name'].lower().replace(' ', '') == software_name.lower().replace('-', '').replace('_', '') or
            software_name_lower in s['name'].lower()):
            software = s
            break
    
    if not software:
        flash('未找到软件', 'error')
        return redirect(url_for('index'))
    
    # 如果没有指定平台，选择第一个有本地文件的平台
    if not platform:
        for p in software['platforms']:
            download_links = software['download_links'].get(p, {})
            if download_links.get('local'):
                platform = p
                break
    
    # 平台名称不区分大小写匹配
    actual_platform = None
    if platform:
        for p in software['platforms']:
            if p.lower() == platform.lower():
                actual_platform = p
                break
    
    if not actual_platform:
        flash('暂无可下载的平台版本', 'error')
        return redirect(url_for('software_detail', software_id=software['id']))
    
    # 检查是否有本地文件
    download_links = software['download_links'].get(actual_platform, {})
    if not download_links.get('local'):
        flash(f'暂无{actual_platform}平台的本地下载文件', 'error')
        return redirect(url_for('software_detail', software_id=software['id']))
    
    # 跳转到感谢页面
    return redirect(url_for('download_thanks', software_id=software['id'], platform=actual_platform))

@app.route('/video/<software_id>')
def stream_video(software_id):
    """视频流式传输路由 - 支持HTTP Range请求和自适应码率"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software or not software.get('video'):
        return jsonify({'error': '视频不存在'}), 404
    
    # 获取视频文件路径
    video_path = os.path.join('static', software['video'])
    if not os.path.exists(video_path):
        return jsonify({'error': '视频文件不存在'}), 404
    
    # 获取文件信息
    file_size = os.path.getsize(video_path)
    
    # 处理Range请求（支持视频拖拽和断点续播）
    range_header = request.headers.get('Range')
    if range_header:
        # 解析Range头
        byte_start = 0
        byte_end = file_size - 1
        
        range_match = range_header.replace('bytes=', '').split('-')
        if range_match[0]:
            byte_start = int(range_match[0])
        if range_match[1]:
            byte_end = int(range_match[1])
        
        # 确保范围有效
        byte_start = max(0, byte_start)
        byte_end = min(file_size - 1, byte_end)
        
        def generate_video_stream():
            """生成视频流数据"""
            with open(video_path, 'rb') as f:
                f.seek(byte_start)
                remaining = byte_end - byte_start + 1
                
                while remaining:
                    # 使用较小的chunk size改善流式传播效果
                    chunk_size = min(8192, remaining)  # 8KB chunks for better streaming
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        # 返回部分内容响应
        response = Response(
            generate_video_stream(),
            206,  # Partial Content
            headers={
                'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(byte_end - byte_start + 1),
                'Content-Type': 'video/mp4',
                'Cache-Control': 'public, max-age=3600',  # 缓存1小时
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Range'
            }
        )
        return response
    else:
        # 完整视频流传输
        def generate_full_video_stream():
            """生成完整视频流"""
            with open(video_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks for better streaming
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(
            generate_full_video_stream(),
            headers={
                'Content-Type': 'video/mp4',
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=3600',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Range'
            }
        )
        return response

@app.route('/video/<software_id>/<quality>')
def stream_video_quality(software_id, quality='auto'):
    """支持不同质量的视频流式传输"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software or not software.get('video'):
        return jsonify({'error': '视频不存在'}), 404
    
    # 获取视频文件路径
    video_path = os.path.join('static', software['video'])
    if not os.path.exists(video_path):
        return jsonify({'error': '视频文件不存在'}), 404
    
    # 根据质量参数调整传输策略 - 使用更小的chunk改善流式传播
    chunk_size = 8192  # 默认8KB for better streaming
    if quality == '480p':
        chunk_size = 4096  # 4KB - 更小chunk适合低质量快速启动
    elif quality == '720p':
        chunk_size = 16384  # 16KB - 适中chunk适合高质量
    elif quality == 'auto':
        # 自适应：根据用户代理判断设备类型
        user_agent = request.headers.get('User-Agent', '').lower()
        if any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone']):
            chunk_size = 4096  # 移动设备使用更小chunk快速启动
        else:
            chunk_size = 8192  # 桌面设备使用标准chunk
    
    # 获取文件信息
    file_size = os.path.getsize(video_path)
    
    # 处理Range请求
    range_header = request.headers.get('Range')
    if range_header:
        byte_start = 0
        byte_end = file_size - 1
        
        range_match = range_header.replace('bytes=', '').split('-')
        if range_match[0]:
            byte_start = int(range_match[0])
        if range_match[1]:
            byte_end = int(range_match[1])
        
        byte_start = max(0, byte_start)
        byte_end = min(file_size - 1, byte_end)
        
        def generate_adaptive_stream():
            """生成自适应视频流"""
            with open(video_path, 'rb') as f:
                f.seek(byte_start)
                remaining = byte_end - byte_start + 1
                
                while remaining:
                    current_chunk_size = min(chunk_size, remaining)
                    chunk = f.read(current_chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        response = Response(
            generate_adaptive_stream(),
            206,
            headers={
                'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(byte_end - byte_start + 1),
                'Content-Type': 'video/mp4',
                'Cache-Control': f'public, max-age={3600 if quality != "auto" else 1800}',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Range',
                'X-Video-Quality': quality
            }
        )
        return response
    else:
        def generate_full_adaptive_stream():
            """生成完整自适应视频流"""
            with open(video_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        response = Response(
            generate_full_adaptive_stream(),
            headers={
                'Content-Type': 'video/mp4',
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes',
                'Cache-Control': f'public, max-age={3600 if quality != "auto" else 1800}',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Range',
                'X-Video-Quality': quality
            }
        )
        return response

@app.route('/api/video/<software_id>/info')
def get_video_info(software_id):
    """获取视频信息API"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software or not software.get('video'):
        return jsonify({'error': '视频不存在'}), 404
    
    video_path = os.path.join('static', software['video'])
    if not os.path.exists(video_path):
        return jsonify({'error': '视频文件不存在'}), 404
    
    try:
        file_size = os.path.getsize(video_path)
        
        return jsonify({
            'success': True,
            'video_info': {
                'file_size': file_size,
                'file_size_formatted': format_file_size(file_size),
                'stream_url': url_for('stream_video', software_id=software_id),
                'quality_urls': {
                    'auto': url_for('stream_video_quality', software_id=software_id, quality='auto'),
                    '720p': url_for('stream_video_quality', software_id=software_id, quality='720p'),
                    '480p': url_for('stream_video_quality', software_id=software_id, quality='480p')
                },
                'supports_range': True,
                'mime_type': 'video/mp4'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取视频信息失败: {str(e)}'
        }), 500

@app.route('/download/<software_id>/<platform>/<download_type>')
def download_software(software_id, platform, download_type):
    """优化的下载功能（支持断点续传、记录下载次数）"""
    software_list = load_software_data()
    software = next((s for s in software_list if s['id'] == software_id), None)
    
    if not software:
        return jsonify({'error': '软件不存在'}), 404
    
    # 获取下载链接
    download_link = software['download_links'].get(platform, {}).get(download_type)
    if not download_link:
        return jsonify({'error': '下载链接不存在'}), 404
    
    # 如果是本地文件，提供优化下载
    if download_type == 'local':
        try:
            # 支持 uploads/ 和 downloads/ 路径
            if download_link.startswith(('uploads/', 'downloads/')):
                file_path = os.path.join('static', download_link)
            else:
                file_path = download_link
            
            if not os.path.exists(file_path):
                return jsonify({'error': '文件不存在'}), 404
            
            # 增加下载次数（防刷机制：1分钟内同一IP最多增加1次）
            try:
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
                if client_ip and can_increment_download_count(software_id, client_ip):
                    software['downloads'] = software.get('downloads', 0) + 1
                    save_software_data(software_list)
            except:
                pass  # 下载次数更新失败不影响文件下载
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # 支持断点续传
            range_header = request.headers.get('Range')
            if range_header:
                # 解析Range头
                byte_start = 0
                byte_end = file_size - 1
                
                range_match = range_header.replace('bytes=', '').split('-')
                if range_match[0]:
                    byte_start = int(range_match[0])
                if range_match[1]:
                    byte_end = int(range_match[1])
                
                # 创建部分内容响应
                from flask import Response
                def generate():
                    with open(file_path, 'rb') as f:
                        f.seek(byte_start)
                        remaining = byte_end - byte_start + 1
                        last_time = time.time()
                        bytes_sent = 0
                        max_speed = 10 * 1024 * 1024  # 10MB/s 速度限制
                        
                        while remaining:
                            chunk_size = min(8192, remaining)  # 8KB chunks
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            bytes_sent += len(chunk)
                            
                            # 速度控制
                            current_time = time.time()
                            elapsed = current_time - last_time
                            if elapsed > 0:
                                current_speed = bytes_sent / elapsed
                                if current_speed > max_speed:
                                    # 计算需要等待的时间
                                    sleep_time = (bytes_sent / max_speed) - elapsed
                                    if sleep_time > 0:
                                        time.sleep(sleep_time)
                            
                            yield chunk
                
                # 处理中文文件名编码
                from urllib.parse import quote
                encoded_filename = quote(file_name.encode('utf-8'))
                response = Response(
                    generate(),
                    206,  # Partial Content
                    headers={
                        'Content-Range': f'bytes {byte_start}-{byte_end}/{file_size}',
                        'Accept-Ranges': 'bytes',
                        'Content-Length': str(byte_end - byte_start + 1),
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}'
                    }
                )
                return response
            else:
                # 普通下载，支持大文件流式传输
                def generate():
                    with open(file_path, 'rb') as f:
                        last_time = time.time()
                        bytes_sent = 0
                        max_speed = 10 * 1024 * 1024  # 10MB/s 速度限制
                        
                        while True:
                            chunk = f.read(8192)  # 8KB chunks
                            if not chunk:
                                break
                            bytes_sent += len(chunk)
                            
                            # 速度控制
                            current_time = time.time()
                            elapsed = current_time - last_time
                            if elapsed > 0:
                                current_speed = bytes_sent / elapsed
                                if current_speed > max_speed:
                                    # 计算需要等待的时间
                                    sleep_time = (bytes_sent / max_speed) - elapsed
                                    if sleep_time > 0:
                                        time.sleep(sleep_time)
                            
                            yield chunk
                
                from flask import Response
                from urllib.parse import quote
                # 处理中文文件名编码
                encoded_filename = quote(file_name.encode('utf-8'))
                response = Response(
                    generate(),
                    headers={
                        'Content-Type': 'application/octet-stream',
                        'Content-Disposition': f'attachment; filename*=UTF-8\'\'{encoded_filename}',
                        'Content-Length': str(file_size),
                        'Accept-Ranges': 'bytes'
                    }
                )
                return response
                
        except Exception as e:
            return jsonify({'error': f'下载失败: {str(e)}'}), 500
    
    # 其他情况记录下载次数后重定向（防刷机制：1分钟内同一IP最多增加1次）
    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        if client_ip and can_increment_download_count(software_id, client_ip):
            software['downloads'] = software.get('downloads', 0) + 1
            save_software_data(software_list)
    except:
        pass
    
    return redirect(download_link)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """网站设置管理 - 需要安全验证"""
    check_admin_access()
    if request.method == 'POST':
        try:
            settings = load_settings()
            settings['site_name'] = request.form.get('site_name', '萌芽软件发布网')
            settings['site_description'] = request.form.get('site_description', '')
            
            # 处理logo上传
            if 'site_logo' in request.files:
                file = request.files['site_logo']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"logo_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    settings['site_logo'] = f'uploads/{filename}'
            
            save_settings(settings)
            flash('网站设置保存成功！', 'success')
            return redirect(url_for('admin_settings', token='lcxm1314520'))
            
        except Exception as e:
            flash(f'保存设置失败: {str(e)}', 'error')
    
    settings = load_settings()
    return render_template('admin/settings.html', settings=settings)

# API文档页面已删除

# ================== 简化的API接口（专为Godot客户端设计） ==================

@app.route('/api/simple/check-version/<software_name>')
def simple_check_version(software_name):
    """
    超简单的版本检查API - 专为Godot客户端设计
    
    参数:
        software_name: 软件名称
        current_version: 当前版本号（URL参数）
    
    返回:
        - 如果有更新: {"has_update": true, "latest_version": "1.0.5", "download_url": "..."}
        - 如果无更新: {"has_update": false, "current_version": "1.0.5"}
        - 如果出错: {"error": "错误信息"}
    """
    try:
        # 获取当前版本号参数
        current_version = request.args.get('current_version')
        if not current_version:
            return jsonify({"error": "缺少current_version参数"})
        
        # 查找软件（支持按名称或game_id查找）
        software_list = load_software_data()
        software = None
        for s in software_list:
            if (s['name'].lower() == software_name.lower() or 
                s.get('game_id', '').lower() == software_name.lower()):
                software = s
                break
        
        if not software:
            return jsonify({"error": f"未找到软件: {software_name}"})
        
        latest_version = software['version']
        
        # 简单的版本号比较
        if current_version != latest_version:
            # 有更新
            # 获取下载链接（优先本地文件）
            download_url = ""
            if software.get('download_links'):
                for platform in ['Windows', 'Android', 'Linux', 'macOS']:
                    if platform in software['download_links']:
                        links = software['download_links'][platform]
                        if 'local' in links:
                            base_url = get_base_url()
                            download_url = f"{base_url}/download/{software['id']}/{platform}/local"
                            break
                        elif links:
                            # 使用第一个可用的外部链接
                            download_url = next(iter(links.values()))
                            break
            
            return jsonify({
                "has_update": True,
                "latest_version": latest_version,
                "current_version": current_version,
                "software_name": software['name'],
                "download_url": download_url,
                "file_size": software.get('file_sizes', {})
            })
        else:
            # 无更新
            return jsonify({
                "has_update": False,
                "current_version": current_version,
                "latest_version": latest_version,
                "software_name": software['name']
            })
            
    except Exception as e:
        return jsonify({"error": f"服务器错误: {str(e)}"})

@app.route('/api/simple/get-latest/<software_name>')
def simple_get_latest(software_name):
    """
    获取软件最新版本信息 - 不需要当前版本参数
    
    返回:
        {"version": "1.0.5", "download_url": "...", "software_name": "软件名"}
    """
    try:
        # 查找软件（支持按名称或game_id查找）
        software_list = load_software_data()
        software = None
        for s in software_list:
            if (s['name'].lower() == software_name.lower() or 
                s.get('game_id', '').lower() == software_name.lower()):
                software = s
                break
        
        if not software:
            return jsonify({"error": f"未找到软件: {software_name}"})
        
        # 获取下载链接
        download_url = ""
        if software.get('download_links'):
            for platform in ['Windows', 'Android', 'Linux', 'macOS']:
                if platform in software['download_links']:
                    links = software['download_links'][platform]
                    if 'local' in links:
                        base_url = get_base_url()
                        download_url = f"{base_url}/download/{software['id']}/{platform}/local"
                        break
                    elif links:
                        download_url = next(iter(links.values()))
                        break
        
        return jsonify({
            "version": software['version'],
            "software_name": software['name'],
            "download_url": download_url,
            "description": software.get('description', ''),
            "file_size": software.get('file_sizes', {}),
            "platforms": software.get('platforms', [])
        })
        
    except Exception as e:
        return jsonify({"error": f"服务器错误: {str(e)}"})

# ================== 原有API 接口 ==================

@app.route('/api/v1/software/<software_name>/version')
@rate_limit(max_requests=30, window=60)  # 每分钟最多30次请求
def api_get_latest_version(software_name):
    """获取软件最新版本信息"""
    try:
        software_list = load_software_data()
        # 支持按名称或ID查找
        software = None
        for s in software_list:
            if s['name'].lower() == software_name.lower() or s['id'] == software_name:
                software = s
                break
        
        if not software:
            return jsonify({
                'success': False,
                'error': '软件不存在',
                'code': 404
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'id': software['id'],
                'name': software['name'],
                'version': software['version'],
                'developer': software['developer'],
                'description': software['description'],
                'platforms': software['platforms'],
                'file_sizes': software.get('file_sizes', {}),
                'updated_at': software['updated_at'],
                'download_count': software.get('downloads', 0)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/v1/software/<software_id>/download/<platform>')
@rate_limit(max_requests=30, window=60)  # 每分钟最多30次请求
def api_get_download_links(software_id, platform):
    """获取指定平台的下载链接"""
    try:
        software_list = load_software_data()
        software = next((s for s in software_list if s['id'] == software_id), None)
        
        if not software:
            return jsonify({
                'success': False,
                'error': '软件不存在',
                'code': 404
            }), 404
        
        if platform not in software['platforms']:
            return jsonify({
                'success': False,
                'error': f'不支持 {platform} 平台',
                'code': 400
            }), 400
        
        download_links = software['download_links'].get(platform, {})
        if not download_links:
            return jsonify({
                'success': False,
                'error': f'{platform} 平台暂无下载链接',
                'code': 404
            }), 404
        
        # 构建完整的下载URL
        base_url = get_base_url()
        download_urls = {}
        
        for link_type, link_url in download_links.items():
            if link_type == 'local':
                # 本地文件提供API下载链接
                download_urls[link_type] = {
                    'url': f"{base_url}/download/{software_id}/{platform}/{link_type}",
                    'type': 'direct',
                    'supports_resume': True,
                    'file_size': software.get('file_sizes', {}).get(platform, '未知')
                }
            else:
                # 外部链接
                download_urls[link_type] = {
                    'url': link_url,
                    'type': 'redirect',
                    'supports_resume': False,
                    'file_size': '未知'
                }
        
        return jsonify({
            'success': True,
            'data': {
                'software_id': software_id,
                'software_name': software['name'],
                'version': software['version'],
                'platform': platform,
                'download_links': download_urls,
                'file_size': software.get('file_sizes', {}).get(platform, '未知')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/v1/software/<software_id>/download/<platform>/<download_type>')
def api_download_software(software_id, platform, download_type):
    """API下载接口（支持断点续传）"""
    return download_software(software_id, platform, download_type)

@app.route('/api/v1/software/list')
@rate_limit(max_requests=20, window=60)  # 每分钟最多20次请求
def api_software_list():
    """获取软件列表"""
    try:
        software_list = load_software_data()
        
        # 支持分页
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        per_page = min(per_page, 100)  # 限制最大每页数量
        
        # 支持筛选
        category = request.args.get('category')
        platform = request.args.get('platform')
        search = request.args.get('search')
        
        # 筛选软件
        filtered_list = software_list
        
        if category:
            filtered_list = [s for s in filtered_list if s['category'].lower() == category.lower()]
        
        if platform:
            filtered_list = [s for s in filtered_list if platform in s['platforms']]
        
        if search:
            search_lower = search.lower()
            filtered_list = [s for s in filtered_list if 
                           search_lower in s['name'].lower() or 
                           search_lower in s['developer'].lower() or 
                           search_lower in s['description'].lower()]
        
        # 分页
        total = len(filtered_list)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_list = filtered_list[start:end]
        
        # 简化数据
        simplified_list = []
        for software in paginated_list:
            simplified_list.append({
                'id': software['id'],
                'name': software['name'],
                'version': software['version'],
                'developer': software['developer'],
                'category': software['category'],
                'platforms': software['platforms'],
                'description': software['description'][:200] + ('...' if len(software['description']) > 200 else ''),
                'downloads': software.get('downloads', 0),
                'updated_at': software['updated_at']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'software_list': simplified_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 500
        }), 500

@app.route('/api/v1/software/<software_id>/check-update')
@rate_limit(max_requests=30, window=60)  # 每分钟最多30次请求
def api_check_update(software_id):
    """检查软件更新（比较版本号）"""
    try:
        current_version = request.args.get('current_version')
        if not current_version:
            return jsonify({
                'success': False,
                'error': '缺少当前版本号参数',
                'code': 400
            }), 400
        
        software_list = load_software_data()
        software = next((s for s in software_list if s['id'] == software_id), None)
        
        if not software:
            return jsonify({
                'success': False,
                'error': '软件不存在',
                'code': 404
            }), 404
        
        latest_version = software['version']
        
        # 简单版本比较（可以根据需要改进）
        def version_compare(v1, v2):
            """比较版本号，返回 1 表示 v2 > v1，0 表示相等，-1 表示 v1 > v2"""
            v1_parts = [int(x) for x in v1.split('.') if x.isdigit()]
            v2_parts = [int(x) for x in v2.split('.') if x.isdigit()]
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for i in range(max_len):
                if v2_parts[i] > v1_parts[i]:
                    return 1
                elif v2_parts[i] < v1_parts[i]:
                    return -1
            return 0
        
        has_update = version_compare(current_version, latest_version) == 1
        
        response_data = {
            'success': True,
            'data': {
                'software_id': software_id,
                'software_name': software['name'],
                'current_version': current_version,
                'latest_version': latest_version,
                'has_update': has_update,
                'update_info': {
                    'description': software['description'],
                    'platforms': software['platforms'],
                    'file_sizes': software.get('file_sizes', {}),
                    'updated_at': software['updated_at']
                } if has_update else None
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 500
        }), 500

@app.route('/static/data/settings.json')
def get_settings_json():
    """提供settings.json文件的API访问"""
    try:
        settings = load_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({"error": "Failed to load settings"}), 500

@app.context_processor
def inject_settings():
    """将网站设置注入到所有模板中"""
    return dict(site_settings=load_settings())

if __name__ == '__main__':
    init_data_files()
    import os
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)