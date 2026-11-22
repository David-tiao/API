# API Extractor V10：验收报告（2026-11-22）

> 基准：GitHub [David-tiao/API](https://github.com/David-tiao/API)，验收源码 commit [旧提交链接已撤销]。  
> 依据：仓库内《内部考核资料（已移除）》第 3 章、6.1 节，以及《内部考核资料（已移除）》。  
> **结论：本次为部分验收，不通过最终交付验收。** 已复现一个 R5 作用域缺陷；静态证据与请求日志/可重放性存在重大缺口。不能根据离线局部测试宣称正式评测 PASS。

## 1. 验收范围与真实执行记录

| 检查 | 具体执行、版本来源 | 结果 |
|---|---|---|
| 当前 GitHub | 读取 `main` 分支、文件树、Dockerfile、依赖、CLI、Schema、核心模块和现有测试文件 | commit `旧提交标识已隐去`，完成只读检查 |
| V10 纯候选映射测试 | 从 GitHub 读取 `candidates.py` 和 `test_candidates.py`，在隔离环境逐字重建；`git hash-object` 分别等于 GitHub 的 `91c2d817…` / `45b3a367…`，执行 `python -m pytest -q` | **8 / 8 PASS** |
| R5 域名边界复现 | 用 GitHub `scope.py` 当前原文，SHA `6b823410…`，调用 `ScopeGuard` | **FAIL（已复现）** |
| 既有本地源码回归 | 本地早期/组合副本 `api_quality_v9/`，`python -m pytest -q` | 30 / 30 PASS；**不是当前 GitHub V10 整仓库测试** |
| 静态证据可重放性 | 本地 HTTP 模拟页，仅含 `fetch("/api/real-lookup")`，模拟禁用浏览器阶段，执行旧副本主流程 | 生成 1 条 `GET /api/real-lookup`，但 `tool.log` 没有对应 API 请求 |
| 请求速率器 | `request_control.py` 当前 GitHub SHA 与本地字节一致；30 个模拟任务 | 观察到最大同时执行 2，最短发起间隔约 0.0503s；这只是局部算法检查 |
| CLI/Schema | `cli.py`、`output.py`、`result.schema.json` 与 GitHub 当前 Blob SHA 相同；检查 CLI `--help`、Python 编译、Node/Bash 语法（本地旧脚本） | 通过；但不是容器运行 |
| Docker/Playwright/真实网络 | 当前隔离执行环境无 Docker daemon，无法联网下载 GitHub 整仓库快照，也未启动 Chromium 或扫描外站 | **UNVERIFIED** |

**重要说明**：不能把 8 与 30 相加称为“V10 全仓库 38 项通过”。因为它们运行于不同工作副本，并未覆盖同一提交的全部源文件。此前聊天中提到的 35 项、30 项也是历史不同范围的结果。

## 2. 考核硬性契约 R1—R8

| 条款 | 验收状态 | 静态和离线证据 / 不能证明之处 |
|---|---|---|
| R1 非交互 | **静态通过** | `cli.py` 使用 argparse 固定参数，Dockerfile 指定 ENTRYPOINT，没有必需的 stdin 确认 |
| R2 退出 0 + Schema | **部分满足/待容器** | `output.py` 采用 Draft 2020-12 Schema 校验与原子替换；`pipeline.py` 对部分结果的退出状态有策略，但真实 Docker 端到端未运行 |
| R3 预算内完成 | **待验证** | 存在 `asyncio.wait_for`，但清理浏览器、写 HAR 与最终写盘也需计入墙钟时间；没有超时审计 |
| R4 ≤8 并发、≤20 RPS | **部分满足，有缺口** | `RequestGate` 对一般 HTTP 受限；Playwright WebSocket 路由中 `connect_to_server()` 绕过共享门控，尚未证明 WS 握手满足全局限流 |
| R5 同域/子域限制 | **未通过：复现缺陷** | 自制公共后缀表不完整，详见第 3 节 |
| R6 `/out/tool.log` 及请求记录 | **静态部分满足** | Docker 入口下固定 `/out/tool.log`、JSONL 有 method/url/status；但静态接口不一定有对应后端请求记录，影响第 3.6 节的更严格证据要求 |
| R7 只在 `/out` 写入 | **待验证** | 设置 HOME、TMPDIR、XDG_CACHE_HOME，输出路径有限制；无真实进程文件系统审计 |
| R8 无外部 API/LLM | **静态基本符合，待联网审计** | 未见运行期外部大模型接口；代理/浏览器/重定向的实际流量尚未经审计 |

**状态解释**：静态符合设计 ≠ 在组织方 Docker 运行契约下通过；R5 的复现则证明了一个可触发的边界错误。

## 3. 已复现的主要失败项

### P0-1：R5 公共域后缀识别不足

当前 `api_extractor/scope.py` 用手写 `_MULTI_LABEL_SUFFIXES` 识别可注册域，没有 `co.za`。可在 GitHub 当前版本的 `ScopeGuard` 复现：

```python
from api_extractor.scope import ScopeGuard, registrable_domain

guard = ScopeGuard(
    "https://app.example.co.za/",
    ["app.example.co.za", "unrelated.co.za"],
)
print(registrable_domain("app.example.co.za"))  # co.za（错误：过宽）
print(guard.is_allowed("https://unrelated.co.za/api"))  # True（不应放行）
```

**问题性质**：合法配置项不等于所有配置都属于目标站点。当前实现可能在某些公共后缀下把无关域名视为同域，违背 R5；组织方对越界访问实施严格处罚。

**修复方向**：使用随镜像离线提供的完整 Public Suffix List 或同等准确的域名边界方案，并在 `allowed_hosts` 初始化时验证授权主机和目标是否处于真正相同的注册域；补 `co.za`、`co.uk`、`github.io`、IP 地址、端口、Unicode/IDNA 的回归测试。不能只加一个特例来掩盖算法缺陷。

### P0-2：静态接口证据不等于 API 实际存在

现有 `normalization.py` 可将源码中的 `fetch("/api/...")` 作为静态候选；`evidence.py` 对 bundle/html 证据主要核查本地文件和片段内容，不要求真实 API 请求。采集日志记录的是下载 HTML/JS 的 HTTP 请求，而不是所有静态推断的 API。

在本地隔离 HTTP 模拟站复现：`result.json` 中出现 `GET /api/real-lookup`，`tool.log` 只有对 `/` 和 `/app.js` 的 GET，没有对 `/api/real-lookup` 的请求。该模拟使用旧副本，但 GitHub 当前源码仍保留了对应的证据接受逻辑。

**问题性质**：第 3.6 节明确要求输出 API 在日志中能找到对应请求证据，抽查 10 条重放，命中低于 80% 时该站点计 0 分。不能把静态代码字符串当成已验证的后端接口。

**修复方向**：分别标记“静态观察”和“动态已确认”；对**已获授权、确认只读且不会改变状态**的请求进行安全验证、记录状态与证据，保留无法安全验证的候选但明确可信度。不能为了满足日志项对未知 POST/DELETE 盲目发起请求。

### P1-1：WebSocket 握手没有计入共享请求门控

`dynamic_analysis.py` 的 websocket route handler 对允许 URL 直接调用 `websocket_route.connect_to_server()`。需为 WS 握手提供预算和限流策略，避免与普通 HTTP 门控产生死锁，同时符合全局 R4。

### P1-2：供应链锁定与交付复现不充分

`requirements.txt` 采用顶层 `==` 固定版本，未附 Python 包 hash，也未在仓库看到 `uv.lock`；`package-lock.json` 则用于 npm。组织方要求完整锁定依赖。不能在不实际构建的情况下证明镜像 15 分钟、6GB，或运行期完全离线安装。

### P1-3：提交结构与材料差异

根目录有 `api_extractor/`，而考核第 6 章的提交结构列出 `src/`；`README.md` 顶部已有 `TOPIC: B`，但参赛者姓名/学号/院系尚需在提交模板中补充。不要为表面合规创建空目录或复制第二套源码，后续迁移应与 Docker 同步验证。

## 4. S1—S5 功能适配判断（不计虚构分数）

| 类别 | 当前已有能力 | 尚需证明或扩充 |
|---|---|---|
| S1：单页 JS bundle | Babel AST、Regex、静态脚本抓取及动态 import | 大型 bundle、变量拼接、真实 API 可访问性 |
| S2：SSR/表单 | HTML 表单、同站链接、外部/内联脚本 | 登录状态、局部 AJAX 和安全交互覆盖率 |
| S3：登录懒加载 | 常见登录表单、Cookie/Headers、有限页面遍历 | 登录成功判断、JS 路由、复杂身份认证 |
| S4：动态签名 | 检测 URL/Header/Body 的 sign/signature 等字段 | 通用签名还原、可复算请求和强证据 |
| S5：WS/SSE/GraphQL | 握手和协议入口、部分帧元数据及 Query/Mutation 观察 | 完整订阅语义、GraphQL variables/schema 和限流验证 |

考核评分依赖隐藏站点的真实 TP、FP、FN、参数与业务语义；**当前没有 ground truth，不能给分数、排名或达标百分比**。

## 5. 合规和原创性单列提醒

《考核细则》1.1、1.4、1.5 以及《公告》4.1 规定：赛前仅允许选型、环境准备和通用脚手架；核心实现须参赛者在 T0 后的 48 小时内独立完成，并如实披露 AI 使用范围、保留开发过程证据。当前 GitHub 已有多个核心代码提交，但**未知官方 T0**，无法断定这些提交是否符合时间规则。正式交付前必须按官方解释核对，不得以改提交时间、篡改历史或冒充人工独立完成的方式规避规则。

## 6. 下一步建议（优先级顺序）

1. **立即修 R5 公共后缀边界**并增加越界测试。
2. **改善静态 API 真实性证据**，将可观察与可验证分开，优先保证 precision 和可核查日志。
3. 修复 WebSocket 的全局请求门控；补网络并发/速率测试。
4. 补齐 Python 依赖的可复现锁定；在有 Docker 的 Ubuntu 上独立构建并检查运行期文件系统和代理。
5. 运行 GitHub 当前提交的**全仓库** `python -m pytest -q`，再使用至少一个新的授权练习站点双轮测试及 ground truth 对照。
6. 根据 T0 官方要求核对原创性、提交路径、身份信息及 AI 使用声明。

**验收结论**：V10 已具备有价值的工程骨架，新增候选映射模块本身通过 8/8 精确版本离线测试；但至少 R5 边界存在确定性缺陷、静态 API 证据不足，另外 Docker 与隐藏站点指标未验证。**当前不能签署“全部验收通过”。**
