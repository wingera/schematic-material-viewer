#!/bin/bash

# 启动应用
echo "正在启动原理图材料列表查看器 (基础模式)..."

# 检查必要文件是否存在
echo "检查必要文件..."
[ -f "app.py" ] && echo "✅ app.py" || echo "❌ 缺少 app.py"
[ -f "requirements.txt" ] && echo "✅ requirements.txt" || echo "❌ 缺少 requirements.txt"
[ -f "static/css/style.css" ] && echo "✅ static/css/style.css" || echo "❌ 缺少 static/css/style.css"
[ -f "static/js/app.js" ] && echo "✅ static/js/app.js" || echo "❌ 缺少 static/js/app.js"
[ -f "templates/index.html" ] && echo "✅ templates/index.html" || echo "❌ 缺少 templates/index.html"

# 创建必要的目录
mkdir -p uploads users

# 设置目录权限
chmod -R 777 uploads users

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请启动 Docker 服务"
    exit 1
fi

# 停止并删除旧容器
echo "清理旧容器..."
docker-compose down

# 删除旧镜像
echo "删除旧镜像..."
docker rmi schematic-materials-viewer:latest 2>/dev/null || true

# 构建镜像
echo "构建 Docker 镜像..."
docker build -t schematic-materials-viewer:latest .

if [ $? -ne 0 ]; then
    echo "❌ 镜像构建失败！"
    exit 1
fi

# 启动服务
echo "启动 Docker 服务..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ 应用启动成功！"
    echo ""
    echo "访问地址: http://localhost:5000"
    echo "查看日志: docker-compose logs -f web"
    echo ""
    echo "默认登录信息:"
    echo "  用户名: admin"
    echo "  密码: password"
    echo ""
    echo "当前模式: 基础模式 (Socket.IO 已禁用)"
    echo ""
    echo "要停止应用，运行: ./stop.sh"
    
    # 等待应用启动
    echo "等待应用启动..."
    sleep 5
    
    # 测试健康检查
    echo "测试应用健康状态..."
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ 应用健康检查通过"
    else
        echo "❌ 应用健康检查失败"
    fi
else
    echo "❌ 应用启动失败！"
    echo "查看详细错误: docker-compose logs web"
    exit 1
fi
