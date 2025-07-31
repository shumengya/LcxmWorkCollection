# 萌芽软件库 Docker 部署指南

## 📦 快速部署

### 1. 使用 Docker Compose 部署（推荐）

```bash
# 克隆或下载项目到服务器
# 确保项目目录包含以下文件：
# - app.py
# - Dockerfile  
# - docker-compose.yml
# - requirements.txt
# - templates/
# - static/js/

# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f software-repo
```

### 2. 手动 Docker 部署

```bash
# 构建镜像
docker build -t software-repo:latest .

# 创建持久化目录
mkdir -p ./data ./static/downloads ./static/uploads

# 运行容器
docker run -d \
  --name software-repo-web \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/static/downloads:/app/static/downloads \
  -v $(pwd)/static/uploads:/app/static/uploads \
  -e FLASK_ENV=production \
  software-repo:latest
```

## 🔧 配置说明

### 环境变量
- `FLASK_ENV=production`: 生产环境模式
- `FLASK_APP=app.py`: Flask应用入口文件
- `PYTHONUNBUFFERED=1`: 禁用Python输出缓冲

### 端口映射
- 容器内部：5000
- 主机端口：5000（可修改）

### 持久化存储
- `./data` → `/app/data`: 存储软件数据、用户信息、网站配置
- `./static/downloads` → `/app/static/downloads`: 存储软件安装包
- `./static/uploads` → `/app/static/uploads`: 存储软件截图

## 🚀 访问网站

部署完成后，访问：
- 网站首页：http://your-server-ip:5000
- 管理后台：http://your-server-ip:5000/admin?token=shumengya

## 📊 监控和维护

### 查看服务状态
```bash
# 查看容器状态
docker-compose ps

# 查看健康检查状态
docker inspect software-repo-web | grep Health

# 查看实时日志
docker-compose logs -f software-repo
```

### 数据备份
```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz data/ static/downloads/ static/uploads/

# 还原数据
tar -xzf backup-20250120.tar.gz
```

### 更新部署
```bash
# 停止服务
docker-compose down

# 重新构建镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

## 🛠️ 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 修改 docker-compose.yml 中的端口映射
   ports:
     - "8080:5000"  # 改为8080端口
   ```

2. **权限问题**
   ```bash
   # 设置目录权限
   sudo chown -R 1000:1000 data/ static/
   sudo chmod -R 755 data/ static/
   ```

3. **容器无法启动**
   ```bash
   # 查看详细错误信息
   docker-compose logs software-repo
   
   # 进入容器调试
   docker-compose exec software-repo /bin/bash
   ```

## 🔒 安全建议

1. **更改管理员访问令牌**
   - 修改 `app.py` 中的 `'shumengya'` 为复杂的随机字符串

2. **使用反向代理**
   ```nginx
   # Nginx配置示例
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **防火墙配置**
   ```bash
   # 只允许必要端口
   ufw allow 80
   ufw allow 443
   ufw deny 5000  # 禁止直接访问Flask端口
   ```

## 📈 性能优化

### 生产环境建议
- 使用 Nginx 作为反向代理
- 配置 SSL/TLS 证书
- 定期备份数据
- 监控磁盘使用情况
- 设置日志轮转

### 资源限制
```yaml
# 在 docker-compose.yml 中添加资源限制
services:
  software-repo:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
``` 