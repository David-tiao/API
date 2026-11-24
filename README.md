# 🎉 API Extractor — 完结撒花！🌸

**TOPIC: B · 前端 API 提取工具 · v0.1.0 · 工程开发阶段收官版（2026-11-23）**

> 从网页里找接口，不只是“猜出一个 URL”，还要解释**从哪里发现、是否真正请求过、证据在哪里**。
>
> **项目状态：已合并到 `main`，工程功能与现有自动验收完成。** 这不代表已经通过组织方隐藏站点的正式评分或全部系统级安全审计。

[📖 零基础精简篇](docs/01-overview/README.md) · [🧩 专业技术篇](docs/02-technical/README.md) · [💻 运行操作篇](docs/03-operations/README.md) · [🗺️ 文档总导航](docs/README.md) · [✅ GitHub Actions](https://github.com/David-tiao/API/actions)

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

## 🎯 能做到什么程度？不能做到什么程度？

**简短结论：已经能自动发现“本次访问实际触发”的部分前端 API，并用 HAR / 日志提供请求证据；还不能保证找全任意网站的全部 API。**

| 能力范围 | 当前真实程度 | 不应误解成 |
|---|---|---|
| **发现与整理常见前端 API** | 支持 HTML/JS 静态线索、实际浏览器请求、去重、路径和参数归纳；合成及自部署练习站有端到端结果 | 能找到一个站点的所有隐藏接口 |
| **SPA / 登录后页面** | 能访问部分安全的前端路由、加载有限 JS chunk，支持常见用户名密码表单；模拟 Cookie 登录通过测试 | 自动攻克验证码、MFA、SSO 或所有交互流程 |
| **GraphQL、WebSocket、SSE、Socket.IO** | 能观察部分协议入口、握手、轮询和有界事件线索 | 完整复现任意业务订阅、协议 Schema 或全部实时消息 |
| **签名与认证** | 能推断常见鉴权类别，标记部分疑似签名字段 | 逆向所有签名算法、伪造凭据或绕过权限 |
| **证据与结果** | `result.json` 只保留有真实请求证据的结果；未触发的源码线索单列在 `static_candidates.json` | 有 HAR 就代表业务逻辑正确，或召回率达到 100% |
| **安全和环境** | 实现授权域名检查、重定向约束、限速和部分脱敏，合成环境已测试 | 已完成正式代理/DNS/文件访问等系统级安全审计 |
| **测试成熟度** | 267 项测试、10 次 Chromium 合成场景通过；自部署 Juice Shop 双轮一致 | 已知官方 S1–S5 评分，或保证所有陌生站点都能成功 |

**实际适用：** 为自己或已获授权的练习站点建立**有证据的已观测接口清单**、辅助学习和开发回归。

**当前不适用：** 无授权扫描、任意网站全量 API 逆向、复杂认证绕过、完整签名恢复，或把自动测试结果直接当成正式考核成绩。

> 以上区分“有端到端测试证据”“实现了但效果依赖网站”“尚未支持或正式验证”。例如 Juice Shop 两轮一致，只能说明**两轮观察结果一致**，并不是 Recall 或 Precision = 100%。

👉 **[阅读详细能力清单、明确资源上限、适用与不适用场景、验证依据](docs/CAPABILITIES_AND_LIMITS.md)**

## 🧭 你应该从哪里开始？

新的 [docs 文档中心](docs/README.md) 按读者需求划分为三个专题目录：

| 阅读路线 | 内容 | 入口 |
|---|---|---|
| **01 · 零基础精简篇** | 通俗解释项目、术语、架构、文件职责与能力边界，不含运行命令 | [开始阅读](docs/01-overview/README.md) |
| **02 · 专业技术篇** | [详细架构](docs/02-technical/01-ARCHITECTURE.md)、[算法数学推导](docs/02-technical/02-ALGORITHMS.md)、[版本升级简史](docs/02-technical/03-VERSION_HISTORY.md) | [技术目录](docs/02-technical/README.md) |
| **03 · 运行操作篇** | 安装、配置、启动、Docker、查看结果、验收、离线评分及排错命令 | [命令行手册](docs/03-operations/README.md) |

## 🛠️ 快速上手

需要实际运行时，请直接阅读 [03 运行操作手册](docs/03-operations/README.md)。该手册集中维护当前命令及前置条件，包括无需外部目标的隔离合成测试，以及仅针对自建或明确获授权站点的运行方式。初次使用建议先检查环境，再运行合成测试，最后尝试自己的练习站点。

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
├── docs/                     文档中心（零基础、专业、操作三条路线）
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

还包含 `graphql_semantics.py`、`transport_semantics.py`、`signature_semantics.py`、`sse_sampling.py`、`redirect_policy.py`、`verification.py`、`offline_benchmark.py` 等专项模块，逐个解释见 [零基础篇](docs/01-overview/README.md)。

## 🔬 如何独立验证？

具体执行命令统一见 [03 运行操作篇](docs/03-operations/README.md) 的合成验收与离线评分章节。历史验证证据：

- [主分支质量门禁](https://github.com/David-tiao/API/actions/workflows/quality-gate.yml)
- [收官基线 CI：267 项测试 / 10 次 Chromium](https://github.com/David-tiao/API/actions/runs/45140723425)
- [自行部署 Juice Shop 双轮实测](docs/ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md)
- [算法与评价公式](docs/02-technical/02-ALGORITHMS.md)

单元测试、合成浏览器测试、自建练习站验证与官方隐藏评测属于不同证据等级，不得互相替代。

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

**代码已经汇入 `main`，欢迎从 [零基础篇](docs/01-overview/README.md) 开始阅读。**

> 🎉 **完结撒花！** 下一位维护者的起点：先读懂项目，再运行测试，然后在明确授权范围内扩展功能。

---

### 历史与附加资料

- [2026-11-23 完结版改写之前的完整 README 存档](docs/README_HISTORY_BEFORE_FINALE_2026-11-23.md)（旧阶段记录，仅用于追溯）
- [开发过程及架构算法](docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md)
- [历史使用与诊断指导](docs/API_EXTRACTOR_AI_OPERATIONS.md)（现行命令以操作篇为准）
- [文档总目录](docs/README.md)
