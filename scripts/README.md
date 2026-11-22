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


### V15 自动 Docker 回归

新增 `ci_docker_smoke.sh`。此脚本仅面向已存在的测试镜像及本仓库的**合成站点**：创建独立的 internal Docker 网络与临时目标容器，使用只读根文件系统加唯一 `/out` 挂载执行两次正式 CLI，并验证实际请求日志、HAR 和结果一致性。只移除脚本亲自创建的网络、容器和临时目录，不调用 `docker prune`、`systemctl`、`sudo`，不操作用户其他容器。GitHub Actions 优先在离线测试成功后执行。真实 Docker 运行结果尚待 GitHub Actions 核实。


**V15 CI 加固**：脚本后续增加独立 `jsonschema.Draft202012Validator` 校验，以及 HAR/日志之间索引、Method、URL、HTTP 状态码的核对；这类代码加固仍需在实际 GitHub Runner 上重新执行通过后才可标记通过。


**V16** `ci_docker_smoke.sh` 扩展为 SPA、SSR 各两次真实容器运行；隔离网络额外启动未授权合成站点并检查其接收日志，避免单纯信任扫描器自报的 R5 阻断行为。只清理自己创建的网络与容器。
