# API Extractor 版本更迭记录（CHANGELOG）

> 项目：[David-tiao/API](https://github.com/David-tiao/API) · 选题 B：前端 API 提取工具  
> 记录日期：2026-11-22（Asia/Singapore）  
> **说明**：以下“V0～V7”是便于理解的**开发迭代阶段编号**，不是正式 Git Tag 或发布版本号。当前 `pyproject.toml` 中的软件版本仍为 `0.1.0`，不要把阶段编号当作发行版本。

## 最新迭代：V8 · 运行状态与部分结果可靠性（2026-11-22）

**代码提交**：[3e3193822](https://github.com/David-tiao/API/commit/3e3193822ed8ae78ee353ece00becc133adb4659)  
**改动类型**：可靠性修复（不增加服务、不改变 CLI / Schema / Dockerfile）  
**涉及文件**：`api_extractor/dynamic_analysis.py`、`api_extractor/pipeline.py`、`tests/test_run_outcomes.py`

### 修复动机和技术依据

1. 以前 Playwright 启动异常时，`DynamicAnalyzer.run()` 只记录 `browser_phase_error` 并返回空列表；`pipeline.py` 无法区分“没有动态接口”和“浏览器根本没有启动”。
2. 以前所有页面的 `page.goto()` 都失败时，代码仍可能走到正常结束分支。
3. 以前 `asyncio.wait_for()` 预算中断后，已经观测到的动态请求可能只保存在 `dynamic.records`，却没有进入最终候选列表。
4. 考核细则 **R2** 要求退出码为 0 且输出 Schema 合法，**R3** 要求预算内落盘。因此不能把“浏览器部分失败”和“完全失败”简单混为一个非零退出码，否则可能丢失本可交付的静态结果。

### 具体实现

- 浏览器新增 `failure_reason` 阶段状态：启动异常记录异常类型；12 个以内的页面访问若全部失败，记录 `NoPagesLoaded`，并写出页面级失败日志。
- 主流程在 `wait_for` 之后统一汇总静态候选与已抓到的动态记录，仍进行域名过滤、路径归一化和 EvidenceAuditor 审计。
- `tool.log` 末尾新增可机器识别的 `verify` 事件 `run_status:<状态>`：
  - `completed`：没有检测到浏览器阶段故障，正常输出；退出码 **0**；
  - `partial_browser_failure`：浏览器阶段失败，但至少有一条经过审计的 API；退出码 **0**（按 R2 交付部分成果，**不表示全流程成功**）；
  - `incomplete_budget`：达到内部预算截止点，已落盘当前结果；退出码 **0**（R2 / R3；不等于完整覆盖）；
  - `failed`：浏览器失败且没有有效 API，或管线/输出发生严重异常；退出码 **1**。
- `result.json` 字段、`tool.log` 原有请求格式保持不变；没有添加运行期外部服务。

### 离线验证

本轮在隔离 Python 环境使用 `python -m pytest -q` 执行 **35 项测试，通过**（原有 28 项 + 新增 7 项）。新增测试覆盖：浏览器启动失败、全部导航失败、正常完成、浏览器失败但静态结果可交付、无有效结果的硬失败、预算截断保留静态证据、预算截断保留已完成的动态 HAR/日志证据。另执行 `python -m compileall -q api_extractor`，通过。

**边界**：采用本地工作副本和模拟浏览器/HTTP 夹具，未执行真实 Chromium、Docker 构建、组织方隐藏 S1～S5 站点，也未证明真实网络下所有超时都能遵守预算。不能以这些离线测试替代最终验收。

**回退定位**：本功能的代码变更可从上述提交 diff 查看；本记录单独提交，并与该提交对应。

## 1. 阅读本记录的规则

本文件独立记录**每次修改的原因、改动内容、涉及代码、验证依据、剩余风险**，以 GitHub 提交为最终可追溯来源。完整系统设计和算法见 [项目迭代、架构与底层算法](PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md)；技术问题及经验见 [修复与经验](FIXES_AND_LESSONS.md)。

**状态术语**：
- **已提交**：GitHub 默认分支实际存在对应改动。
- **局部验证**：代码、语法或离线单元/模拟集成测试有相应检查记录。
- **待真实验收**：尚无实际 Docker、Chromium、陌生练习站点或隐藏评测数据证明。
- **不代表完全满足**：单项代码缺陷修复不意味着整套 S1～S5 达到覆盖率、精确率和证据评分目标。

## 2. 迭代总览

| 阶段 | Git 提交（可点击） | 本次重点 | 变更类型 | 验证界限 |
|---|---|---|---|---|
| V0 | [`946c488`](https://github.com/David-tiao/API/commit/946c48868d52ad2db1a18427d68c891b09937585) | 初始化 API Extractor 工程 | 初始架构 | 仅有代码，未据此认定验收 |
| V1 | [`ec1e6c0`](https://github.com/David-tiao/API/commit/ec1e6c081613d0d84ed5a63f8ed579e2013f2a8b) | 修正 WS 路由调用与请求稳定等待 | 兼容性与稳定性 | 真实浏览器仍需验证 |
| V2 | [`130ca62`](https://github.com/David-tiao/API/commit/130ca62b7015cbb07f1aa7dbd8223bfea0ebfa8a) | CLI 异常、域名安全、证据和镜像契约 | P0/P1 修复 | 具备新增回归测试 |
| V3 | [`980b434`](https://github.com/David-tiao/API/commit/980b434be225d8b1f308f1bd04adb27e4a70fee1) | Body 签名判断与双轮验收工具 | 功能、测试 | Docker 双轮脚本未在真实环境执行 |
| V4 | [`33a7a0f`](https://github.com/David-tiao/API/commit/33a7a0f93382a2fc1a655ae8bc9974197b1dfb9d) | 限制浏览器临时目录写入范围 | 文件系统边界 | 需文件系统审计 |
| V5 | [`043d2b2`](https://github.com/David-tiao/API/commit/043d2b2f230ae3ca286926c5da02e410672a9535) | S5 WebSocket/SSE 静态入口补全 | 协议识别 | 仅覆盖可静态定位的入口 |
| V6 | [`ba07d6e`](https://github.com/David-tiao/API/commit/ba07d6e2636bd13c34e111cbdb86180a626df01a) | 引入 EvidenceAuditor 独立证据审计 | 架构演进 | 验证引用一致性，不是端点可重放 |
| V7 | [`5659d284`](https://github.com/David-tiao/API/commit/5659d2846572f9e43ce353d25d5c267b16360139) | 正式记录架构、算法及迭代依据 | 工程文档 | 文字对照源码，不是运行测试 |
| V8 | [`3e3193822`](https://github.com/David-tiao/API/commit/3e3193822ed8ae78ee353ece00becc133adb4659) | 失败状态显式报告、预算取消保留部分 API | 可靠性与 R2 适配 | 35 项离线测试；真实 Docker 待验收 |

以上提交按**实现顺序**排列。GitHub 原始提交时间统一以 Git 元数据为准；2026-11-21 UTC 的提交对应新加坡时间 2026-11-21 至 22 日。

## 3. 各阶段更迭详解

### V0｜初始工程骨架

- **问题/目标**：需要一套可以从目标网站提取 API、保留证据并通过 CLI / Docker 交付的完整基础结构。
- **架构设计**：Python 作为主调度；HTTPX + BeautifulSoup 进行资源采集；Node.js/Babel AST 与正则识别静态调用；Playwright 动态捕获；归一化、JSON Schema、JSONL/HAR 输出。
- **主要模块**：`api_extractor/cli.py`、`pipeline.py`、`crawler.py`、`static_analysis.py`、`dynamic_analysis.py`、`normalization.py`、`output.py`、`tools/js_ast_analyzer.cjs`、`Dockerfile`。
- **取舍**：优先建立可扩展流水线，没有证据表明初版能完整覆盖复杂业务、动态签名或隐藏站点。

### V1｜WebSocket 与动态等待策略

- **发现的问题**：Playwright 1.55 的 WebSocket route `connect_to_server()` 被不正确地 `await`；固定极短等待可能错过异步响应体。
- **主要修改**：`api_extractor/dynamic_analysis.py`，调整 WebSocket 路由调用，避免握手受 HTTP 并发槽阻塞；采用有限时间内观察请求稳定的等待逻辑。
- **为什么更合理**：按目标版本实际接口调用，并让动态请求在输出前尽量完成，降低漏记响应的概率。
- **待验证**：真实 WebSocket 连接、长轮询、持续 SSE 的行为和性能。

### V2｜运行契约、作用域和误报控制

- **发现的问题**：主流程失败时仍返回 `0`；未给 `allowed_hosts` 时兄弟子域被放行；错误 HTTP 请求可能进入结果；正则兜底可能把图片路径当作接口；容器运行/诊断契约存在缺口。
- **主要修改**：`api_extractor/pipeline.py`、`scope.py`、`normalization.py`、`static_analysis.py`、`dynamic_analysis.py`、`Dockerfile`。
- **修复内容**：错误分支返回非零退出码；默认作用域只接受目标主机及子域；动态失败请求过滤；静态伪接口特征过滤；在 Playwright 注入站点自定义 Header；记录 HAR 时间与受限的 WebSocket 帧类型元数据；最终镜像加入 `package-lock.json`。
- **新增测试**：`tests/test_contract_regressions.py`。
- **为什么有效**：错误不会再轻易伪装成成功；未明确授权的兄弟子域默认被拒绝；候选接口的判定条件更严格。
- **待验证**：真实 Docker 运行、完整 Public Suffix List 和真实浏览器异常路径。

### V3｜S4 签名推断 + 可重复的验收流程

- **发现的问题**：签名字段有时出现在 JSON/form 请求体里，仅看 Header 和 URL 会漏掉；根据字符串 `sign` 子串判断又会误报 `design`。
- **主要修改**：`api_extractor/normalization.py`、`tests/test_contract_regressions.py`。
- **新增文件**：`tests/test_integration_local_http.py`、`scripts/acceptance_stage10.sh`。
- **改进思路**：按明确的签名键集合识别，检测请求 Body；用本地 HTTP 模拟站验证抓取 HTML/JS→识别→证据→JSON 的静态链路；提供双轮 Docker 运行验收脚本，检查 Schema、日志、证据索引和输出重复性。
- **待验证**：这只是**签名存在性推断**，不等于签名算法恢复、可重算或可重放。双轮 Docker 脚本需要真实镜像才能验证。

### V4｜浏览器临时目录和文件系统边界

- **发现的问题**：浏览器可能在默认 HOME、`/tmp` 或缓存目录创建运行文件，不容易追踪写入边界。
- **主要修改**：`Dockerfile`、`api_extractor/pipeline.py`、`scripts/start_safe_stage8.sh`、`scripts/diagnose_environment_stage10.sh`、`scripts/acceptance_stage10.sh`。
- **改进思路**：设置 `HOME=/out/home`、`TMPDIR=/out/tmp`、`XDG_CACHE_HOME=/out/cache`，并在合规路径下创建目录。
- **待验证**：这些设置只能约束已知缓存入口，**不能证明所有库或系统进程都不会在其他路径写入**。

### V5｜S5 静态协议入口补全

- **发现的问题**：JS 使用 `new WebSocket(url)` 或 `new EventSource(url)` 时，原来的 `fetch/axios/XHR` 识别规则可能漏掉协议入口；只在 AST 无结果时才运行正则又可能造成漏检。
- **主要修改**：`api_extractor/static_analysis.py`、`tests/test_contract_regressions.py`、`README.md`。
- **改进思路**：增加静态 WebSocket 和 SSE 构造器匹配，将 AST 与 Regex 候选按请求标识去重合并，同时复用域名安全过滤。
- **待验证**：不意味着已经解析 WebSocket 消息订阅、SSE 完整事件语义或 GraphQL Schema。

### V6｜EvidenceAuditor：由“有引用”升级为“引用一致”

- **发现的问题**：仅检查 `evidence` 数组非空，不能证明证据文件存在、HAR 索引正确或对应同一 API。
- **新增文件**：`api_extractor/evidence.py`、`tests/test_evidence_audit.py`。
- **修改模块**：`api_extractor/pipeline.py`，在候选归一化后、最终输出前调用审计器。
- **审计算法**：规范化文件路径并限制在输出目录内；拒绝穿越和越界符号链接；检查静态证据源码片段；缓存 HAR 解析；校验索引、Method、Host、归一化 Path；与 `tool.log` 中有效动态请求交叉核验。清除无效证据，证据全部失效的 API 不输出。
- **为什么有效**：可减少“结果中引用了实际不存在或指向其他请求的证据”这类可检测的质量问题。
- **局限**：静态源码证据并不证明真实 API 存在，HAR 与日志一致也不保证接口可重放成功。

### V7｜迭代、数据流与算法文档化

- **目标**：让读者能根据代码理解为什么使用当前技术，以及修复如何影响总体架构。
- **新增文件**：`docs/PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md`。
- **更新文件**：`docs/FIXES_AND_LESSONS.md`、`README.md`。
- **文档内容**：阶段演进、主流程、模块职责、有界抓取/BFS、Babel AST 与正则、Playwright、限流器、路径归一化、证据审计、验证层次。
- **价值**：让技术取舍、缺陷复现、验收边界可以独立追溯。

## 4. 本轮新增的维护制度

**本文件是专门的版本历史台账**：从现在开始，每次实质性修改都在顶部追加条目，至少写明：

1. **日期 + Git commit**（未提交时写“待提交”，不得编造 SHA）。
2. **变更目的和根因**。
3. **实际修改文件**和影响的输入/输出。
4. **测试命令、退出码、执行环境和结果**；未运行写 `UNVERIFIED`。
5. **兼容性、安全风险及未解决问题**。
6. **回退参考**：优先查看对应 commit diff；不得未经确认直接对主分支执行强制回退。

### 文档记录增量（2026-11-22）

- 新增 `docs/CHANGELOG.md`，把以往迭代分解为可追溯的版本历史条目。
- 更新根目录 `README.md` 和架构文档中的索引链接。
- **本次只更新文档**，不修改提取算法、CLI、Docker 镜像和依赖，也不新增运行测试。
- 本次文档提交的 SHA 以 GitHub 的提交历史为准，文件创建时不提前伪造。

## 5. 当前验证状态与未解决事项

**历史测试记录（非本次重新执行）**：此前开发会话中报告过逐步增加至 28 项本地单元/模拟集成测试通过，并完成 Python/Bash 语法检查。本次修改仅为文档编写和 Git 历史/文件对照；不把历史报告升级为当前机器上的新实测结果。

**仍未验收**：
- 真正的 Docker 镜像构建、浏览器启动、镜像大小和构建时间。
- S1～S5 未知授权站点的 Recall、Precision、语义正确率与双轮稳定性。
- S3 复杂 SSO/MFA、S4 通用动态签名复算、S5 WS 订阅与 GraphQL 深度解析。
- 真实代理下的并发/RPS 和运行时文件系统访问审计。

**最终结论**：代码拥有针对已知缺陷的修复与回归测试；不能据此宣称选题 B 已通过正式综合考核。
