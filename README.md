# API Extractor

**TOPIC: B** — 前端 API 提取工具（API Extractor）

本项目面向经授权的 Web 站点，自动采集前端资源、分析 JavaScript、观察浏览器运行时请求，并输出结构化 `result.json`、JSONL `tool.log` 与请求证据。

> 本压缩包为 Linux 版本。压缩包内直接包含项目根目录文件；解压到 `/home/tao/API` 后，不会再多套一层 `api-extractor/` 目录。

## 1. 当前实现范围

| 计划阶段 | 当前实现 |
|---|---|
| 1. 项目初始化 | Python 工程、Node/Babel AST 分析器、依赖版本固定、测试和脚本 |
| 2. 资源采集 | HTML、外部/内联 JS、样式表、表单和同站链接采集；有界抓取 |
| 3. 静态分析 | Babel AST 分析 fetch/axios/XHR/请求封装、动态 import，并提供正则兜底 |
| 4. 动态分析 | Playwright 捕获 Fetch/XHR/EventSource；有限页面遍历和基础账号密码表单登录 |
| 5. 高级协议 | WebSocket 握手、SSE、GraphQL 请求识别 |
| 6. API 整理 | 去重、数字/UUID/哈希路径归一化、参数、鉴权和响应字段分析 |
| 7. 证据链 | JS/HTML 证据、脱敏 HAR、JSONL 请求日志和访问范围校验 |
| 8. CLI 契约 | `--target`、`--config`、`--out`、`--budget`、非交互执行和 Schema 校验 |
| 9. 测试 | 范围控制、路径归一化、鉴权和输出结构单元测试；真实练习站点仍需验证 |
| 10. 工程交付 | Dockerfile、依赖文件、README、示例配置和 Linux 启动脚本 |

这是一个可继续开发的集成版本，不代表所有边界情况均已解决。当前不会通用逆向任意加密签名算法，也不会自动处理任意业务流程、复杂 MFA、验证码或 SSO。

## 2. 目录结构

```text
/home/tao/API/
├── api_extractor/             # Python 核心模块
├── tools/                     # JavaScript AST 分析器
├── scripts/
│   ├── bootstrap_project_stage1_to_10.sh
│   ├── start_extractor_stage8.sh
│   └── validate_contract_stage10.sh
├── tests/                     # 单元测试
├── docs/                      # 架构文档
├── examples/                  # 示例配置与结果
├── demo/                      # 演示说明
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── package.json
├── package-lock.json
├── TOPIC
├── README.md
└── .gitignore
```

## 3. Linux 环境要求

- Linux x86_64（建议 Ubuntu 22.04/24.04 或兼容发行版）
- Python 3.11 或更新版本（仅本地虚拟环境模式需要；Docker 模式使用容器内 Python）
- Node.js 与 npm
- Git（可选，初始化脚本会在可用时初始化仓库）
- Docker Engine（可选；使用 Docker 模式时需要）
- Chromium 所需系统依赖（本地 Playwright 模式需要）

Ubuntu/Debian 可先安装基础工具：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git unzip
```

确认 Python 版本：

```bash
python3 --version
node --version
npm --version
```

仅在运行本地初始化脚本时，`python3` 必须为 3.11 或更新版本。**Ubuntu 22.04 宿主机使用 Docker 时无需升级系统 Python**。

## 4. 解压到指定目录

假设压缩包位于 `/home/tao/`：

```bash
sudo mkdir -p /home/tao/API
sudo chown -R "$USER":"$(id -gn)" /home/tao/API
unzip -o /home/tao/api-extractor-project.zip -d /home/tao/API
cd /home/tao/API
```

解压后应能直接看到：

```bash
ls -la /home/tao/API
# 应包含 api_extractor/ scripts/ tests/ Dockerfile README.md 等
```

不要解压成 `/home/tao/API/api-extractor/` 这种双层目录。

所有 Shell 脚本均根据自身所在位置自动定位项目根目录，不依赖写死的 `/home/tao/API`。以后移动项目目录，无需修改脚本。

## 5. 一键初始化

```bash
cd /home/tao/API
chmod +x scripts/*.sh
bash scripts/bootstrap_project_stage1_to_10.sh
```

初始化脚本会：

1. 检查 Python、Node.js 和 npm；
2. 创建 `.venv` Python 虚拟环境；
3. 安装 `requirements.txt` 中固定版本的 Python 依赖；
4. 根据 `package-lock.json` 执行 `npm ci`；
5. 安装 Playwright Chromium；
6. 运行单元测试并检查 CLI 入口。

如果本机已安装并启动 Docker，且希望初始化后同时构建镜像：

```bash
bash scripts/bootstrap_project_stage1_to_10.sh --docker
```

### Playwright 系统依赖

如果本地模式启动浏览器时提示缺少 Linux 动态库，可执行：

```bash
sudo .venv/bin/python -m playwright install-deps chromium
.venv/bin/python -m playwright install chromium
```

Docker 模式使用固定版本的 Playwright 官方 Ubuntu Noble 浏览器基础镜像，构建时不再执行 `playwright install --with-deps chromium`。仍需网络访问 Docker 基础镜像仓库、PyPI 和 npm。

## 6. 一键启动 API 提取

将组织方提供的配置文件放在项目目录中，例如 `/home/tao/API/site.json`，然后运行：

```bash
cd /home/tao/API
bash scripts/start_extractor_stage8.sh \
  "https://你的授权测试站点/" \
  "./site.json" \
  "./out/result.json" \
  1200
```

参数依次为：

1. 目标站点 URL；
2. `site.json` 配置文件路径；
3. 输出 `result.json` 路径；
4. 时间预算（秒），默认示例为 1200 秒。

启动脚本默认采用 `auto` 模式：Docker daemon 可用时使用 Docker，否则使用本地 `.venv`。也可以显式指定模式：

```bash
# 强制本地运行
API_EXTRACTOR_MODE=local bash scripts/start_extractor_stage8.sh \
  "https://你的授权测试站点/" "./site.json" "./out/result.json" 1200

# 强制 Docker 运行
API_EXTRACTOR_MODE=docker bash scripts/start_extractor_stage8.sh \
  "https://你的授权测试站点/" "./site.json" "./out/result.json" 1200
```

相对配置路径和输出路径按执行命令时所在的当前目录解析。建议先 `cd /home/tao/API` 再运行。

## 7. 验证运行契约

```bash
cd /home/tao/API
bash scripts/validate_contract_stage10.sh \
  "https://你的授权测试站点/" \
  "./site.json" \
  "./out/result.json" \
  1200
```

单独运行单元测试：

```bash
.venv/bin/python -m pytest
```

## 8. Docker 运行契约

手动构建：

```bash
docker build -t api-extractor:0.1.0 .
```

评测环境调用示例：

```bash
docker run --rm \
  --network bench-net \
  -v /bench/cfg:/cfg:ro \
  -v /bench/out:/out \
  -e HTTP_PROXY="$HTTP_PROXY" \
  -e HTTPS_PROXY="$HTTPS_PROXY" \
  api-extractor:0.1.0 \
  --target https://app.example.lab/ \
  --config /cfg/site.json \
  --out /out/result.json \
  --budget 1200
```

## 9. 配置和输出

`examples/site.example.json` 仅为格式示例。正式评测时应使用组织方提供的 `site.json`。

- `allowed_hosts` 是额外的访问白名单，不能扩大到目标站点授权域名之外。
- `credentials` 可选；当前对常见用户名/密码表单作尽力登录，不保证适配 MFA、验证码或复杂 SSO。
- 不要将真实账号口令写入源码或提交到 Git。

输出目录示例：

```text
out/
├── result.json
├── tool.log
└── evidence/
    ├── dynamic.har
    ├── js/
    └── pages/
```

`result.json` 遵循 `api_extractor/result.schema.json`。`tool.log` 为 JSONL，记录时间、方法、URL、状态码和阶段（`static`、`dynamic`、`verify`）。敏感查询参数会进行脱敏。

## 10. 已知限制与后续工作

1. **S4 签名恢复：** 当前识别疑似签名字段并保留运行时证据，不承诺通用还原任意加密算法。
2. **S3 登录：** 支持常见用户名/密码表单的尽力登录；MFA、验证码、SSO 和自定义登录组件仍需增强。
3. **S5 WebSocket：** 当前可捕获握手地址；消息帧语义和订阅结构还需扩展。
4. **S5 GraphQL：** 当前识别请求入口与请求类型；未实现完整 Schema 推断。
5. **页面探索：** 浏览器访问发现的同站链接并滚动触发懒加载；不会任意点击按钮，避免提交表单、修改数据或触发破坏性操作。
6. **响应采样：** 仅采样有限大小的 JSON 响应字段，不保存二进制或大型响应体。
7. **泛化评分：** 在取得 ground truth 前，不宣称已达到特定 Recall/Precision。提交前应在多个陌生练习站点运行并计算指标。

## 11. 第三方依赖与 AI 使用声明

| 依赖 | 版本 | License | 用途 |
|---|---:|---|---|
| Python | 3.11+ | PSF | 主运行环境 |
| HTTPX | 0.28.1 | BSD-3-Clause | HTTP 资源采集 |
| Beautiful Soup 4 | 4.13.4 | MIT | HTML 解析 |
| Playwright | 1.55.0 | Apache-2.0 | 浏览器自动化和网络观察 |
| jsonschema | 4.25.1 | MIT | 输出结构校验 |
| Node.js | 环境提供 | MIT | AST 分析运行环境 |
| @babel/parser | 7.28.4 | MIT | JavaScript AST 解析 |
| pytest | 8.4.2 | MIT | 单元测试 |

**AI 使用声明（提交前核实并修改）：** 开发过程中使用 OpenAI ChatGPT 辅助架构讨论、代码草拟、测试脚手架和文档编写。提交者必须审查、理解、测试并能够独立维护所有提交组件，并按实际使用情况更新本声明。

## 12. 开发过程证据

保留完整 Git commit 历史，不要 squash 为单次提交。保存设计笔记、中间草稿、测试输出和关键节点截图。评审可能要求解释任意函数的实现与设计取舍。


## 13. 当前修复记录与验收（请先看）

在 [docs/FIXES_AND_LESSONS.md](docs/FIXES_AND_LESSONS.md) 中记录了已经复现的缺陷、修复方案、未验证项与工程经验。新增的 `tests/test_contract_regressions.py` 和 `tests/test_integration_local_http.py` 用于回归验证，不应把单元测试通过理解成所有 S1～S5 站点评分合格。

建议依次执行：

```bash
bash scripts/diagnose_environment_stage10.sh build
bash scripts/diagnose_environment_stage10.sh test
# 仅对自己部署或获得明确授权的练习站点运行：
bash scripts/acceptance_stage10.sh https://你的授权站点/ ./site.json 180
```

`acceptance_stage10.sh` 会将两次独立运行的输出放在 `out/acceptance/`，并检查镜像大小、Schema、日志、证据链接与结果稳定性。它不会更改 Docker 服务或关闭其他容器。

**AI 使用补充声明：** 2026-11-22 期间使用 OpenAI ChatGPT 辅助完成运行契约与作用域修复、S4/S5 基础识别扩展、测试脚本和问题记录。提交者仍须对全部代码进行个人理解、真实环境复现、来源核对和最终答辩；正式提交前应按实际情况完善本声明。


## 14. 项目迭代与底层算法

阅读 [docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md](docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md)，了解迭代历史、架构数据流、AST/正则/Playwright/归一化/证据审计的设计依据，以及真实验证与当前缺口的区别。


## 15. 版本更迭记录

所有版本阶段与实际 Git 提交的对应关系、各次 AI 辅助修改原因、涉及文件、验证状态及遗留问题，统一维护在 [docs/CHANGELOG.md](docs/CHANGELOG.md)。阶段编号不是软件发行版本，当前工具版本仍为 `0.1.0`。


## 16. V8：可靠运行状态与部分结果交付

本次迭代不改变命令行参数或输出 JSON Schema。完成后可通过 `tool.log` 中最后的 `run_status:` 记录区分 `completed`、`partial_browser_failure`、`incomplete_budget` 和 `failed`。**根据评测细则 R2，部分但合法的结果允许退出码 0；应同时检查日志状态，不应把退出码 0 当作浏览器阶段全部成功。**

详细改动、对应提交和测试依据见 [docs/CHANGELOG.md](docs/CHANGELOG.md) 的 V8 记录。本轮新增 `tests/test_run_outcomes.py` 回归测试；真实 Docker 和陌生站点表现仍待验证。


## 17. V9：日志脱敏与 HAR 证据一致性

`JsonlLogger` 已强化 URL 账号密码、敏感 Query 值的遮蔽；证据审计只关联当前任务新增的 `tool.log` 行，且检查 HAR 的方法、主机、路径、请求索引与状态。输出 Schema、CLI 参数不变。详见 [V9 更迭记录](docs/CHANGELOG.md) 和 [修复经验](docs/FIXES_AND_LESSONS.md)。

离线验证为**本轮 30 项针对性测试通过**，不代表当前主分支所有测试、真实 Chromium、Docker 或隐藏站点已验收。
