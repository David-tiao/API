# API Extractor

**TOPIC: B** — 前端 API 提取工具（API Extractor）

本项目面向经授权的 Web 站点，自动采集前端资源、分析 JavaScript、观察浏览器运行时请求，并输出结构化 `result.json`、JSONL `tool.log` 与请求证据。

> GitHub 当前分支中的文本源码是项目权威版本；旧发行 ZIP 和 Dockerfile 备份已归档到 `archive/legacy/`，不要与最新代码混用。

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
API/
├── api_extractor/     # Python 核心代码：采集、分析、候选、审计与输出
├── tools/             # Node/Babel AST 分析
├── scripts/           # 稳定启动/诊断/验收入口
├── tests/             # pytest 测试
├── docs/              # 导航、架构、版本和设计决策
├── examples/  demo/   # 示例与演示
├── archive/legacy/    # 历史 ZIP 与 Dockerfile 备份
├── Dockerfile         # 当前唯一有效 Dockerfile
├── requirements.txt / pyproject.toml
├── package.json / package-lock.json
└── README.md / TOPIC / .gitignore
```

模块责任和为什么保持 `api_extractor/` 根目录结构，见 [项目结构规范](docs/PROJECT_STRUCTURE.md)。

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


## 18. V10：规范目录与职责边界

旧版 ZIP 与 Dockerfile 备份已保留原始 Git 内容并移动至 [archive/legacy](archive/README.md)。从 `pipeline.py` 抽出了候选映射纯函数模块 `api_extractor/candidates.py`，新增 8 项定向离线测试并通过。保持了 CLI、Dockerfile、脚本与输出 Schema 路径。文档导航见 [docs/README.md](docs/README.md)，代码边界见 [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)，实际修改详情见 [CHANGELOG.md](docs/CHANGELOG.md)。

本轮**未**重跑当前 GitHub 完整测试集、Docker 或真实 Chromium；严格 `src/` 布局目前仍未迁移，原因见 [ADR-0001](docs/adr/0001-compatibility-first.md)。


## 19. V11：安全作用域与 WebSocket 全局门控

已经对 `ScopeGuard` 的 R5 公共后缀判定做 fail-closed 修复，并使 WebSocket 连接纳入共享 RequestGate。变更目的、代码与 19 项专项离线测试见 [docs/CHANGELOG.md](docs/CHANGELOG.md)（V11），最新验收边界见 [docs/ACCEPTANCE_V11_2026-11-22.md](docs/ACCEPTANCE_V11_2026-11-22.md)。**没有重新运行真实 Docker/Chromium；R6 静态 API 的真实请求证据仍是待办**。保持原 CLI、Schema 和项目软件版本 `0.1.0` 不变。


## 20. V12：正式接口与静态候选分开输出

**行为变化**：`result.json` 只输出具有已核验 HAR + 本轮请求日志支持的接口；仅在 JS/HTML 中出现、尚未真实请求过的线索保存在同目录 `static_candidates.json`，标记为未验证。不会为静态候选伪造请求日志，也不会为了补证据擅自调用未知的状态变更 API。固定 CLI、原 `result.schema.json` 和 Dockerfile 不变。

本轮 50 项相关离线测试通过，但尚未重新运行 GitHub 最新完整检出版本、真实 Docker/Chromium 或接口重放。**这种精确率优先策略可能降低静态站点的覆盖率，不能保证最终评分更高。** 详细取舍见 [docs/CHANGELOG.md](docs/CHANGELOG.md)（V12）与 [V12 验收报告](docs/ACCEPTANCE_V12_2026-11-22.md)。


## 21. V13：本地显式授权 GET 验证

V12 默认不把未观察到的 JS/HTML 请求当成正式 API。V13 增加**仅限自己部署或明确获授权的练习站点**的可选功能：在本地 `site.json` 增加最多 5 个操作者事先确认可安全调用的完整 GET URL。

```json
{
  "site_id": "local-practice",
  "allowed_hosts": ["127.0.0.1"],
  "credentials": [],
  "headers": {},
  "explicit_readonly_get_urls": [
    "http://127.0.0.1:3000/api/public-items"
  ]
}
```

只有该 URL 同时存在于静态发现的 GET 候选，经过作用域和共享限流器检查，且得到真正的 2xx JSON 响应，才会记录 `tool.log` 和 `evidence/probe.har` 并在证据审计通过后进入 `result.json`。默认无字段时验证请求数为 0；不发送 Cookie、用户名/密码及自定义 Header，不跟随重定向，拒绝 Query、URL 凭据与动态占位符。

**GET 本身不保证只读，必须自行确认该 URL 的授权和无副作用。官方第 3.6 节不允许针对隐藏站点手工枚举接口作为适配方式**；本选项仅用于本地实验，不应作为正式评分提升的依据。87 项隔离离线测试通过，不意味着真实 Docker/Chromium/重放通过。见 [CHANGELOG](docs/CHANGELOG.md) V13、[V13 验收记录](docs/ACCEPTANCE_V13_2026-11-22.md) 与 [ADR-0002](docs/adr/0002-local-get-verification.md)。



## 22. V14：离线 Recall/Precision 与双轮稳定性基准

新增可**独立执行、完全离线**的 `python -m api_extractor.offline_benchmark`。从自建模拟站点的 ground truth 和两次独立运行目录读取结果、HAR、`tool.log`，计算按照考核细则权重的 Recall（40）、Precision（20），分析重复接口、第三方域名误报、HAR/日志一致性、T1/T2/T3 分档召回，以及 `0.7 × mean + 0.3 × min` 双轮修正。

使用方法：[docs/OFFLINE_BENCHMARK.md](docs/OFFLINE_BENCHMARK.md)。本轮离线执行结果：[V14 验收记录](docs/ACCEPTANCE_V14_2026-11-22.md)；更迭历史：[CHANGELOG.md](docs/CHANGELOG.md)。

**不计**官方语义 20 分、证据链 10 分和工程质量 10 分；报告的 `official_100_point_score` 固定为 `null`。隔离组合工作副本 119 项 pytest 通过，其中 V14 新增 32 项；尚未进行当前 GitHub 精确 checkout 全量测试或真实 Docker/Chromium 与隐藏站点评测。该模块仅为离线开发质量门槛，不修改正式扫描行为。



## 23. V15：同一提交自动验收

新增 [GitHub Actions 质量门禁](.github/workflows/quality-gate.yml)，用于自动运行当前 GitHub 提交的全仓库 `pytest`、语法检查，并在前者通过时构建 Docker 镜像、检查大小与构建时间，在**仅含合成 HTTP 站点**的 Docker internal 网络中运行两次真实 Chromium。结果必须包含真实 `GET /api/items` 请求、`tool.log`、HAR 与一致的接口集合，不能以空 `result.json` 冒充验收成功。

本地手动运行（必须已构建镜像、允许本机 Docker 操作）：`bash scripts/ci_docker_smoke.sh api-extractor-ci:latest`。具体契约、当前运行结果和未验证项见 [docs/ACCEPTANCE_V15_2026-11-22.md](docs/ACCEPTANCE_V15_2026-11-22.md)。

此 CI **不访问真实考核站点**，不包含任何内部资料；请先将 GitHub 仓库设为 Private，并单独完成旧提交历史清理。真实 Docker、官方 R1～R8、S1～S5 及正式重放只有实际验证后才能给出最终结论。


**V15 首轮验证更新**：GitHub Actions [Run #1](https://github.com/David-tiao/API/actions/runs/45011683183) 已真实执行，精确 checkout 137 项测试通过；Docker 28 秒构建、镜像 2,864,215,392 字节；自建隔离站点真实 Chromium 双轮各输出 1 条 API。后续提交会对 JSON Schema 和 HAR/日志索引作更严格的二次检查。参见 [V15 记录](docs/ACCEPTANCE_V15_2026-11-22.md)，这些数字不是正式隐藏站点评分。
