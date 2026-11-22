# 历史交付物（不作为当前源码）

V10 将四份历史文件从仓库根目录转入 `archive/legacy/`。这是一项**路径迁移**，没有删除或修改二进制内容，迁移前后 Git blob SHA 相同。

- `legacy/API_Extractor_Linux_20261107.zip`：历史 Linux 打包。
- `legacy/API_Extractor_AI_Scripts_Linux.zip`：历史 AI 启动与诊断脚本压缩包。
- `legacy/Dockerfile.backup`：早期 Dockerfile 备份。
- `legacy/Dockerfile.backup.20261113_211656`：早期时间戳备份。

当前工作源码始终以根目录 `api_extractor/`、`tools/`、`scripts/` 以及根目录 `Dockerfile` 为准。GitHub 不会自动移动用户 Ubuntu 本地下载文件；如果此前用旧文件名从仓库根目录操作，需调整到此路径。
