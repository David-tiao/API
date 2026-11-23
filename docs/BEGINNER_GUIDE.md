# API Extractor 零基础入门：项目介绍、概念解释与文件结构

> **适合谁？** 从来没写过 Web 项目、不知道 API、Python、Docker、GitHub Actions 是什么的读者。
>
> **先看这一句：** 这个项目是一个“前端 API 发现与取证工具”：在**明确获得授权的网站**中，它读取网页源码、观察浏览器发出的网络请求，整理可能的接口，并提供能追溯的证据。它不是用来突破登录、盗取数据或随意扫描第三方网站的工具。
>
> **对应版本：** 2026-11-23 的仓库 `main` 结构；当前软件版本在 `pyproject.toml` 中是 `0.1.0`。若以后代码改变，以代码与根目录 `README.md` 为准。

## 1. 先用一个生活例子理解项目

想象你在网上商城按下“搜索商品”按钮：

1. **前端**（你看到的页面）接收你输入的“苹果”。
2. 前端可能向**后端**（服务器）发送“请查询苹果相关商品”的请求。
3. 后端返回一份数据，例如商品名称和价格。
4. 前端把数据显示成商品列表。

网页里看到的按钮和商品卡片是“界面”，而前后端传递数据的地址就是这个工具想寻找的 **API 接口**。

一个**假设性示例**（用来解释概念，并非声称程序在某网站找到过它）：

```text
浏览器页面： https://shop.example.test/
      │
      └── GET https://shop.example.test/api/products?keyword=apple
                                │
                                ▼
                  服务器返回 JSON 数据：
                  {"items":[{"name":"Apple"}]}
```

这个项目做的事情不是帮你买苹果，而是尝试回答：

- 网页访问了**哪些接口**？请求方法是 GET、POST，还是别的？
- API 位于哪个域名、哪个路径？携带哪些参数？
- 能否根据实际观察推测身份验证方式、响应字段？
- **证据在哪里**？哪条日志、哪条真实浏览器请求能支持这个结论？

## 2. 第一次看见的名词：一个个解释

| 名词 | 零基础解释 | 在本项目中有什么用 |
|---|---|---|
| **前端（Frontend）** | 用户能看到、操作的网页界面 | 是我们观察的对象 |
| **后端（Backend）** | 处理请求、管理数据的服务器程序 | 前端通常向它获取数据 |
| **API（接口）** | 程序与程序约定的“交流窗口” | 主要发现目标 |
| **URL** | 一个完整的网络地址 | 例如 `https://shop.example.test/api/items?page=1` |
| **Host（主机名）** | URL 中标记服务器位置的部分 | 上例的 `shop.example.test` |
| **Path（路径）** | 地址中表示资源位置的部分 | 上例的 `/api/items` |
| **Query（查询参数）** | URL 中 `?` 后面的参数 | 上例 `page=1` |
| **HTTP** | 浏览器与服务器沟通的常见协议 | API 访问的基础 |
| **GET / POST** | 两种 HTTP 请求方法；GET 常用于读取，POST 常用于提交 | 用来区分接口行为；**GET 不保证绝对只读** |
| **Request / Response** | 请求 / 响应 | 一来一回就是一次网络交互 |
| **Status Code（状态码）** | 服务器回应的数字状态 | 常见 `200` 成功、`404` 未找到、`401` 未认证、`403` 禁止访问 |
| **Header（请求头）** | 请求中的附加信息 | 可承载内容类型或认证信息 |
| **Cookie / Token** | 常见的会话/身份凭据 | 判断接口是否需要登录；不能公开真实值 |
| **JSON** | 用花括号和方括号表示结构化数据的格式 | `site.json` 和 `result.json` 使用它 |
| **HTML / CSS / JavaScript** | 网页结构 / 样式 / 交互逻辑 | 工具会采集、分析其中的接口线索 |
| **Python** | 编程语言 | 这个项目的主要实现语言 |
| **Node.js** | JavaScript 的运行环境 | 在这里主要支持 JS 代码结构分析 |
| **CLI** | 命令行程序：在终端输入命令来运行 | 项目以 `python -m api_extractor.cli` 为入口 |
| **Schema** | 对 JSON 必须有哪些字段、字段是什么类型的规则 | 检查 `result.json` 格式是否符合要求 |
| **Log / JSONL** | 运行记录；JSONL 是“一行一个 JSON 对象” | `tool.log` 用于追踪过程 |
| **HAR** | 浏览器 HTTP 请求/响应的记录格式 | 用来证明某次请求确实被观察到 |
| **Docker** | 把程序和依赖封装到相对一致的容器环境 | 便于构建和运行验收镜像 |
| **Git / GitHub** | 版本管理工具 / 代码托管平台 | 保存代码历史和协作记录 |
| **CI / GitHub Actions** | 代码更新后自动执行检查/测试 | 防止改动破坏已有功能 |

### 稍微进阶的几个词

- **静态分析（Static Analysis）**：不必实际点击网页，就阅读 JS / HTML 源码寻找接口声明。它相当于“查看说明书”，有线索，但**不能证明接口真的发生过网络请求**。
- **动态分析（Dynamic Analysis）**：用浏览器真正打开页面，观察 Fetch / XHR / SSE / WebSocket 等网络请求。它相当于“现场观察”，可以保留请求证据。
- **AST（抽象语法树）**：把 JavaScript 代码解析成结构化的树，便于找到 `fetch(...)` 等调用；本项目利用 Babel 解析器。
- **正则表达式（Regex）**：按文字模式查找内容，可作为静态分析的后备方案，但没有真正理解完整程序逻辑。
- **SPA（单页应用）**：许多页面切换并不重新加载整个网页。`#/reports` 可能是前端内部路由；本项目会在有界、安全条件下发现这些路由。
- **Lazy Loading / Chunk（懒加载代码块）**：需要打开某个页面后才下载的 JS。项目可以分析浏览器已加载的这些代码，但源码线索依旧不等于已请求的 API。
- **WebSocket**：浏览器与服务器建立持续的双向通信通道；Schema 中可能用 `WS` 表示。
- **Socket.IO**：在 WebSocket 或 HTTP 轮询之上工作的实时通信方案。`/socket.io` 的 GET、POST、WS 可能只是**传输层请求**，不应把它们直接解释成三条业务 REST API。
- **SSE（Server-Sent Events）**：服务器向浏览器持续推送事件的一种方式，通常是单向的。
- **GraphQL**：一种 API 查询方式；不同操作可能共用一个入口。项目可识别部分 GraphQL 请求，Schema 中可能使用 `GQL` 方法标识。
- **Scope（授权范围）**：告诉工具只允许访问哪些域名；项目的 `ScopeGuard` 会限制越界目标。
- **Rate Limit / Concurrency（速率限制 / 并发）**：限制每秒请求数量与同时进行的请求数量，避免程序无节制地访问服务器。
- **Recall / Precision（召回率 / 精确率）**：召回率关注“真正存在的接口找到了多少”，精确率关注“报出来的接口中有多少是真的”。**没有可靠的真值清单，就不能计算可信的正式分数。**

## 3. 程序实际怎样工作：从输入到输出

```text
你提供：授权站点 URL + site.json + 输出目录 + 运行时间预算
                            │
                            ▼
                  cli.py 读取参数
                            │
                            ▼
              pipeline.py 组织完整流程
                            │
           ┌────────────────┴─────────────────┐
           ▼                                  ▼
  config.py / scope.py                request_control.py
  读取配置、限定允许域名             限制速度和并发
           │                                  │
           └────────────────┬─────────────────┘
                            ▼
           crawler.py 收集 HTML / JS / 页面
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    static_analysis.py          dynamic_analysis.py
    阅读 JavaScript 源码         浏览器打开网页、观察请求
    Node/Babel AST + Regex       也能缓存实际加载的 JS chunk
              │                           │
              └─────────────┬─────────────┘
                            ▼
                 candidates.py 形成候选
                            ▼
            normalization.py 整理/合并数据
                            ▼
           evidence.py 检查证据是否真实对应
                            ▼
                 output.py 校验 Schema
                            │
          ┌─────────────────┴──────────────────┐
          ▼                                    ▼
    result.json                        static_candidates.json
    有真实请求证据的结果                仅有源码线索、尚未验证
          │
          └── 相关运行证据：tool.log、evidence/*.har、保存的网页/JS
```

**最重要的区别：** 工具在 JavaScript 中看到 `fetch("/api/example")`，不代表浏览器真的请求了它。本项目不会仅凭这段字符串就把它当作正式结果；未经请求证据证明的发现会进入 `static_candidates.json`。

## 4. 项目文件夹都是什么意思？

这是当前仓库的**简化目录图**。只展示重要部分，实际文件还包括其他测试和历史文档。

```text
API/                                 ← 项目根目录（整个仓库）
├── README.md                        ← 项目总说明、安装和运行方式
├── TOPIC                            ← 项目选题标识
├── api_task.md                      ← 项目任务相关说明
├── site.json                        ← 本地示例配置；不要填真实秘密并提交
├── Dockerfile                       ← 告诉 Docker 怎样构建程序镜像
├── requirements.txt                 ← Python 依赖清单
├── pyproject.toml                   ← Python 项目配置、版本、测试配置
├── package.json                     ← Node / Babel 依赖说明
├── package-lock.json                ← Node 依赖的锁定版本
├── .gitignore                       ← 告诉 Git 哪些本地文件不该提交
├── .dockerignore                    ← 告诉 Docker 构建时忽略哪些文件
├── .github/workflows/               ← GitHub 自动测试流程
├── api_extractor/                   ← Python 核心代码（重点）
├── tools/                           ← JavaScript AST 分析辅助工具
├── scripts/                         ← 安装、启动、检查、验收脚本
├── tests/                           ← 自动化测试及模拟网站
├── examples/                        ← 配置与结果格式样例
├── docs/                            ← 文档、设计说明、验收报告
├── demo/                            ← 演示材料的说明
└── archive/legacy/                  ← 历史 ZIP / Dockerfile 备份
```

注意：**核心代码实际在 `api_extractor/`，不是 `src/`。** 不要因为看过其他 Python 项目的 `src` 目录就以为这个仓库少了核心代码。这里采用的是当前经过测试的目录结构。

### 4.1 `api_extractor/`：最重要的源码目录

| 文件 | 一句话解释 | 可以把它想象成 |
|---|---|---|
| `__init__.py` | Python 包的标识和版本入口 | 文件夹的名牌 |
| `cli.py` | 解析 `--target`、`--config` 等命令行参数 | 前台接待 |
| `pipeline.py` | 安排整个扫描流程、时间预算和结果生成 | 总调度员 |
| `config.py` | 读取 `site.json` 并检查配置字段 | 读说明书的人 |
| `scope.py` | 判断 URL 是否位于允许访问的范围内 | 门卫 |
| `request_control.py` | 控制请求频率和并发数量 | 交通警察 |
| `crawler.py` | 收集网页、脚本、样式、链接和表单 | 资料收集员 |
| `static_analysis.py` | 阅读 JS 源码寻找接口线索 | 代码侦探 |
| `dynamic_analysis.py` | 用 Playwright 浏览页面并记录网络行为 | 现场观察员 |
| `candidates.py` | 将不同来源的发现整理为候选记录 | 信息登记员 |
| `normalization.py` | 统一路径、参数、鉴权，并合并重复记录 | 档案整理员 |
| `evidence.py` | 检查 HAR、日志和源码证据是否能够对应 | 证据审核员 |
| `output.py` | 按规定格式生成、校验和写入 JSON | 交付专员 |
| `result.schema.json` | 定义正式结果允许有哪些字段与类型 | 标准答题纸 |

其余专项模块：

| 文件 | 主要作用 |
|---|---|
| `redirect_policy.py` | 判断 HTTP 重定向的下一跳是否安全 |
| `sse_sampling.py` | 有界观察 SSE 事件流 |
| `graphql_semantics.py` | 识别部分 GraphQL 操作和变量特征 |
| `signature_semantics.py` | 标注观察到的签名字段，不等于还原签名算法 |
| `transport_semantics.py` | 区分 Socket.IO 轮询与 WebSocket 传输 |
| `jsonl_logger.py` | 输出 JSONL 日志并遮蔽一部分敏感字段 |
| `verification.py` | 仅在显式授权时尝试少量指定 GET 验证 |
| `offline_benchmark.py` | 使用本地已知真值和运行结果做离线质量评估；不是正式扫描主流程 |

初学者不需要一次读懂所有文件。可以先看 `cli.py`，再看 `pipeline.py`：前者告诉你“程序从哪里开始”，后者告诉你“各模块怎样连接”。

### 4.2 其他文件夹：该从哪里找东西？

| 位置 | 主要用途 | 什么时候看 |
|---|---|---|
| `tools/js_ast_analyzer.cjs` | Node + Babel 解析 JavaScript 的辅助程序 | 想研究 AST 时 |
| `scripts/start_extractor_stage8.sh` | 启动扫描的脚本 | 想运行工具时 |
| `scripts/bootstrap_project_stage1_to_10.sh` | 建立开发环境、安装依赖、运行初始测试 | 首次安装时 |
| `scripts/diagnose_environment_stage10.sh` | 检查当前环境、镜像与运行条件 | 遇到安装或运行问题时 |
| `scripts/acceptance_stage10.sh` | 针对明确授权的练习站进行双轮验收 | 做功能验收时 |
| `scripts/ci_docker_smoke.sh` | 在隔离合成网站上运行 Docker 浏览器回归 | 想了解 CI 怎样测试时 |
| `scripts/ci_lab_juiceshop.sh` | 在自行部署的 Juice Shop 上做独立双轮验证 | 想复现实测时 |
| `tests/test_*.py` | 一个个单元测试文件 | 研究某项功能是否正确时 |
| `tests/fixtures/` | 测试用的模拟网站及数据 | 想看“可控的测试题”时 |
| `examples/site.example.json` | 配置文件样例 | 首次准备配置时 |
| `examples/result.example.json` | 结果格式样例 | 想知道输出是什么样时 |
| `docs/README.md` | 文档目录 | 想继续学习时 |
| `docs/architecture.md` | 项目架构和数据流图 | 理解模块怎样配合时 |
| `docs/PROJECT_STRUCTURE.md` | 比本教程更详细的模块职责 | 开始读代码时 |
| `docs/CHANGELOG.md` | 历次改动及其原因 | 想了解演进历史时 |
| `docs/ACCEPTANCE_*.md` | 各阶段验收报告及其限制 | 想核对真实测试记录时 |
| `docs/adr/` | 重要技术选择与取舍的记录 | 想了解“为什么这么设计”时 |
| `.github/workflows/` | GitHub Actions 自动化验证配置 | 想理解 CI 时 |
| `archive/legacy/` | 旧版文件备份，**不是目前运行入口** | 仅调查历史时 |

文件后缀速查：`.py` 是 Python 程序，`.js/.cjs` 是 JavaScript 程序，`.json` 是结构化配置/数据，`.sh` 是终端脚本，`.md` 是 Markdown 文档，`.toml` 是配置文件。

## 5. 第一次动手：不碰陌生网站

**建议顺序：先了解结构 → 检查环境 → 运行测试 → 再扫描自己有权限的练习站。**

### 第一步：进入项目目录并了解命令

在 Linux 终端进入已经克隆或解压好的项目目录（下面的路径请按自己电脑的实际位置调整）：

```bash
cd /你的目录/API
ls
python3 --version
node --version
```

你应该能够看到 `api_extractor/`、`scripts/`、`tests/`、`README.md` 等文件。Linux 本地方式需要 Python 3.11+ 和 Node/npm 等依赖。

### 第二步：只检查环境，不发起站点扫描

```bash
bash scripts/diagnose_environment_stage10.sh check
```

这个命令用于检查环境；它可以在 `out/operations/` 写诊断报告。它不代表已完成对某个网站的扫描。

### 第三步：安装开发依赖（需要联网安装包）

```bash
bash scripts/bootstrap_project_stage1_to_10.sh
```

脚本会创建 `.venv/` Python 虚拟环境、安装 Python/Node 依赖和 Playwright Chromium，并运行测试。第一次安装可能需要下载大量依赖；安装前先阅读脚本并确保你信任当前仓库。

然后可以单独运行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m api_extractor.cli --help
```

`pytest` 是自动检查代码的工具；测试通过表示**当前测试覆盖的行为符合预期**，不是所有陌生网站都保证达到某个发现率。

### 第四步：只对你自己搭建或明确获授权的站点扫描

假设你**已经在自己的电脑上**部署了一个练习网站，监听在 `127.0.0.1:3000`，可以复制示例配置：

```bash
cp examples/site.example.json site.local.json

API_EXTRACTOR_MODE=local bash scripts/start_extractor_stage8.sh \
  "http://127.0.0.1:3000/" \
  "./site.local.json" \
  "./out/result.json" \
  120
```

这条命令只是使用说明，**不会替你启动一个练习网站**。如果 `127.0.0.1:3000` 没有服务，扫描不会得到有意义的目标数据。Docker 中的 `127.0.0.1` 指向容器自身，不能想当然地当作宿主机地址。

这四项参数分别是：

1. **`--target`**：从哪个获授权的网页开始扫描？
2. **`--config`**：从哪个 JSON 文件读取授权范围与可选登录配置？
3. **`--out`**：把正式结果写到哪里？
4. **`--budget`**：最多安排多少秒给整轮任务？

配置文件可以从 `examples/site.example.json` 学起：

```json
{
  "site_id": "local-practice",
  "entry": "http://127.0.0.1:3000/",
  "credentials": [],
  "headers": {},
  "allowed_hosts": ["127.0.0.1"],
  "notes": "本地自建练习网站"
}
```

- `site_id`：给这次目标起个代号。
- `entry`：可选入口信息；真正运行时的起始 URL 由 `--target` 指定。
- `credentials`：可选登录信息；空数组表示不提供账号。**不要将真实密码提交到 GitHub。**
- `headers`：自定义 HTTP 请求头；初学者可以保持空对象。
- `allowed_hosts`：允许访问的主机名单，**不能借它绕过目标站点所属授权范围**。
- `notes`：给人看的备注。

⚠️ **不要拿一个你没有授权的真实网站练手。** Juice Shop 等练习应用也优先使用自己启动的实例；公开演示站不等于允许任意自动化扫描。

## 6. 程序运行后，每种输出文件意味着什么？

常见的本地输出目录可以是：

```text
out/                             ← 执行后产生，不是仓库自带的源码目录
├── result.json                  ← 正式报告：实际请求证据审核后的接口
├── static_candidates.json       ← 仅从代码/页面发现、未证明发生过请求的线索
├── tool.log                     ← 按时间记录扫描过程（一行一个 JSON）
└── evidence/                    ← 证明来源的材料
    ├── dynamic.har              ← 浏览器请求证据
    ├── probe.har                ← 如使用显式授权 GET 验证，可能生成
    ├── js/                      ← 保存的 JS 源码（含已加载的 lazy chunks）
    └── pages/                   ← 保存的网页源码
```

### `result.json`：正式结果

可以先看仓库中的 [`examples/result.example.json`](../examples/result.example.json)。其中每条 `endpoints` 可能包含：

- `method`：例如 GET、POST、WS、GQL。
- `host` / `path`：主机及 API 路径。
- `auth`：观察与推断出的鉴权类型，例如 `none`、`cookie`、`bearer`、`apikey` 或 `sign`。
- `params.path/query/body`：路径、查询字符串、请求体中的参数结构。
- `response.fields`：能观察到的响应字段名（不等于下载完整敏感数据）。
- `evidence`：证据文件位置，HAR 证据会有 `request_index`。
- `confidence`：内部置信度指标，**不是官方精确率，也不保证接口业务语义正确**。

### `static_candidates.json`：线索，不是确认结果

例如某份 JS 中写了 `fetch("/api/later")`，但本次运行从未请求它。程序可能把它放在这里，等待人工判断；不能直接当作一个已验证接口。

### `tool.log`：程序做了什么？

这是 JSONL，不是一个巨大的 JSON 数组。常见字段包括时间 `ts`、方法 `method`、地址 `url`、状态 `status`、阶段 `phase`。公开阶段值为 `static`、`dynamic`、`verify`。

最后的 `run_status:completed` 表示本轮正常完成；`partial_browser_failure` 或 `incomplete_budget` 说明存在部分失败或时间不足。**退出码为 0，也不必然表示浏览器阶段百分之百成功，应结合日志判断。**

### `evidence/`：为什么相信这条接口？

这里可以保存页面/JS 文件和 HAR 请求记录。项目对正式结果有证据审核：请求方法、URL、状态和请求索引等需要和本轮日志对应。HAR 不是“万能安全证明”，它只帮助说明**哪些网络事实被记录到**。

日志与 HAR 会做一定脱敏，但**仍可能包含站点内部信息**；不要直接上传真实目标的输出文件到公开仓库。

## 7. 已验证的部分与还不能保证的部分

截至对应的主分支合并，项目已经对代码进行过自动回归、Docker/Chromium 合成环境测试，并在**自行部署的** OWASP Juice Shop 上做过双轮实测。具体证据见 [SPA / Socket.IO 验收记录](ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md) 和 [Lazy Chunk 验收记录](ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md)。

但以下事情**不应夸大**：

- 不能保证自动发现一个网站上的**所有** API，尤其是需要复杂登录、验证码、多因素认证、不同交互分支的接口。
- 识别到可能的签名字段，不等于能破解或复原所有签名算法。
- Socket.IO 的连接或轮询记录不一定代表独立业务接口。
- 开源练习靶场的测试通过，不等于官方隐藏考场 S1–S5 得分已经确定。
- 合成环境的越界访问测试，不等于已经完成正式考核机上的代理、DNS 和文件系统级别审计。

## 8. 推荐阅读顺序：第一次读代码就照这个走

1. **本教程**：先记住前端、API、静态分析、动态分析、证据这几个概念。
2. [根目录 README](../README.md)：学会环境要求和启动命令。
3. [`api_extractor/cli.py`](../api_extractor/cli.py)：看清楚四个命令行参数。
4. [`api_extractor/pipeline.py`](../api_extractor/pipeline.py)：理清整个运行流程。
5. [`api_extractor/crawler.py`](../api_extractor/crawler.py) 与 [`static_analysis.py`](../api_extractor/static_analysis.py)：理解代码分析从哪里获得线索。
6. [`api_extractor/dynamic_analysis.py`](../api_extractor/dynamic_analysis.py)：理解真实浏览器请求怎样被观察到。
7. [`api_extractor/evidence.py`](../api_extractor/evidence.py) 和 [`output.py`](../api_extractor/output.py)：理解结果为什么可信、输出为什么需要 Schema。
8. [`tests/`](../tests/)：读测试用例，看输入和预期结果有什么关系。
9. [架构图](architecture.md)、[目录职责](PROJECT_STRUCTURE.md)、[开发记录](CHANGELOG.md)：开始理解设计上的取舍。

### 常见疑问

**Q：我不懂 Python，也能看这份项目吗？**  
可以。先理解第 1～4 节、运行一次环境检查，再逐步学习 Python 的函数 `def`、类 `class`、`async/await`。不用先读懂全部源码。

**Q：有 `result.json` 就说明一个网站的 API 全被找到了吗？**  
不是。它只说明本轮筛选并通过证据审核的部分接口；漏掉的接口需要有可靠的真值数据才可衡量。

**Q：为什么很多文件都叫 `test_...py`？**  
因为项目使用 `pytest` 按约定寻找这些测试文件。每项测试用一个可重复的场景检查某个行为。

**Q：为什么仓库里同时有 Python 和 JavaScript？**  
Python 负责主流程、浏览器控制、日志和输出；Node/Babel 主要帮助理解被分析的 JavaScript 源码。

**Q：`main`、分支和 PR 有什么区别？**  
`main` 是主分支；开发分支是试改代码的地方；PR（Pull Request）是请求把分支改动合并进主分支的一次审查记录。

---

**读完记住这一句话就够了：API Extractor = 在授权范围内采集页面 + 分析前端代码 + 观察真实请求 + 核对证据 + 输出规范的接口清单。**

想看更细的实现，请接着读 [项目架构](architecture.md) 和 [项目目录职责](PROJECT_STRUCTURE.md)。