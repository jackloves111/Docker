#!/bin/sh
echo "[授权] 开始验证 License..."

LICENSE_SALT="${LICENSE_SALT:-1234567890987654321}"
UUID_PATH="/host_uuid"
LICENSE_PATH="/config/license.dat"

if [ ! -f "$UUID_PATH" ]; then
    echo "[授权] 错误：无法读取主机 UUID ($UUID_PATH)"
    echo "[授权] 容器启动失败"
    exit 1
fi

if [ ! -f "$LICENSE_PATH" ]; then
    echo "[授权] 错误：License 文件不存在 ($LICENSE_PATH)"
    echo "[授权] 容器启动失败"
    exit 1
fi

UUID=$(cat "$UUID_PATH" | tr -d '\n' | tr '[:upper:]' '[:lower:]')
STORED_SIGNATURE=$(cat "$LICENSE_PATH")
CALCULATED=$(echo -n "${UUID}${LICENSE_SALT}" | sha256sum | cut -d' ' -f1)

if [ "$CALCULATED" != "$STORED_SIGNATURE" ]; then
    echo "[授权] 错误：License 验证失败"
    echo "[授权] UUID: $UUID"
    echo "[授权] 容器启动失败"
    exit 1
fi

echo "[授权] License 验证通过"
exec "$@"
