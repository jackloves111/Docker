# 容器 License 验证方案

## 原理

```
用户输入订单号(SALT) + 主机 UUID → SHA256 → License 文件
容器接收 SALT + 读取 UUID → SHA256 → 对比 License → 通过/拒绝
```

## 目录结构

```
项目/
├── run.sh                    # 安装脚本（用户输入 SALT，宿主机执行）
├── docker-entrypoint.sh      # 容器入口（验签）
└── Dockerfile                # 构建命令
```

---

## 一、宿主机端（run.sh）

### 1. 用户输入 SALT（第 37 行）

```bash
# ==================== License 签名配置 ====================
read -s -p "请输入 License SALT密钥（订单号）: " LICENSE_SALT
echo
```

### 2. License 函数

```bash
get_host_uuid() {
    cat /sys/devices/virtual/dmi/id/product_uuid 2>/dev/null | tr -d '\n' | tr '[:upper:]' '[:lower:]'
}

generate_license() {
    local uuid="$1"
    local config_dir="$2"
    local signature=$(echo -n "${uuid}${LICENSE_SALT}" | sha256sum | cut -d' ' -f1)
    echo -n "$signature" > "${config_dir}/license.dat"
}
```

### 3. 安装时生成 License

```bash
mkdir -p "$config_dir"
generate_license "$(get_host_uuid)" "$config_dir"
```

---

## 二、容器入口（docker-entrypoint.sh）

```bash
#!/bin/sh
LICENSE_SALT="${LICENSE_SALT:-1234567890987654321}"
UUID_PATH="/host_uuid"
LICENSE_PATH="/config/license.dat"

if [ ! -f "$UUID_PATH" ]; then
    echo "[授权] 错误：无法读取主机 UUID"
    exit 1
fi

if [ ! -f "$LICENSE_PATH" ]; then
    echo "[授权] 错误：License 文件不存在"
    exit 1
fi

UUID=$(cat "$UUID_PATH" | tr -d '\n' | tr '[:upper:]' '[:lower:]')
STORED=$(cat "$LICENSE_PATH")
CALCULATED=$(echo -n "${UUID}${LICENSE_SALT}" | sha256sum | cut -d' ' -f1)

if [ "$CALCULATED" != "$STORED" ]; then
    echo "[授权] 错误：License 验证失败"
    exit 1
fi

echo "[授权] License 验证通过"
exec "$@"
```

---

## 三、Dockerfile

```dockerfile
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV LICENSE_SALT=1234567890987654321

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "-m", "app.main"]
```

---

## 四、docker run 挂载和环境变量

```bash
-v /sys/devices/virtual/dmi/id/product_uuid:/host_uuid:ro \
-v "$config_dir/license.dat:/config/license.dat:ro" \
-e LICENSE_SALT="用户输入的订单号"
```

---

## 五、部署流程

```
1. 运行 run.sh
   ↓
2. 输入 LICENSE_SALT（订单号）
   ↓
3. get_host_uuid() 获取主板 UUID
   ↓
4. generate_license() 生成 license.dat
   ↓
5. docker run 启动容器（传入 LICENSE_SALT）
   ↓
6. docker-entrypoint.sh 执行验签
   ↓
7. 验签成功 → exec "$@" 启动主进程
   验签失败 → exit 1 容器停止
```

---

## 六、安全设计

| 组件 | SALT 状态 |
|------|-----------|
| **镜像内** | 只有默认值，无效 |
| **run.sh** | 用户输入，不存储在镜像 |
| **docker run** | 通过 `-e` 传入容器 |

攻击者解包镜像 → 只能拿到默认值，无法伪造 License

---

## 七、适用场景

- Docker 容器
- 需要绑定物理机的 License 验证
- 离线环境可用（无需网络）

---

## 八、优势

1. **验签在主进程启动前**：失败直接退出，不启动任何服务
2. **SALT 不存在镜像中**：更安全
3. **不依赖容器内 docker 命令**：更安全
4. **restart=always 不影响**：容器根本没启动，不会反复重启
