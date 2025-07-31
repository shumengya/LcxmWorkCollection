# 使用Python 3.13.2官方镜像作为基础镜像
FROM python:3.13.2-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 配置apt使用阿里云镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main" > /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian/ bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list

# 复制requirements.txt并安装Python依赖
COPY requirements.txt .
# 配置pip使用国内镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --no-cache-dir -r requirements.txt

# 复制所有源码（除了要持久化的目录）
COPY app.py .
COPY templates/ ./templates/
COPY static/js/ ./static/js/
COPY SimpleUpdateChecker.gd .
COPY UpdatePanel.gd .

# 创建必要的目录
RUN mkdir -p data static/uploads static/downloads templates

# 创建数据目录的默认文件（如果不存在）
RUN echo '[]' > /tmp/default_software.json && \
    echo '[]' > /tmp/default_users.json && \
    echo '{"site_name": "萌芽软件库", "site_description": "发布优质软件，提升工作效率", "site_keywords": "软件下载,工具软件,免费软件", "footer_text": "© 2025 萌芽软件库. All rights reserved.", "contact_email": "admin@example.com"}' > /tmp/default_settings.json

# 创建启动脚本
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# 初始化数据文件（如果不存在）' >> /app/start.sh && \
    echo '[ ! -f /app/data/software.json ] && cp /tmp/default_software.json /app/data/software.json' >> /app/start.sh && \
    echo '[ ! -f /app/data/users.json ] && cp /tmp/default_users.json /app/data/users.json' >> /app/start.sh && \
    echo '[ ! -f /app/data/settings.json ] && cp /tmp/default_settings.json /app/data/settings.json' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# 设置权限' >> /app/start.sh && \
    echo 'chmod -R 755 /app/data /app/static' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# 启动Flask应用' >> /app/start.sh && \
    echo 'exec python app.py' >> /app/start.sh

# 设置目录权限
RUN chmod -R 755 /app && chmod +x /app/start.sh

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.settimeout(5); s.connect(('localhost', 5000)); s.close()" || exit 1

# 启动命令
CMD ["/app/start.sh"] 