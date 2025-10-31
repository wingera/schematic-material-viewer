#!/bin/bash

# 停止应用
echo "正在停止原理图材料列表查看器..."
docker-compose down

if [ $? -eq 0 ]; then
    echo "✅ 应用已停止！"
else
    echo "❌ 停止应用时出错！"
    exit 1
fi
