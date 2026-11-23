# 🎉 API Extractor — 完结撒花！🌸

**TOPIC: B · 前端 API 提取工具 · v0.1.0 · 工程开发阶段收官版（2026-11-23）**

> 从网页里找接口，不只是“猜出一个 URL”，还要解释**从哪里发现、是否真正请求过、证据在哪里**。
>
> **项目状态：已合并到 `main`，工程功能与现有自动验收完成。** 这不代表已经通过组织方隐藏站点的正式评分或全部系统级安全审计。

[📖 零基础入门教程](docs/BEGINNER_GUIDE.md) · [🗺️ 文档导航](docs/README.md) · [🧩 项目结构](docs/PROJECT_STRUCTURE.md) · [📜 迭代与修复记录](docs/CHANGELOG.md) · [✅ GitHub Actions](https://github.com/David-tiao/API/actions)

## 🚀 30 秒认识这个项目

想象在购物网站搜索商品：浏览器会向服务器请求商品数据。这个请求所访问的地址，可能就是一个 **API**。

本项目只针对**自己部署或明确获授权的 Web 站点**，自动读取 HTML/JavaScript、在浏览器中观察真实 Fetch/XHR 等请求、收集接口线索，最后检查证据并输出结构化结果。简单理解为：

```text
提供授权站点 URL + 配置
          │
          ▼
读取网页 / JavaScript ───→ 源码中的 API 线索
          │
          ▼
Playwright 浏览器观察 ──→ 实际发出的网络请求
          │
          ▼
规范化、去重、参数/鉴权推断
          │
          ▼
HAR + tool.log + 源码证据核对
          │
          ├── result.json             有真实请求证据的正式结果
          └── static_candidates.json  尚未请求过的静态线索
```

**最重要的设计原则：** 代码里写了 `fetch("/api/example")`，并不等于浏览器真的访问过它；未经实际请求证明的候选**不能冒充已验证接口**。

## ✅ 完结撒花：已经做到了什么？

以下是**可复核的工程验收**，不是官方隐藏考核成绩：

| 项目 | 已验证结果 |
|---|---|
| 主分支 | 功能 PR #1、#2 均已合并至 `main` |
| Python 全仓库测试 | **267 项通过** |
| Docker + Chromium 合成验收 | **10/10**，覆盖 SPA、SPA Hash、SSR、SSE、模拟登录，各两轮 |
| 访问范围检查 | 合成环境中，越界模拟接收端没有收到被禁止的请求 |
| 独立 OWASP Juice Shop 练习环境 | 自行部署的隔离容器，两轮扫描均完整完成 |
| Juice Shop 观察结果 | 每轮 **9 条有 HAR 证据的记录**、集合一致性 Jaccard = **1.0000** |
| Socket.IO 分类 | 每轮的 **3/3 条传输记录**已标注；不能当作三条普通业务 REST API |

**对应证据：** [主分支 CI（267 项测试及 10 次 Chromium 验收）](https://github.com/David-tiao/API/actions/runs/45138090536) · [Juice Shop 独立双轮验收](https://github.com/David-tiao/API/actions/runs/45133273791) · [详细实验记录](docs/ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md)。

Juice Shop 结果来自在自己的 Docker 内网运行的实例，**不是对 OWASP 公共演示站进行自动扫描**。测试中的“9 条”表示当次观察到的 API/协议传输记录，不代表该应用所有业务接口，更不能直接推算正式 Recall/Precision。

### 功能小结

- **前端资源收集：** HTML、CSS、外部/内联 JS、表单、站内链接及受限的懒加载 JS chunk。
- **静态发现：** Node/Babel AST 分析 `fetch`、axios、XHR 等，配合正则兜底。
- **动态发现：** Playwright 捕获实际的 Fetch/XHR、受限的 SPA 路由和常见登录后请求。
- **协议线索：** GraphQL、WebSocket、SSE，以及 Socket.IO 轮询/握手类型的区分。
- **结果整理：** 路径归一化、去重、参数/鉴权/响应字段推断；真正证据与静态线索分开。
- **安全约束：** 域名授权范围、逐跳重定向检查、共享请求限流、部分敏感信息脱敏、受限的资源预算。
- **工程交付：** 固定 CLI、JSON Schema、Dockerfile、pytest、GitHub Actions、可追溯的历史验收文档。

## 🧭 你应该从哪里开始？

| 你的情况 | 推荐入口 |
|---|---|
| **完全零基础**，不懂 API、前后端、JSON 或文件夹 | [📖 零基础入门：概念 + 文件结构 + 运行示例](docs/BEGINNER_GUIDE.md) |
| **想快速运行**，电脑上已经有 Linux 和练习站点 | 往下看「5 分钟上手」 |
| **想看全部文件分别干什么** | [项目目录与模块边界](docs/PROJECT_STRUCTURE.md) |
| **想理解整体架构** | [架构图](docs/architecture.md) 和 [底层算法说明](docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md) |
| **想复现测试** | [测试与脚本说明](scripts/README.md)、[GitHub Actions](https://github.com/David-tiao/API/actions) |
| **想看修复了什么问题** | [CHANGELOG](docs/CHANGELOG.md)、[故障与经验](docs/FIXES_AND_LESSONS.md) |
| **想审查实测证据** | [Juice Shop](docs/ACCEPTANCE_JUICE_SHOP_2026-11-23.md)、[SPA / Socket.IO](docs/ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md)、[Lazy JS](docs/ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md) |
| **准备答辩或考核** | 本文的「验收边界」和 [离线评分说明](docs/OFFLINE_BENCHMARK.md) |

## 🛠️ 5 分钟上手（Linux / 自建练习站）

下面是**使用路径**，不是保证安装或扫描在任意电脑上都能 5 分钟完成。首次安装 Chromium / Python / Node 依赖可能耗时较长。

### 1. 准备环境并取得代码

推荐 Linux x86_64（Ubuntu 22.04/24.04 或兼容环境）；**本地运行**需要 Python 3.11+、Node.js、npm，并且能下载 Playwright Chromium。Docker 模式需要可用的 Docker Engine。

```bash
git clone https://github.com/David-tiao/API.git
cd API

python3 --version
node --version
npm --version

# 先做环境诊断，不扫描目标网站
bash scripts/diagnose_environment_stage10.sh check
```

### 2. 安装项目依赖、运行自检

```bash
# 建立 .venv、安装 Python/Node 依赖和 Playwright 浏览器
bash scripts/bootstrap_project_stage1_to_10.sh

# 重新检查单元测试与命令行帮助
.venv/bin/python -m pytest -q
.venv/bin/python -m api_extractor.cli --help
```

也可以在具备 Docker 的电脑上用 `docker build -t api-extractor:0.1.0 .` 构建镜像；可复现的自动 Docker 检查见 [`quality-gate.yml`](.github/workflows/quality-gate.yml)。

### 3. 只对**自己搭建或明确获授权**的练习站运行

假设你已经**另行启动**了一个本地练习站，且它在 **`http://127.0.0.1:3000/`** 正常响应：

```bash
cp examples/site.example.json site.local.json

# 显式使用本地模式：容器里的 127.0.0.1 不是宿主机。
API_EXTRACTOR_MODE=local bash scripts/start_extractor_stage8.sh \
  "http://127.0.0.1:3000/" \
  "./site.local.json" \
  "./out/result.json" \
  120
```

脚本的四个输入依次是：**起始网址、JSON 配置、输出文件、时间预算（秒）**。示例中的 `127.0.0.1:3000` 不会自动启动一个网站；没有本地目标时，不要预期生成有意义的接口结果。

- `examples/site.example.json` 只是配置格式示例；实际操作时需确认 `allowed_hosts` 与目标站点一致。
- `credentials` 是可选账号信息；**不要在公开仓库提交真实密码、Token、Cookie 或包含这些信息的配置**。
- Docker 与手动评测调用方式见 [脚本说明](scripts/README.md) 和 [零基础教程](docs/BEGINNER_GUIDE.md)。Docker 中连接练习容器时要使用正确的**容器网络和服务名**，不能直接照搬宿主机的 `127.0.0.1`。
- 即使是 GET 请求也未必完全无副作用；必须先确认有明确授权，避免对第三方公共网站任意自动扫描。

### 4. 看懂输出，不只是看有没有报错

```text
out/
├── result.json             已证据核验的接口报告
├── static_candidates.json  静态分析发现但没有实测证据的候选
├── tool.log                 一行一个 JSON 的运行日志（JSONL）
└── evidence/
    ├── dynamic.har          浏览器真实请求的 HAR 证据
    ├── probe.har            如有显式授权 GET 验证，可能出现
    ├── js/                  HTML/JS 相关的静态证据
    └── pages/
```

```bash
# JSON 是否能正常解析？
.venv/bin/python -m json.tool out/result.json

# 查看运行日志的最后几行（也要检查 run_status）
tail -n 12 out/tool.log
```

**不要只看退出码 0。** `tool.log` 的 `run_status:completed`、`partial_browser_failure`、`incomplete_budget`、`failed` 各有不同含义；有些情况下程序可以成功写出**部分但合法**的结果。

结果结构由 [`api_extractor/result.schema.json`](api_extractor/result.schema.json) 约束；可以参考 [输出样例](examples/result.example.json)。本地 `out/` 及实际目标站 HAR 可能包含敏感信息，不要原样公开。

## 🗂️ 项目目录速览

```text
API/
├── api_extractor/            Python 核心：流程、采集、分析、审计、输出
│   ├── cli.py                命令行入口
│   ├── pipeline.py           全流程调度、时间预算和结果状态
│   ├── config.py             读取 site.json
│   ├── scope.py              限定授权域名
│   ├── request_control.py    限流 / 并发控制
│   ├── crawler.py            HTML / JS / CSS / 链接采集
│   ├── static_analysis.py    JavaScript 静态 API 线索
│   ├── dynamic_analysis.py   Playwright 浏览器动态观察
│   ├── candidates.py         来源数据转候选
│   ├── normalization.py      路径、参数、鉴权、去重
│   ├── evidence.py           HAR / 日志 / 证据核验
│   ├── output.py             JSON Schema 校验与输出
│   └── result.schema.json    正式接口输出的格式要求
├── tools/                    Node / Babel AST 辅助工具
├── scripts/                  初始化、启动、诊断、验收脚本
├── tests/                    pytest 测试与合成练习站夹具
├── docs/                     入门、架构、迭代、验收文档
├── examples/                 示例配置与结果
├── demo/                     演示材料说明
├── archive/legacy/           历史 ZIP / Dockerfile 备份（非当前入口）
├── .github/workflows/        GitHub 自动验收工作流
├── Dockerfile                容器构建说明
├── requirements.txt          Python 依赖版本
├── pyproject.toml            Python 项目与 pytest 配置
├── package.json              Node/Babel 依赖声明
├── package-lock.json         Node 依赖版本锁定
├── site.json                 本地示例配置，非真实秘密
├── TOPIC                     选题标记
└── README.md                 你正在阅读的项目首页
```

**为什么没有 `src/`？** 目前实际的 Python 包就在根目录 `api_extractor/`。这是已测试并延续的布局，不应为了看起来符合某种模板而复制第二套核心代码。详见 [架构决策 ADR-0001](docs/adr/0001-compatibility-first.md)。

还包含 `graphql_semantics.py`、`transport_semantics.py`、`signature_semantics.py`、`sse_sampling.py`、`redirect_policy.py`、`verification.py`、`offline_benchmark.py` 等专项模块，逐个解释见 [入门指南](docs/BEGINNER_GUIDE.md)。

## 🔬 如何独立验证？

在已经安装依赖的本地环境：

```bash
.venv/bin/python -m pytest -q

# 高级用法：先构建镜像，确保你自己的练习服务已加入现有 Docker 网络
docker build -t api-extractor:0.1.0 .

# 假设你已有 practice-lab-net 网络，且站点容器名为 practice-web；
# site.practice.json 中的 allowed_hosts 也应允许 practice-web。
API_EXTRACTOR_NETWORK=practice-lab-net \
  bash scripts/acceptance_stage10.sh \
  "http://practice-web:3000/" "./site.practice.json" 180
```

这段双轮验收命令是**需要提前准备好容器网络和练习网站**的示例，执行前务必替换为自己的授权目标。`acceptance_stage10.sh` 通过 Docker 运行扫描器，不应直接把宿主机的 `127.0.0.1` 当作容器能访问的站点。运行前请阅读 [`scripts/README.md`](scripts/README.md)。如需查看 GitHub 的真实 CI 历史：

- [主分支 Python + Docker/Chromium 质量门禁](https://github.com/David-tiao/API/actions/workflows/quality-gate.yml)
- [最新完整基线验证：267 passed / 10 次 Chromium](https://github.com/David-tiao/API/actions/runs/45138090536)
- [自行部署 Juice Shop 双轮实测与局限](docs/ACCEPTANCE_JUICE_SHOP_2026-11-23.md)
- [两轮一致性和分数公式（离线工具）](docs/OFFLINE_BENCHMARK.md)

测试的证据范围必须分清：**单元测试 ≠ 真实浏览器合成测试 ≠ 陌生授权网站 ≠ 官方隐藏评测**。

## ⚠️ 项目边界：工程收官不等于所有场景都完美

1. **授权是前提。** 仅用于自己搭建或获得明确授权的站点；共享公共演示站也不能默认允许自动扫描。
2. **覆盖率不能凭空计算。** 没有权威接口真值 `ground truth` 时，不声称官方 Recall、Precision 或总分。
3. **复杂登录仍有局限。** MFA、验证码、跨站 SSO 和未知业务流程，不保证自动完成。
4. **签名和协议识别有边界。** 能观察部分签名字段、GraphQL、SSE、WebSocket、Socket.IO，但不保证恢复任意加密算法、业务语义或所有订阅事件。
5. **安全审计仍需正式环境复核。** 现有合成测试不能代替组织方考核机的文件访问、代理、DNS 和外部联网系统级审计。
6. **输出需要保护。** `site.json`、`tool.log`、HAR、JS 缓存、历史 Git 提交都可能携带敏感信息；将仓库设为私有并不能自动清理旧的公开历史，公开前应单独审查。
7. **项目历史保留可追溯。** 历次设计与修复记录在 `docs/`；本项目的老 ZIP / Dockerfile 备份不是当前权威源代码。

## 📚 技术依赖、致谢与 AI 使用说明

| 技术 | 版本/来源 | 用途 |
|---|---|---|
| Python | 3.11+ | 主要业务逻辑与 CLI |
| HTTPX | 0.28.1 | HTTP 采集 |
| Beautiful Soup 4 | 4.13.4 | 解析 HTML |
| Playwright | 1.55.0 | Chromium 自动浏览与真实请求观察 |
| jsonschema | 4.25.1 | JSON Schema 校验 |
| Node.js + @babel/parser | Node 环境 / Babel 7.28.4 | JavaScript AST 分析 |
| pytest | 8.4.2 | 自动化测试 |
| Docker | 依执行环境安装 | 构建、隔离与复现 |

以上技术由各自维护者开发，遵循各自许可；具体依赖声明见 [`requirements.txt`](requirements.txt)、[`package.json`](package.json)。

**AI 辅助声明：** 开发过程中使用 OpenAI ChatGPT 辅助架构讨论、代码草拟、测试、问题排查和文档编写。提交者应理解、审查并能独立解释与维护全部内容，按实际情况完善正式提交材料。这里的“完结”只指当前开发和已有测试闭环，不意味着隐瞒 AI 使用或宣称官方考核通过。

## 🌸 收官寄语

从最早能读取网页，到静态 AST、真实 Chromium、证据审计、登录后探索、SPA 懒加载、Socket.IO，再到在独立练习站上发现问题、修复问题、补回归测试——这个项目最值得保留的成果，是**每个结论都有可以复核的测试和证据**。

**代码已经汇入 `main`，欢迎从 [零基础教程](docs/BEGINNER_GUIDE.md) 开始阅读。**

> 🎉 **完结撒花！** 下一位维护者的起点：先读懂项目，再运行测试，然后在明确授权范围内扩展功能。

---

### 历史与附加资料

- [2026-11-23 完结版改写之前的完整 README 存档](docs/README_HISTORY_BEFORE_FINALE_2026-11-23.md)（旧阶段记录，仅用于追溯）
- [开发过程及架构算法](docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md)
- [更多使用与诊断指导](docs/API_EXTRACTOR_AI_OPERATIONS.md)
- [文档总目录](docs/README.md)
