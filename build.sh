#!/bin/bash

# 构建 Docker 镜像
echo "正在构建原理图材料列表查看器镜像..."
docker build -t smv-beta:latest .

if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功！"
    echo "运行以下命令启动应用："
    echo "docker-compose up -d"
else
    echo "❌ 镜像构建失败！"
    exit 1
fi
