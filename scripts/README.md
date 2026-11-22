# scripts：稳定运行、诊断与验收入口

V10 没有移动现有 Shell 脚本，避免历史 Ubuntu 命令失效。

| 脚本 | 主要目的 |
|---|---|
| `start_safe_stage8.sh` | 首选的独立 Docker 启动、状态、日志、停止 |
| `diagnose_environment_stage10.sh` | 首选的只读检查、显式构建、测试与诊断报告 |
| `acceptance_stage10.sh` | 在已授权练习站点运行两轮，并检查 Schema/日志/HAR |
| `start_extractor_stage8.sh` | 历史兼容的启动入口 |
| `validate_contract_stage10.sh` | 历史兼容的运行契约校验 |
| `bootstrap_project_stage1_to_10.sh` | 本地开发依赖初始化 |
| `fix_apt_stage10.sh`、`fix_browser_stage10.sh` | 特定故障修复；必须先审核再执行 |

建议先运行 `bash scripts/diagnose_environment_stage10.sh check`。没有本机授权时，不要对公网目标执行自动扫描。任何脚本不得擅自重启 Docker 全局服务或处理其他容器。
