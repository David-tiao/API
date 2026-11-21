# API Extractor：AI 开发约束、启动与排错说明

> 项目：前端 API 提取（考核选题 B）  
> 环境：Linux（你的工作目录为 `/home/tao/API`）  
> 交付内容：`scripts/start_safe_stage8.sh`、`scripts/diagnose_environment_stage10.sh` 和本文档。  
> 适配原则：**只新增独立脚本与说明文件，不替换现有工程文件。**

## 1. 为什么需要这套脚本

现有 API Extractor 不是常驻 Web 服务，而是**一次性执行并退出的扫描任务**。它从 `--target` 和 `site.json` 获取目标及授权范围，按预算运行静态、动态分析，最终产生 `result.json` 和 `tool.log`。

原有项目有 `scripts/start_extractor_stage8.sh`，它会在每次启动前尝试 Docker 构建；在你当前 Ubuntu 22.04 环境中，构建曾受基础镜像下载、containerd 镜像层锁定、Debian APT 网络和 Playwright 浏览器依赖安装失败影响。因此新脚本将**镜像构建**与**日常启动**分开：镜像存在时直接运行；缺少镜像时才构建，必要时可手动显式构建。

这三个新文件不承担代码修复工作；排错脚本只提供可验证的诊断与证据，不能把未运行的测试写成 PASS。

## 2. 对应你的五份 AI 规范

| 依据 | 在这个项目中的具体落地 |
|---|---|
| `AI_agent_开发规定.md` | 最小改动；不改项目核心模块、Dockerfile、Git 历史；不未经允许执行危险操作 |
| `AI_启动脚本.md` | 统一入口、环境检查、实例归属校验、生命周期锁、受控停止、状态和日志 |
| `AI_排错脚本.md` | 工具版本检查、Docker 镜像/依赖检查、显式构建、错误分类、结构化 JSON 报告 |
| `AI_测试规定.md` | 对复杂项目保留可以真实执行测试代码的入口；不把语法检查当作业务测试 |
| `AI_自我验证.md` | 开发前读文档和调用链，三轮审查（功能/安全/兼容），执行实际验证并如实报告 |

**原文适用范围说明：** `AI_agent_开发规定.md` 示例工程是 `air_vision_27`，其中关于相机、云台、串口和机器人执行器的条款不适用于当前无硬件的 API Extractor；这里移植的是工程保护、授权范围、修改记录和真实验证原则。`AI_启动脚本.md` 中多服务、多端口和串口管理的例子也不应照搬到单次 Docker 扫描任务。

## 3. 新增文件应放在哪里

把压缩包中的文件**合并解压**到已有项目，保留其他文件原样：

```text
/home/tao/API/
├── api_extractor/                   # 原有 Python 核心代码，不改
├── tools/                           # 原有 JavaScript AST 工具，不改
├── scripts/
│   ├── bootstrap_project_stage1_to_10.sh  # 原有脚本，不改
│   ├── start_extractor_stage8.sh     # 原有脚本，不改
│   ├── validate_contract_stage10.sh # 原有脚本，不改
│   ├── start_safe_stage8.sh         # 新增：启动/停止/状态
│   └── diagnose_environment_stage10.sh # 新增：排错/报告
├── docs/
│   ├── architecture.md              # 原有文档，不改
│   └── API_EXTRACTOR_AI_OPERATIONS.md # 新增：本文档
├── Dockerfile                       # 保留你目前实际版本
├── requirements.txt
├── package-lock.json
└── out/                               # 运行后产生，已被原 .gitignore 忽略
    ├── result.json
    ├── tool.log
    ├── evidence/
    └── operations/                   # 启动状态、构建日志和排错报告
```

> **注意：** 这次提供的是“三文件增量包”，不是重打包的完整工程。不要先删除 `/home/tao/API` 或覆盖当前 Dockerfile。若之前执行过修复脚本，新启动脚本会原样使用你当前的 Dockerfile。

## 4. 最简操作说明

进入项目目录并赋予新脚本执行权限：

```bash
cd /home/tao/API
chmod +x scripts/start_safe_stage8.sh scripts/diagnose_environment_stage10.sh
```

首先检查环境（不执行系统安装、构建或清理）：

```bash
bash scripts/diagnose_environment_stage10.sh check
```

如果镜像不存在，明确执行一次构建：

```bash
bash scripts/diagnose_environment_stage10.sh build
```

准备好授权目标对应的 `site.json`（不要把真实密码放进 Git）后，执行一次提取：

```bash
bash scripts/start_safe_stage8.sh start \
  "https://你的授权测试站点/" \
  "./site.json" \
  "./out/result.json" \
  1200
```

上面的 URL 需要替换为**有授权的真实测试地址**，并确保 `site.json` 与目标站点匹配；这是示例，不是可直接访问的站点。`site.json` 的格式参考 `examples/site.example.json`；`allowed_hosts` 必须限定在授权范围内。

## 5. 启动脚本命令

```bash
bash scripts/start_safe_stage8.sh start   <URL> <site.json> [out/result.json] [预算秒数]
bash scripts/start_safe_stage8.sh restart <URL> <site.json> [out/result.json] [预算秒数]
bash scripts/start_safe_stage8.sh stop
bash scripts/start_safe_stage8.sh status
bash scripts/start_safe_stage8.sh logs
bash scripts/start_safe_stage8.sh doctor
bash scripts/start_safe_stage8.sh build
```

- **start**：预检查、必要时构建、检查归属、安全移除上一次本项目容器、创建新任务、前台运行、验证输出。
- **restart**：停止已验证归属的旧任务，然后需要重新传入目标、配置、输出、预算。不会在磁盘记录或重用凭据。
- **stop**：只停止带当前项目标记的实例，不使用 `pkill python`、`docker stop $(docker ps -q)` 等宽泛命令。
- **status**：显示 `RUNNING`（运行中）、`COMPLETED`（结束且基本校验通过）、`STOPPED`/`FAILED`（已停止或异常）。扫描是批处理，不会一直保持 `RUNNING`。
- **logs**：查看项目容器日志和最近一次 `tool.log`；诊断报告在 `out/operations/` 下。
- **doctor**：调用排错脚本的 `env` 环境检查。
- **build**：显式执行当前 Dockerfile 的镜像构建。

镜像默认名 `api-extractor:0.1.0`，默认网络是 Docker 已存在的 `bridge`。如果授权练习环境处于 `bench-net`，使用：

```bash
API_EXTRACTOR_NETWORK=bench-net bash scripts/start_safe_stage8.sh start \
  "https://你的授权测试站点/" "./site.json" "./out/result.json" 1200
```

此脚本不自动创建考核网络，也不会扩大站点访问白名单。Linux 容器里的 `127.0.0.1` **不等于宿主机**；本机靶场需要正确配置容器可访问的地址和网络。

> 启动时只允许扫描你有权访问的目标。程序内部的作用域限制仍以 `scope.py` 和 `site.json` 为准；启动脚本的简单输入校验不是完整授权证明。

## 6. 排错脚本命令

```bash
bash scripts/diagnose_environment_stage10.sh check
bash scripts/diagnose_environment_stage10.sh check --build --test
bash scripts/diagnose_environment_stage10.sh env
bash scripts/diagnose_environment_stage10.sh deps
bash scripts/diagnose_environment_stage10.sh build
bash scripts/diagnose_environment_stage10.sh test
bash scripts/diagnose_environment_stage10.sh report
bash scripts/diagnose_environment_stage10.sh logs
```

| 命令 | 工作内容 | 是否改变系统或镜像 |
|---|---|---|
| `env` | 识别 Ubuntu、Docker、架构、磁盘和项目文件、Shell 语法 | 不改系统；会写诊断日志 |
| `deps` | 检查容器中的 Python、Node/Babel、Chromium 和 CLI | 不安装依赖；执行短暂容器检查 |
| `check` | 默认执行环境、项目完整性、容器依赖检查 | 不构建；会写诊断报告 |
| `build` | 显式 `docker build`，记录完整输出并分类错误 | 会更改 Docker 构建缓存和镜像 |
| `test` | 在容器里运行仓库已有 pytest | 不修改业务源码 |
| `check --build --test` | 一键执行构建、依赖检查及已有测试 | 会构建；不安装主机全局软件 |
| `report` | 查看最近一次 JSON 报告 | 只读 |
| `logs` | 查看最近一次完整诊断日志 | 只读 |

默认不执行 `apt install`、`pip install`、`sudo`、`systemctl restart`、`docker system prune`，也**不自动修改 Dockerfile**。需要修复系统级问题时，由你阅读诊断证据并明确决定。

## 7. 数据流与运行结果

```text
用户 CLI 输入 URL + site.json + 输出路径 + budget
                       |
                       v
start_safe_stage8.sh：校验项目、Docker、任务实例、输出目录
                       |
                       v
Docker 容器启动 api_extractor.cli
                       |
                       v
pipeline.py：抓取 HTML/JS → 静态分析(Regex/AST)
                     → Playwright 动态请求捕获
                     → normalize_candidates 去重/整理
                       |
                       v
             /out/result.json  + /out/tool.log
                       |
                       v
start_safe_stage8.sh：检查容器退出码和当前任务日志/结果
```

`result.json` 是结构化接口清单；`tool.log` 是 JSONL 证据。**容器退出码为 0 不代表提取成功**：当前项目 `pipeline.py` 在某些异常发生时会记录 `pipeline_error` 并写出空结果，因此新启动脚本会检查当前任务的 `tool.log`，并提醒你排查 `endpoints: []`。这仍不等于完成了考核方的全量 Schema/Recall/Precision 校验。

## 8. 诊断报告和常见故障

诊断记录写入：

```text
/home/tao/API/out/operations/
├── diagnosis_日期_进程号.log
├── diagnosis_日期_进程号.json
├── diagnosis_latest.log
├── diagnosis_latest.json
├── build_日期.log
├── lifecycle.lock
├── last_output_path
└── last_log_offset
```

可能出现的情况：

- `No such image`：项目镜像未构建。运行 `... diagnose_environment_stage10.sh build`，**不要**直接 `docker run` 未存在的镜像。
- `Unable to connect to deb.debian.org`：镜像构建时 Debian APT 仓库不可达，属于构建网络错误；不能直接归因于 Python 源码。
- `Failed to install browsers`：Playwright 浏览器或系统依赖安装失败。检查构建日志中更早出现的下载报错。
- `ref ... locked for ...`：containerd 下载/镜像层处理异常；脚本不自动清除全局缓存或重启 Docker，避免影响 `siyuan`。
- `Docker daemon unavailable`：检查当前用户权限以及 `docker info`，脚本不自动使用 `sudo`。
- `pipeline_error` 但 `result.json` 存在：结果不能视为业务成功；需要检查工具日志和抓取阶段。
- Docker 构建通过但 `endpoints` 为空：业务效果还未验证，可能是站点不可达、未登录、未触发 API 或分析能力不足。

完整诊断报告包含实际检测时间、环境、分类结果、日志路径和未解决问题。请不要公开包含敏感目标 URL 或凭据的完整日志。

## 9. 安全边界与已知限制

1. **不动其他容器**：只识别属于当前项目路径和 Linux 用户、具有预期 Docker 标签的容器；不会停止你的 `siyuan` 容器。
2. **单实例模型**：同一个项目目录默认只运行一个提取任务。`restart` 会停止该项目现有任务。
3. **自动构建有网络要求**：缺少镜像时 `start` 会构建一次。若仓库不通，会失败并留下日志；不会无限重试。
4. **没有宿主机 Python 3.11 要求**：Docker 镜像内使用 Python 3.12；宿主机 Python3 只用于配置检查、结构化报告。
5. **结果验证不是全面业务测试**：仅检查关键 JSON 字段、当前日志错误和 Docker 退出码；端到端提取效果、访问频率与考核评分仍应做独立测试。
6. **输出文件权限**：容器以你的 Linux UID/GID 运行，避免生成 root 拥有的结果文件；若当前 Dockerfile 或 Chromium 对非 root 环境不兼容，脚本会报错并保留日志，不会自动添加 `--privileged`。
7. **测试必须真实执行**：交付的文件经过静态语法及可行的模拟测试，不代表已经在你的 Ubuntu/Docker/授权靶站上完成实际构建和抽取验证。
8. **AI 开发授权**：今后的代码修改应先读 README、架构与相关源文件，说明范围、三轮审查、实际测试及未验证项；未经你的当前任务授权，不改其他文件。

## 10. 安装后自检建议

```bash
cd /home/tao/API
bash -n scripts/start_safe_stage8.sh scripts/diagnose_environment_stage10.sh
bash scripts/diagnose_environment_stage10.sh env
bash scripts/start_safe_stage8.sh status
```

如果已有镜像：

```bash
bash scripts/diagnose_environment_stage10.sh check --test
```

如果尚未构建成功，先运行显式构建并查看诊断报告：

```bash
bash scripts/diagnose_environment_stage10.sh build
bash scripts/diagnose_environment_stage10.sh report
```

### 修改清单与验证记录（交付前说明）

- **新增**：`scripts/start_safe_stage8.sh`、`scripts/diagnose_environment_stage10.sh`、`docs/API_EXTRACTOR_AI_OPERATIONS.md`。
- **未修改**：现有 `api_extractor/`、`tools/`、`Dockerfile`、`requirements.txt`、`package-lock.json`、原启动脚本、原 `.gitignore` 和 Git 历史。
- **应进行的检查**：Bash 语法、自检命令、只读诊断、Docker 命令模拟、Linux 实际镜像构建、真实练习站点运行。
- **明确未宣称**：已在你的机器上完成 Docker 端到端构建、S1–S5 实际测评或真实站点的准确率验证。
