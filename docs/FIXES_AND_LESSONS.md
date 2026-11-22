# API Extractor 修复记录与工程经验

> 检查基础：GitHub `David-tiao/API` 的 `main` 分支（修复前 commit `旧提交标识已隐去`）。
> 本文记录问题、具体修复、可复现检查和仍未通过的验收项。禁止把静态审查当作隐藏站点的评分结果。

## 1. 范围与原则

本轮仅修复 API 提取工程本身的真实缺陷，不修改其他仓库、不修改用户 Ubuntu 系统配置、不重启 Docker、不清理用户数据。遵循 AI 辅助开发约束中的最小修改、证据保存、三轮审查原则。开发者需要阅读并理解核心实现，提交前如实更新 AI 使用声明。修改记录由 Git 历史保存。

## 2. 已发现问题与修复

| ID | 问题与证据 | 修复文件 | 处理 |
|---|---|---|---|
| P0-01 | `pipeline.py` 捕获异常后只输出空 `endpoints`，返回 0，产生假成功 | `api_extractor/pipeline.py` | 出现 pipeline 或输出验证错误时返回非零退出码；保留结构化空结果和日志 |
| P0-02 | 无 `allowed_hosts` 时 `app.example.com` 可扫描兄弟域名 `api.example.com` | `api_extractor/scope.py` | 默认仅允许目标主机及其子域；显式白名单仍支持同注册域内获授权的兄弟子域 |
| P0-03 | 自定义 `--out /out/nested/result.json` 时日志被放到 `/out/nested/tool.log`，不符合 R6 | `api_extractor/pipeline.py` | 容器中固定 `/out/tool.log`；证据统一保存到 `/out/evidence/` |
| P0-04 | 输出目录创建发生在容器路径约束验证之前 | `api_extractor/pipeline.py` | 首次写入前先验证 `--config` 与 `--out` 的规范化路径 |
| P0-05 | Dockerfile 未复制 `package-lock.json`，环境检查脚本会找不到文件 | `Dockerfile` | 最终镜像复制该锁文件 |
| P1-01 | 动态请求失败（状态 -1/0）仍进入候选 API，容易形成误报 | `pipeline.py`、`normalization.py` | 传递 HTTP 状态并排除未完成/错误请求；401/403 保留作鉴权线索 |
| P1-02 | 正则兜底把 `fetch('/images/logo.png')` 当 API | `static_analysis.py` | 在 fallback 也应用已有 API 特征过滤 |
| P1-03 | Playwright 未注入 `site.json` 中必需的自定义 Header | `dynamic_analysis.py` | 创建浏览器上下文时设置 `extra_http_headers` |
| P1-04 | 脱敏 HAR 的 `startedDateTime` 是 null | `dynamic_analysis.py` | 请求时记录 ISO8601 时间，保留证据时间信息 |
| P1-05 | WebSocket 只记录连接地址，缺少消息方向/类型证据 | `dynamic_analysis.py` | 有界采集帧方向和安全的协议类型名，不记录原始消息体、令牌或私密数据 |

改动仅适用于其所述范围，未修改真实站点凭据或本地评测环境。对于 `--budget` 小于 4 秒的情况，采集时间提前预留输出余量；完整预算限制仍需要容器端到端测量。

## 3. 验证命令

```bash
python -m pytest -q
python -m compileall -q api_extractor
bash -n scripts/start_safe_stage8.sh scripts/diagnose_environment_stage10.sh
docker build -t api-extractor:0.1.0 .
docker run --rm --pull=never api-extractor:0.1.0 --help
```

本轮在隔离 Python 环境运行了 21 项单元/本地集成测试，全部通过；`compileall` 和 Bash 语法检查也通过（动态分析模块的浏览器生命周期仍需真实 Chromium 实测）。这不是对 GitHub CI、Docker 构建或隐藏靶场的通过声明。所有未执行项必须在实际 Ubuntu/Docker 环境运行后再勾选。

## 4. S1～S5 功能覆盖与剩余缺口

| 场景 | 当前能力 | 必须追加的实测 |
|---|---|---|
| S1 | HTML/JS 抓取 + Babel AST + regex | React/Vue 多 bundle、变量拼接、精确率 |
| S2 | 表单 action / 多页同站链接 | 多页面与局部 AJAX 的 ground truth 对照 |
| S3 | 基础表单登录、懒加载链接、会话 Cookie、配置 Headers | SSO/MFA、登录成功判断、JS 路由交互 |
| S4 | 动态运行时捕获签名请求、辨认签名参数 | 签名算法还原与重放未实现，不能宣称完成 |
| S5 | WebSocket 握手及帧元数据、SSE 与 GraphQL 请求 | WS 订阅关联、GraphQL variables/schema 完整解析与可复验性仍不足 |

## 5. 经验与可操作结论

1. **Schema 正确不等于采集成功**：异常必须通过退出码和日志区分；`endpoints: []` 只能表示结果为空。
2. **配置白名单优先，不能以相同二级域推定授权**：默认安全拒绝，明确授权才放行。
3. **按真实 HTTP 结果衡量证据**：网络失败、404 与 JS 字符串命中不是同一强度的证明；静态候选需要可追溯代码位置。
4. **Docker 依赖要能在离线运行时使用**：构建阶段下载并固定，运行阶段不应安装额外包。之前出现 `deb.debian.org` 断连和 containerd layer lock，不能靠无差别重启或删除全局缓存解决。
5. **Playwright 版本必须匹配镜像**：目前 `v1.55.0-noble` 与 Python 依赖 `playwright==1.55.0` 对齐；正式交付必须测实际浏览器启动。
6. **保护凭据和用户资产**：不记录 HTTP 认证头和 WS 原始消息、不修改第三方容器、不自动删除 Docker 数据。
7. **有限自动交互与复杂签名是泛化短板**：没有多站点基准测试和签名复现证据，不能假定 S4/S5 已达标。

## 6. 尚未通过的正式验收门槛

- [ ] 在 Ubuntu Docker 环境完成 `docker build` 并实测构建耗时 ≤15 分钟和镜像体积 ≤6 GB。
- [ ] 以完整评测命令在 `bench-net` 运行两轮，检查 `/out/result.json`、`/out/tool.log`、`/out/evidence/`。
- [ ] 验证所有访问严格属于授权站点范围，并经代理按 ≤8 并发、≤20 RPS 执行。
- [ ] 在陌生的 S1～S5 授权练习站点上取得 ground truth，测量 Recall、Precision、语义和证据可重放率。
- [ ] S4 动态签名的可复验请求尚未实现通用处理；S5 高级协议也需扩展。
- [ ] 根据评审附录检查 Python 依赖 hash 锁定与所有供应链校验项。
- [ ] 检查 README 中 AI 辅助声明、第三方 License、个人原创提交证据与提交时间规则。

**状态：本轮属于针对已知问题的实现和局部回归测试，不等于最终综合考核 PASS。**

## 7. 追加修复与验收工具

- POST 的 JSON/form Body 中 `signature`、`sign` 等签名字段现在参与 `auth=sign` 推断；排除 `design` 等普通字段的误判。仅推断签名存在，不伪称已还原签名算法。
- 新增 `tests/test_integration_local_http.py`，使用真实本地 HTTP 服务器运行静态采集→证据→JSON 全链路；浏览器阶段在此测试中显式替换为无操作 stub。
- 新增 `scripts/acceptance_stage10.sh`。使用明确授权的目标和现有 Docker 镜像独立执行两次，核查容器退出状态、镜像体积、Schema、`tool.log`、证据路径/HAR 索引、两次输出差异；仅写入 `out/acceptance/`，不修改 Docker 服务或其他容器。
- 使用方法：`bash scripts/acceptance_stage10.sh https://你的授权练习站点/ ./site.json 180`。必要时环境变量 `API_EXTRACTOR_NETWORK=bench-net` 指向已存在的 Docker 网络。
- **验证边界：**本次本地 Python 3.13 环境完成 19 项测试与源码语法验证；此验收脚本仅通过 Bash 语法和帮助输出检查，因当前容器没有 Docker daemon，未执行真实 Docker 双轮验收。

## 8. 容器临时文件边界（R7）

浏览器框架会创建临时 profile/cache；默认 Linux 位置可能位于 `/tmp` 或用户主目录。为尽量满足“运行期不得写出 `/out`”的约束，Dockerfile 现声明 `HOME=/out/home`、`TMPDIR=/out/tmp`、`XDG_CACHE_HOME=/out/cache`，并在执行管线时在已核准的 `/out` 下创建子目录。启动/诊断/双轮验收脚本使用相同环境变量。

**风险和待测：** 这些设置仅引导已知框架缓存路径，不能证明 Chromium、动态链接器和第三方包不存在其他临时写入。需要在评测容器中用文件系统审计确认 R7；不能仅凭静态配置宣称满足全部规则。路径校验先于创建，避免误写到挂载点外。


## 9. S5 静态入口增量识别

发现部分前端仅通过 `new WebSocket(url)`、`new EventSource(url)` 声明实时通道，现有静态请求模式容易遗漏。因此在正则后备分析中识别字符串形式的 WebSocket（`WS`）和 SSE（`GET`）入口，并和 AST 结果合并去重，防止 AST 先发现其他接口时跳过这两类通道。新增两项测试验证 S5 地址发现和越界过滤。

**限制：** 动态拼接的 WebSocket URL、帧内完整订阅载荷、GraphQL 变量类型及签名复现仍需要进一步完善和真实授权站点验证。此处“发现入口”不等于高级协议全部实现。

## 10. 证据审计模块（新增）

新增 `api_extractor/evidence.py`，在 `pipeline.py` 归一化后、写入结果前运行：验证证据来源属于 `/out`，拒绝缺失、路径穿越和越界符号链接；验证 HAR 请求索引、Method/Host/Path 及 `tool.log` 中实际动态请求。仅移除无效引用，失去全部证据的 API 不输出，问题数量写入 `verify` 日志。

这是面向 R6 和证据链评分的架构加固：**源码中声明过某个接口不等于网络实际调用**。它只能改善引用的一致性，无法替代接口可达性测试、签名重放和实际 S1～S5 评测。

隔离环境新增 7 项证据审计测试；本轮总计 **28 项单元和本地模拟 HTTP 测试通过**，并通过 Python/Bash 语法检查。Docker、真实 Chromium 和外部练习站点没有测试。

系统设计、迭代时间线及底层算法详见 [PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md](PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md)。

## 11. V8：浏览器失败、预算中断与 R2 的契约权衡（2026-11-22）

**根因**：浏览器启动失败被 `DynamicAnalyzer.run()` 捕获后只写日志、返回空记录；所有页面导航失败也可能不影响主流程的完成判断。同时，预算取消时，已观察到的请求可能仅位于 `dynamic.records`。若为所有部分失败返回非零退出码，又会违反考核 R2 对合法部分结果的退出码要求。

**改动**：新增阶段属性 `failure_reason`、全部页面访问失败识别；管线统一把已经捕获的动态记录加入候选；在日志中明确写入 `run_status:completed | partial_browser_failure | incomplete_budget | failed`。浏览器失败但有至少一条经 EvidenceAuditor 审查的 API，返回 0 并标记部分完成；浏览器失败且无可交付条目或严重管线错误，则返回 1。预算中断输出当前合法结构并返回 0，日志标记不完整。

**为什么更可靠**：消除了“完全不知道浏览器失败”的静默状态，同时不丢失静态提取成果及中断前完成的动态请求证据，并符合 R2/R3 的实际交付口径。**退出码 0 只是合法交付，不再被用作‘全部阶段成功’的唯一依据**。

**验证**：新增 `tests/test_run_outcomes.py` 的 7 项离线回归，包含模拟启动失败、全导航失败、预算中断、静态/动态证据保留、成功和失败状态；隔离环境累计 35 项 `pytest` 测试通过，`compileall` 通过。**未做真实浏览器/真实站点测试**。

**后续风险**：动态监控尚不能保证复杂登录、WS 长连接与进程外超时的每一种情况；必须在真实 Docker/代理与授权练习站点验证 R2/R3/R4。

## 12. V9：敏感日志与证据链跨轮污染（2026-11-22）

- **根因 1**：`redact_url` 过去只处理 Query，URL 用户名/密码会作为 userinfo 原样保留，`key`、`jwt`、`csrf` 等短键可能漏脱敏。
- **修复 1**：`jsonl_logger.py` 删除 URL userinfo，扩大并规范敏感键匹配；解析失败时采取保守占位符，避免错误时反泄漏。测试验证原 URL 的密钥片段不写入 JSONL，IPv6 与业务参数正常保留。
- **根因 2**：`tool.log` 是 append-only，过去 `EvidenceAuditor` 会读取前几轮的记录；仅用 `method/host/path` 判定有效，存在陈旧日志给新 HAR 背书的可能。
- **修复 2**：`JsonlLogger.start_offset` 记录本次运行前日志字节长度；`pipeline.py` 将偏移传入 `audit_endpoints`；审计索引加入 `request_index`、HTTP 状态，并与 HAR 核对；拒绝无效状态，允许 401/403 用于鉴权证据。**静态源码证据不需要强行关联动态请求。**
- **根因 3**：管线异常原始字符串有机会包含配置/请求地址等敏感值。
- **修复 3**：`pipeline.py` 的 `pipeline_error` 和 `output_validation_error` 仅记录异常类型。

**验证**：隔离环境中的针对性测试 30 项通过（包含原有基础测试、更新后的证据测试与 12 项新增测试），Python 源码语法检查通过。此测试只覆盖本轮涉及的模块，并非完整当前 GitHub 分支的全量测试。Docker 与真实浏览器未运行。

**经验**：当日志采用追加模式时，**证据必须带有“属于本轮运行”的边界**；请求的路径相同不足以说明来自同一次观察。隐私保护应“默认不回显未处理的敏感原文”，且不得随意清空用户历史日志。

**留存风险**：历史日志不会被自动擦除；原始网页及 JS 源码、第三方底层错误流仍可能包含敏感内容。完善安全边界需额外审计，不能将 V9 视为终极隐私保证。


## 13. V10：结构治理与编排层减负

**发现的问题**：仓库根目录的旧 ZIP、Dockerfile 备份与当前源码混放；`pipeline.py` 重复包含表单和动态请求的候选格式转换；文档缺少导航；直接整体迁移源码到 `src/` 容易破坏 Docker CLI。

**修复依据**：保留旧文件的 Git Blob SHA，只改变路径到 `archive/legacy/`；新增 `candidates.py` 实现无网络、无文件操作的 `from_html_forms()` 与 `from_network_records()`，保持输入的状态、索引、请求字段，由 `normalization.py` 与 `evidence.py` 继续判定有效性。增加 8 项独立测试，实际运行通过。

**经验**：小型高质量项目优先单向数据流与可独立测试的纯函数，不为目录外观复制两套源码；不要擅自丢弃用户历史资产。**未验证项**：最新全仓库测试、真实 Docker、严格 `src/` 目录结构和隐藏站点评分。


## 14. V11：修复域名注册边界与 WebSocket 门控（2026-11-22）

- **根因（R5）**：手动维护的注册域后缀表会遗漏 `co.za` 等后缀，错误允许与目标无关的兄弟域名；`allowed_hosts` 不是可覆盖同域边界的豁免。
- **修复**：`scope.py` 借助操作系统 libpsl 内置 PSL 计算可注册域，支持 ccTLD/私有后缀；在库缺失时保守限制为目标主机及其后代，不依据二级域名自行猜测；额外拒绝携带 URL userinfo 的请求，支持 IDNA 规范化。
- **根因（R4）**：之前 WebSocket connect 过程绕过了 HTTP 共享并发与限速门控，实际连接数量不可约束。
- **修复**：WebSocket Route 引入 `_limiter.before(id(route))`，开放连接占用共享槽位，客户端或上游关闭与异常时调用幂等 `after` 释放；借助 RequestGate 限制连接建立的发起频率。
- **验证**：19 项专项离线测试通过，覆盖 `co.za` 越界、`github.io` 私有后缀、IP、IDNA、无 PSL 退化、WS 长连接槽位、并发等待、异常释放、模拟 20 RPS 限速；Python 编译检查通过。
- **剩余风险**：尚未在官方 Docker 内确认 libpsl 系统库加载及 Chromium 的真实 WS 流量。缺失 libpsl 时虽然可避免未知兄弟域越界，但会降低多子域站点覆盖率。R6 静态接口无真实请求证据的问题仍未解决。

**经验**：安全边界不能依赖不完整的域名后缀经验表；复杂协议不应绕开全局限速器；即使局部修复有测试依据，仍应将代理、真实浏览器与隐藏评测明确列为未验收。


## 15. V12：源码声明与真实请求不能混为一谈（2026-11-22）

- **根因**：曾经的 `EvidenceAuditor` 能证明某 JS/HTML 文件存在且片段匹配，却不能证明对应 API 真正触发请求；这种静态候选直接进入正式结果，与考核 3.6 的逐项日志和重放核查存在冲突。
- **修复**：在已有证据审计之后，新增 `split_by_request_proof()`。只有与本轮 `tool.log` 和 HAR 校验一致的请求才进入 `result.json`；静态专有候选被保存在 `static_candidates.json`，不写虚构状态，也不主动向未知接口发请求。
- **安全细节**：sidecar 只保存端点 Method、Host、标准化 Path 和静态证据的文件/位置，省略 Header、Body、源码片段；重复执行时使用原子替换，避免旧数据污染。
- **合同取舍**：R2 规定合法 JSON + 0 退出码；浏览器仅部分失败但依然生成了合法空结果时，输出 `run_status:partial_browser_failure` 而不是谎称完整成功。真实管线错误仍返回非零。
- **验证**：离线组合工作副本中 50 项相关测试通过，含新增 12 项（8 纯函数 + 4 假浏览器主流程）；未进行 GitHub 最新完整 checkout 的全量测试、Docker、Chromium 或真实站点重放。
- **最重要的遗留问题**：这是**质量分级而非真实接口验证器**，正式结果的 Recall 可能下降，且 HAR 和日志一致不能保证接口能重复调用成功。R6 只能评价为“证据引用约束增强”，不能写成“正式 PASS”。

**经验**：静态分析扩大候选集合，不能提升观测证据的等级；应将“发现可能存在”与“已发生请求”分别展示、分别统计。不能为了提高表面命中率让工具自动执行不确定的状态变更接口。


## 16. V13：静态接口补证不能靠猜测（2026-11-22）

**已知问题**：V12 将静态专有候选排除在正式接口清单之外，符合“有真实请求证据才提交”的原则，却降低潜在 Recall。如果主动对未知路径发送 GET，虽然方法名是 GET，也不代表服务端一定无副作用。

**处理**：新增独立 `verification.py`，只在用户明确批准的本地测试配置（`explicit_readonly_get_urls`，最多 5 个精确 URL）中启用。源 URL 必须是静态分析发现的 GET，经过 ScopeGuard 和共享 RequestGate，禁止重定向、认证凭据、Query/fragment 和动态路径参数；只有真实 2xx JSON 响应才写入脱敏 `probe.har` 并在 `tool.log` 记录本次真实请求，再由 EvidenceAuditor 核对。不成功的请求不能作为有效接口证据，静态线索原样保留待验证。

**验证**：在隔离 Python 3.13.5 工作副本运行 87 项离线测试通过，含 23 项新增 MockTransport/模拟主流程用例，Python 编译检查通过；未运行联网、Docker、真实站点和官方重放。

**取舍**：这是本地授权调试辅助，而不是正式评测允许的站点适配策略；官方标准配置不包含该字段时，额外验证请求数为 0。真实 GET 即使返回 200 JSON，也不能证明业务完全无副作用或跨会话重放成功。

**维护经验**：提交后必须核对新 Git commit 继承的文件树。本轮 V13 代码提交基树没有包含此前 V12 文档提交，因此同步恢复 V12 原文并追加 V13，避免版本更迭记录在最新分支中倒退。


## 17. V14：不要再用测试数量代替质量指标（2026-11-22）

**问题**：之前的测试主要核对函数/文件是否符合预期，不能显示 T1/T2/T3 Recall、Precision、重复错误、证据有效率与两次独立运行的变化；V12 的“证据严格但 Recall 可能下降”一直缺少量化。

**实现**：新增独立纯离线评分器，使用合成的显式 ground truth、Schema 合法的结果、当轮 HAR/JSONL，测量 TP/FP/FN、加权 Recall(40)、Precision(20)、不同档位覆盖率、证据一致率和两轮 Jaccard；按考核规则的 0.7/0.3 修正客观局部得分。数据格式、脚本、对照用例详见 [OFFLINE_BENCHMARK.md](OFFLINE_BENCHMARK.md)。

**执行依据**：隔离 V14 工作副本 Python 3.13.5，完整 pytest **119 项通过**（其中新增评分/流水线相关测试 32 项），Python 源码编译检查通过。完整项目使用的是旧 V13 本地基底加上精确的 V14 新文件，**不应将该结果说成当前 GitHub commit 的全量测试或官方正式验收**。新文件 Git Blob SHA 与本地测试文件逐一核对。

**重要现象**：单条合成 T1 页面中，只做静态发现但不触发真实请求，正式输出无条目，对这一条真值的局部得分为 0/60；使用用户明确批准的 MockTransport GET 后，两轮输出均可本地获得 60/60 和一条证据一致的 TP。这说明 V12 的证据约束会改变 Recall，但不能预测真实站点成绩。

**经验**：离线评估只可以证明自己的真值、算法和文件的一致性；无网络抓包不等于“真实请求发生”，无官方人工语义评审不能编造满分。零输出的 Precision 必须标为 `null`，不能虚构 100%。


## 18. V15：单个开发副本的测试通过不等于交付版本可验收

**问题**：以往多次分别运行隔离工作副本，报告 28、35、50、87、119 项通过，但未在最新 GitHub 同一个提交上自动构建正式 Docker 镜像并启动真实 Chromium。缺乏稳定的版本绑定和双轮端到端质量门禁。

**方案**：在 GitHub 同一提交上配置两阶段 CI。先安装 pinned Python/npm 依赖并运行全部 pytest；然后（若第一阶段成功）按硬性时间/体积限制构建真实 Docker 镜像，使用离线合成 HTTP 网站执行两轮真实 Playwright 流程，独立核验 API 请求日志与 HAR、结果非空、Schema 合法和集合一致性。CI 只用自建虚拟站点，网络设置为 internal-only。

**当前实际验证**：本地创建的 Python fixture 真实提供 200 HTML/JS/JSON，fixture 单测 1 项通过；CI YAML 解析、Shell/Python 语法检查通过。Docker 与完整仓库 pytest 需要 GitHub Actions 运行后才算实测，不得提前写成 PASS。

**遗留限制**：仅验证合成站点，不能证明复杂 S1～S5、认证/签名、真实重放及隐藏评分；只读 rootfs 不等于对所有运行期读写做过系统审计。内部资料旧 Git 对象仍需由仓库所有者执行专门的历史清理。


### V15 实际验证补充

首次 GitHub Actions Run #1（提交 `466dde4`）完成：当前精确 GitHub checkout 中的 137 项测试全部通过，Docker 镜像构建 28 秒，大小 2,864,215,392 字节；自造 internal HTTP 站点的真实 Chromium 双轮各发现 1 条 API、结果集合一致。证明 CI 链路可在干净 GitHub Runner 上执行。之后新增独立 Schema 校验和 HAR/log 请求关联更严格的检查，尚需在新提交中复跑。不能由单个合成 API 推断全部复杂协议、真实权限边界或正式重放率。
