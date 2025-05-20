# 备注解释
```
[AutoRun]
enabled=false         # 禁用自动运行外部程序
program=              # 自动运行程序的路径（留空表示不启用）

[BitTorrent]
Session\AddExtensionToIncompleteFiles=true  # 未完成文件添加.!qB扩展名（防止误操作）
Session\AddTrackersEnabled=true             # 启用自动添加备用Tracker功能
Session\AdditionalTrackers=                 # 自定义Tracker列表（此处为空）
Session\AnnounceToAllTrackers=true          # 向所有Tracker同时汇报（加快做种）
Session\Port=36560                          # BT监听端口（需路由器映射）
Session\DefaultSavePath=/video             # 默认下载保存路径
Session\GlobalDLSpeedLimit=200000          # 全局下载限速200KB/s（单位：字节）
Session\TempPath=/video/temp/              # 未完成文件暂存目录

[Preferences]
General\Locale=zh_CN                       # 中文界面语言
WebUI\Address=*                            # Web控制台监听所有IP
WebUI\ServerDomains=*                      # 允许所有域名访问
WebUI\BanDuration=0                        # 永久封禁违规客户端（0=永久）
WebUI\CSRFProtection=false                 # 禁用CSRF保护（可能降低安全性）
WebUI\ClickjackingProtection=false         # 禁用点击劫持保护
WebUI\HostHeaderValidation=false           # 禁用主机头验证
WebUI\LocalHostAuth=false                  # 禁用本地主机免认证
WebUI\Password_PBKDF2="@ByteArray(...)"    # Web登录密码加密存储（base64+盐值）
```
