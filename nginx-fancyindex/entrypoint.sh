#!/bin/sh

# 检查 /www/.theme 目录是否存在，如果不存在则复制主题文件
if [ ! -d "/www/.theme" ]; then
    echo "主题文件不存在，正在复制主题文件..."
    cp -r /tmp/.theme /www/.theme
    echo "主题文件复制完成"
else
    echo "主题文件已存在，跳过复制"
fi

# 启动 nginx
exec /usr/sbin/nginx -g "daemon off;"