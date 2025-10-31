#!/bin/bash

# 清理 Docker 资源
echo "正在清理 Docker 资源..."

# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi smv-beta:latest

# 删除数据卷（可选）
read -p "是否删除数据卷？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker volume rm schematic-materials-viewer_uploads_data
    docker volume rm schematic-materials-viewer_users_data
fi

# 清理未使用的镜像和容器
docker system prune -f

echo "✅ 清理完成！"
