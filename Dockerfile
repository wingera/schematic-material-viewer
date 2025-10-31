# 使用官方 Python 运行时作为父镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_ENV=production

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 创建非 root 用户运行应用
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 创建必要的目录并设置权限
RUN mkdir -p uploads users static/css static/js templates \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app

# 复制所有应用文件
COPY --chown=appuser:appuser . .

# 检查文件是否复制成功
RUN echo "=== 检查文件结构 ===" && \
    ls -la /app && \
    echo "=== 检查静态文件 ===" && \
    find /app/static -type f && \
    echo "=== 检查模板文件 ===" && \
    find /app/templates -type f

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 关键修复：直接运行 Python 应用，不使用 Gunicorn
CMD ["python", "app.py"]
