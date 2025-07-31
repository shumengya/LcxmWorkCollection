#!/bin/bash

# 萌芽软件库 Docker 一键部署脚本
# 作者：树萌芽
# 版本：1.0

set -e

echo "🚀 萌芽软件库 Docker 一键部署脚本"
echo "=================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查Docker Compose是否安装  
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建持久化目录
echo "📁 创建持久化目录..."
mkdir -p data static/downloads static/uploads

# 设置目录权限
echo "🔐 设置目录权限..."
chmod -R 755 data static

# 检查端口是否被占用
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 5000 已被占用，请停止占用该端口的服务或修改 docker-compose.yml 中的端口映射"
    read -p "是否继续部署？(y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 停止旧的服务（如果存在）
echo "🛑 停止旧的服务..."
docker-compose down 2>/dev/null || true

# 构建并启动服务
echo "🔨 构建Docker镜像..."
docker-compose build --no-cache

echo "🎉 启动服务..."
docker-compose up -d

# 等待服务启动
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ 服务启动成功！"
    
    # 获取本机IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "🌐 访问地址："
    echo "   网站首页: http://localhost:5000"
    echo "   网站首页: http://$LOCAL_IP:5000"
    echo "   管理后台: http://localhost:5000/admin?token=shumengya"
    echo "   管理后台: http://$LOCAL_IP:5000/admin?token=shumengya"
    echo ""
    echo "📝 重要提示："
    echo "   1. 请立即更改管理员访问令牌 'shumengya'"
    echo "   2. 生产环境请配置反向代理和HTTPS"
    echo "   3. 定期备份 data/ 和 static/ 目录"
    echo ""
    echo "📖 查看详细文档: docker-deploy.md"
    echo ""
    echo "🔧 常用命令："
    echo "   查看日志: docker-compose logs -f software-repo"
    echo "   停止服务: docker-compose down"
    echo "   重启服务: docker-compose restart"
    echo "   更新服务: docker-compose build --no-cache && docker-compose up -d"
    
else
    echo "❌ 服务启动失败，请查看日志："
    docker-compose logs software-repo
    exit 1
fi 