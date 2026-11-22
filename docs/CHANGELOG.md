# API Extractor 版本更迭记录（CHANGELOG）

> 安全说明：为降低历史资料再次暴露的风险，早期提交的公开直达链接及标识已撤销。GitHub 上的旧对象和缓存**尚需独立历史清理**，此处不代表清理完成。历史重写后可在仓库提交历史中查阅新标识。

> 项目：[David-tiao/API](https://github.com/David-tiao/API) · 选题 B：前端 API 提取工具  
> 记录日期：2026-11-22（Asia/Singapore）  
> **说明**：以下“V0～V16”是便于理解的**开发迭代阶段编号**，不是正式 Git Tag 或发布版本号。当前 `pyproject.toml` 中的软件版本仍为 `0.1.0`，不要把阶段编号当作发行版本。

## 验收快照：V10（2026-11-22，非功能版本）

针对代码基线 `旧提交标识已隐去`，新增 [V10 验收报告](ACCEPTANCE_V10_2026-11-22.md)。结果：V10 候选纯函数的 8 项当前 GitHub SHA 一致的测试通过；但 R5 注册域解析存在可复现越界风险，静态推断的 API 无法自然满足逐条请求日志与重放证明。完整 GitHub 当前全仓库测试、Docker 和隐藏站点未验证。**本次只更新文档，不修改业务代码；不视为 V11 版本发布。**

## 安全维护：内部资料不纳入公开仓库（2026-11-22）

已清理公开工作树中不应跟踪的内部材料，并更新 Git/Docker 排除规则。此提交没有改变扫描器源码、CLI、Schema 或验收结果。**注意：正常删除提交不清除历史 Git 对象或外部缓存；历史彻底清理需要单独进行，并应优先调整仓库可见性。**

## V15 实测结论更新：完整 Schema 与 HAR/日志一致性检查通过

加固版提交 `7244ee3` 的 [GitHub Actions 第二轮](https://github.com/David-tiao/API/actions/runs/45011978873) **completed/success**：精确 checkout **137 项 pytest 通过**；Docker **32 秒**，镜像 **2,864,047,070 字节**；隔离站点的 Chromium 双轮各识别 **1 条**合成 API，**两次独立 JSON Schema 校验、逐请求 HAR/JSONL 方法/URL/状态/索引检查都通过**。本轮通过的是合成站点交付链路，不是 S1～S5 隐藏站点综合考核；公开仓库旧历史资料仍待所有者清理。

## V15 验证增量：GitHub Actions 首轮成功与证据核对加固

代码基线 `466dde4019d20da5a6deff52f4dc227b11f68ec7` 首轮 GitHub Actions [运行记录](https://github.com/David-tiao/API/actions/runs/45011683183) 已完成，两个 Job 均成功：**全仓库 pytest 137 项通过**；Docker 原构建 **28 秒**、镜像大小 **2,864,215,392 字节**；internal Docker 网络中的真实 Chromium 两轮分别发现 **1 条**合成 GET API，集合一致。最新增量加强独立 JSON Schema/HAR/日志对齐及所有 main 提交的 CI 触发，等新流水线结束再认定最新版通过。

这只是自建模拟站点基础验收，非 S1～S5 官方隐藏站点、真实网络越界审计或历史保密清理的最终验收。详见 [V15 验收记录](ACCEPTANCE_V15_2026-11-22.md)。

## V16 · SSR 表单与跨域重定向的真实负向验收（2026-11-22）

**改动**：扩展 `tests/fixtures/docker_smoke_site.py`、`tests/test_docker_smoke_fixture.py`、`scripts/ci_docker_smoke.sh`；新增 `tests/test_crawler_redirect_scope.py`。本轮**不修改生产扫描器、Dockerfile、CLI 或结果 Schema**。

**动机**：V15 已在 GitHub 精确提交中通过 137 项离线测试、真实 Docker 构建和两轮 SPA 合成站点验收，但只能证明允许的 GET 正常工作，不能证明未授权跨域请求真的被阻断，也不能证明 HTML 表单不被擅自提交。

**新增**：同一个 internal-only Docker 网络部署已授权的 `fixture` 和未授权的 `offscope` 两个合成服务端。浏览器分别访问 SPA `/`、SSR `/ssr`；后者包含一个未知 `POST /api/submit` 表单、一个已观察的 `GET /api/ssr-items`、一张跨域图片与一个指向异域的 302 重定向。每种场景**独立运行两次**；要求正式结果只输出观察到的 GET、未提交 POST、静态表单只保存在待验证旁路文件。跨域是否成功被阻止由 **offscope 实际接收端访问日志**判断，而不是仅听信扫描器的阻断说明。

**证据质量**：四次运行都由独立容器验证正式 JSON Schema；对每条 HAR 核对本轮 JSONL 的请求方法、URL、HTTP 状态与索引，并比较同场景双轮集合。另补四项 HTTPX MockTransport 重定向安全测试。

**真实执行界限**：本地新 SSR/SPA/302 夹具 **3 项测试通过**，Bash 和 Python 语法检查通过；完整仓库 pytest、四轮 Docker、异域接收端日志检查以本提交 GitHub Actions 真实结果为准，**未经执行不得宣称通过**。R5 真实代理/DNS、S1～S5 隐藏站点和公开 Git 历史保密仍不属于此模拟验收。

详见 [V16 验收](ACCEPTANCE_V16_2026-11-22.md)。

## 最新迭代：V15 · 同一提交的自动回归与隔离 Docker 双轮验收（2026-11-22）

**新增**：`.github/workflows/quality-gate.yml`、`scripts/ci_docker_smoke.sh`、`tests/fixtures/docker_smoke_site.py`、`tests/test_docker_smoke_fixture.py`；文档详见 [V15 验收说明](ACCEPTANCE_V15_2026-11-22.md)。

**根因**：此前 V14 的 119 项测试在隔离组合工作副本执行，虽然新文件 SHA 核对过，但仍不能证明 GitHub 当前完整工作树、Playwright Docker 镜像、R2 输出契约和双轮稳定性同步通过。新结构将验证**绑定到同一个 Git commit**，区分 Python/Node 单元测试和真正的浏览器容器端到端运行。

**实施**：

- 在 GitHub Actions 的全仓库检出中安装固定版本 Python/Node 依赖，运行 `pytest`、Python 编译检查、Node 语法、Shell 语法，并核查内部资料保护忽略规则。
- 仅在离线测试成功后，尝试 900 秒内 `docker build`、镜像大小 ≤6 GiB；使用 **Docker internal-only network** 隔离测试中的 Python 模拟网站。两次独立执行与正式 CLI 相同的参数，分别检查 JSON、真实 API 日志、HAR、非空接口结果及端点集合稳定性。
- 测试容器使用只读根文件系统，只有 `/out` 可写；CI 不访问真实站点、不读取组织方靶场凭据、不操作其他容器。
- 本轮仅新增质量基础设施，**不修改扫描器运行行为、Dockerfile、输出 Schema 或 S1～S5 算法**。

**已经执行的检查**：在当前隔离环境中，新的合成 HTTP 夹具真实启动并成功提供 HTML/JS/JSON；独立 Python HTTP 夹具测试 **1 项通过**；Bash/ Python 编译与 GitHub Actions YAML 结构检查通过。**当前环境没有 Docker，也没有从 GitHub 下载完整源码的网络能力；本文件刚提交时 GitHub Actions 全量测试与真实 Docker 结果尚待运行，不能标为 PASS。**

**保密提醒**：仓库当前仍是公开的，历史提交里的内部资料尚未在 GitHub 完成重写和缓存清理。CI 不含内部资料内容，不能替代私有化与历史清理。后续须先完成保密处理，再进入真正的正式场站验收。

## 最新迭代：V14 · 离线量化评分基准与双轮稳定性（2026-11-22）

**新增文件**：`api_extractor/offline_benchmark.py`、`tests/test_offline_benchmark.py`、`tests/test_benchmark_pipeline.py`、`tests/fixtures/benchmark/ground_truth.synthetic.json`、`tests/fixtures/benchmark/README.md`、`docs/OFFLINE_BENCHMARK.md`、`docs/ACCEPTANCE_V14_2026-11-22.md`。

**动机**：V12/V13 已能区分静态猜测和已观察请求，但只有 pytest 数量无法说明总体准确度、漏报率及两轮输出稳定性。依照考核细则第 3.2、3.5、3.5.1、3.6 节，新增一个**只读、完全离线**的开发评分器，读取人工为自建站点确认的 ground truth 和两次独立运行的 `result.json`、`tool.log`、HAR。

**实现**：按 METHOD + 归一化路径匹配；T1/T2/T3 权重为 1.0/1.4/1.8；Recall 部分为 40 分，Precision 为 20 分（FP > TP 时精确率项清零）；独立输出目录的两轮局部分数采用 `0.7 × mean + 0.3 × min` 修正。额外检查预测重复项、第三方域、HAR/JSONL 是否按方法、Host、Path、索引、状态对应；输出端点集合 Jaccard、剔除运行时间和证据索引的语义指纹，支持自设门槛并原子写入报告。五站权重为 1/1/1.2/1.3/1.5，四站必须仅使用 S2～S5；支持局部客观分聚合。

**为何不报告官方 100 分**：语义 20 分、正式证据链 10 分、工程质量 10 分不在这个本地工具的自动评分范围内；`official_100_point_score` 固定为 `null`。真值外确实存在的 API 官方可人工纠正为 TP，而离线工具保守计 FP；重复接口保守按额外 FP 计。本地 HAR/日志一致并不意味着通过实际网络重放。

**离线验证**：在 Python 3.13.5 的独立 V14 开发工作副本运行 `python -m pytest -q -o addopts='' --disable-warnings`，**119 项测试通过**；新评分器及管线专项 **32 项通过**；`python -m compileall -q api_extractor tests` 通过。合成单条 T1 夹具中，静态-only 正式清单 0/60，显式批准的 MockTransport GET 产生有效 HAR/日志后，两次模拟运行都为 60/60、Jaccard=1、证据一致率 100%。**这些是开发测试，不是当前 GitHub 完整 checkout、真实 Docker、真实网络或隐藏评测 PASS。**

**兼容性**：没有修改扫描器主流程、CLI、Dockerfile、评测 `result.json` Schema 或运行期访问边界；评分器通过独立的 `python -m api_extractor.offline_benchmark` 命令调用，不参与生产扫描。使用与方法和局限详见 [离线基准说明](OFFLINE_BENCHMARK.md) 与 [V14 验收](ACCEPTANCE_V14_2026-11-22.md)。

## 最新迭代：V13 · 本地显式授权 GET 验证（2026-11-22）

**代码提交**：[旧提交链接已撤销]  
**文件**：新增 `api_extractor/verification.py`、`tests/test_safe_get_verification.py`、`tests/test_get_verifier_pipeline.py`；修改 `config.py`、`pipeline.py`、`normalization.py`、`evidence.py`。

**问题**：V12 仅将浏览器确实触发的接口输出到 `result.json`，静态 JS/HTML 声明不具备真实请求证据，默认保存在 `static_candidates.json`。这样避免了虚假请求证据，但可能损失 T1 Recall。

**改进**：新增 `ExplicitGetVerifier`，供开发者在**自己部署或明确授权的本地练习环境**中，通过可选配置 `explicit_readonly_get_urls` 精确批准最多 5 个 GET URL。目标必须同时出现在当前静态候选中且通过 ScopeGuard；拒绝 Query/fragment、userinfo、路径占位符、歧义点段、非 HTTP(S) 与越界域名。GET 顺序执行，使用已有 RequestGate 和任务预算，不跟随重定向、不转发账号、Cookie 或额外配置 Header。2xx 且响应 Content-Type 为 JSON 才生成 `evidence/probe.har`，并由本轮 `tool.log` 中的真实 `phase=probe` 请求记录核查方法、Host、Path、状态和索引；审核通过才进入正式结果。其它静态候选仍属于待验证线索。

**验证**：隔离 Python 3.13.5 工作副本的 `pytest -v --disable-warnings` 有 **87 项通过**，其中新增 23 项定向/参数化测试，真实 GET 全用 HTTPX `MockTransport` 代替；`compileall` 通过。这不是 GitHub 当前完整 checkout、真实浏览器、Docker 或赛题评测的通过记录。

**安全与考核限制**：GET 并不天然保证服务器不修改数据，必须由操作者逐 URL 确认安全与授权。**官方 3.6 的允许适配字段不包括每站手动枚举接口路径**，因此这只是本地调试能力，默认字段缺失时不发送任何额外 GET，不能用于隐藏评测的站点特化，也无法保证实际 R6 重放率。CLI、结果 Schema、Dockerfile 均未改变。

**补充维护**：提交 V13 代码时发现所用基树未包含 V12 后续文档提交，本次文档更新同时从原提交 `旧提交标识已隐去` 恢复 V12 文档，保留历史正文与文件链接，再追加 V13。本修正只处理文档一致性，不重写 Git 历史。

## 最新迭代：V12 · R6 请求证据强度分级（2026-11-22）

**代码提交**：[旧提交链接已撤销]  
**代码文件**：`api_extractor/evidence.py`、`api_extractor/output.py`、`api_extractor/pipeline.py`；新增 `tests/test_evidence_policy.py`、`tests/test_r6_pipeline.py`；调整 `tests/test_run_outcomes.py` 与 `tests/test_integration_local_http.py`。

### 要解决的具体问题

V11 之前，只有 JS/HTML 源码位置的静态候选，经过文件存在性检查就可能进入正式 `result.json`。但《考核细则》第 3.6 节强调：正式输出的接口在 `tool.log` 中必须有可查验的真实请求证据，并抽查重放。**源码声明了 `fetch('/api/items')` 不等于程序实际上请求过后端。** 对这些候选写入虚构状态码无法满足考核，也可能违反规范。

### 本次实现与数据流

1. 仍完整执行静态分析及动态浏览器分析，先按照既有 `normalization.py` 去重，再由 `EvidenceAuditor` 验证源码文件及动态 HAR（方法、Host、Path、索引、响应状态及本轮请求日志）。
2. **在审计后新增 `split_by_request_proof()` 分级**：拥有已经审计通过的 `har` 请求证据的端点进入正式 `result.json`；只有 `bundle/html` 证据的端点不再进入正式结果。
3. **保留静态线索**：另写入 `/out/static_candidates.json`（本地模式为输出目录），明确标记 `kind=unverified_static_candidates`、`reason=no_observed_request`。只存 Method/Host/Path 和来源文件定位，不复制源码片段、请求 Header 或 Body。
4. `tool.log` 增加 `request_proof_gate:confirmed=N,static_only=M` 汇总，但**不为静态候选伪造 HTTP 请求记录**。
5. R2 保持固定 CLI、Schema 和正常返回 0 的要求；即使浏览器失败、没有已观察接口，仍可输出合法空清单，并在 `tool.log` 中记录 `run_status:partial_browser_failure`。真正的采集异常仍沿用非零退出码。
6. 诊断 sidecar 原子覆盖，重复运行不会沿用上一轮静态候选。

### 实测与适用范围

在隔离 Python 工作副本中，新增的 8 项纯证据分级测试、4 项离线主流程集成测试，以及现有证据审计、规范化、候选映射、作用域、输出等 **50 项相关测试通过**；执行了 `python -m compileall -q api_extractor tests`。测试通过仅证明这些离线用例，**没有复现当前 GitHub 完整 checkout 全套 pytest，没有启动真实 Docker/Chromium，也没有通过组织方重放抽查**。

### 代价与剩余问题（必须阅读）

- **Precision / R6 改善，Recall 可能下降**：T1 静态可见但未实际触发的接口现在只在 `static_candidates.json`，不会计入正式结果。选题 B 的 Recall 权重为 40，不能将这项变化简单视为总分必然提高。
- **R6 尚未验收完成**：HAR/日志一致不等于重放成功；运行时观察的接口可能依赖会话、签名或不可重放的业务状态。
- **没有主动探测**：本轮不会盲目调用未知 POST/PUT/PATCH/DELETE，也没有为 GET 接口增加自动请求。后续如果要提高静态候选转正率，应只针对明确授权、确定安全的请求设计额外验证与预算限流。
- 正式 Docker 镜像、R4/R5 代理审计、S1～S5 隐藏站点尚未实测，软件版本仍为 `0.1.0`。

进一步的风险分析见 [V12 验收快照](ACCEPTANCE_V12_2026-11-22.md)。

## 最新迭代：V11 · R5 可注册域边界与 R4 WebSocket 全局限流（2026-11-22）

**代码提交**：[旧提交链接已撤销]  
**修改文件**：`api_extractor/scope.py`、`api_extractor/dynamic_analysis.py`、新增 `tests/test_scope_psl.py` 与 `tests/test_ws_gate.py`。  
**定位**：修复 V10 验收的两个硬性安全阻断项；不修改 CLI、Schema、运行时外部调用、历史文件。

### 问题与理由

1. **R5：旧版手工 Public Suffix 列表不完整**。例如将 `app.example.co.za` 错误地简化成 `co.za`，允许非授权 `unrelated.co.za`，属于潜在越界。
2. **修复：使用系统 libpsl 内置的 Public Suffix List** 计算注册域，覆盖多标签公共后缀以及 `github.io` 等私有后缀。若库缺失或无法确认，`registrable_domain` 保守返回完整主机名，禁止推断兄弟子域。统一 IDNA 规范化，禁止 URL 自带 username/password。
3. **R4：WS 握手原本绕过共享 RequestGate**。以前的 `connect_to_server()` 直接执行，没有并发/RPS 约束。
4. **修复：增加 `DynamicAnalyzer._route_websocket()`**，使用相同的 `BrowserRequestLimiter` 和 `RequestGate` 控制建立连接；连接关闭、上游关闭或异常时释放槽位；开放连接持续占用槽位，不把“握手完成”错误地等同于“请求完成”。当前 Playwright 的 `connect_to_server()` 为同步调用，不添加错误的 `await`。

### 本轮验证

在隔离环境使用修改后的 `scope.py`、作用域原测试、模拟 WebSocket 组件运行：

```bash
python -m pytest -q tests/test_scope.py tests/test_scope_psl.py tests/test_ws_gate.py
python -m compileall -q api_extractor tests
```

**19 项定向测试通过**（5 项原作用域 + 8 项新增 Public Suffix/IDNA/凭据/后备规则 + 6 项 WS 并发/限速/生命周期模拟）。其中 `scope.py` 与本次 GitHub 代码文件的 Git Blob SHA 一致；WS 使用假的 Route 测试真实门控逻辑，不是 Chromium 网络实测。宿主机检测到 libpsl，亦测试了强制缺失时的 fail-closed 路径。

**未验证**：官方 Docker 镜像 libpsl 是否可加载、真实 Chromium/WebSocket 代理侧流量是否持续符合 ≤8 并发/≤20 RPS、隐藏站点 S1～S5 的召回率与重放率。请不要将这些局部用例与历史测试计数相加，宣称“全仓库通过”。

### R6 证据链仍未关闭

本次**没有**自动调用静态源码里的任意接口，也没有伪造 `tool.log` 请求状态。源码出现 `fetch('/api/...')` 并不保证真的触发网络请求，尤其未知 POST/DELETE 可能有业务副作用。V10 验收指出的“静态条目缺少对应真实请求/可重放证据”仍是独立的待修复项，详见 [V11 验收状态](ACCEPTANCE_V11_2026-11-22.md)。后续需设计明确授权、证据分级与安全执行策略。

## 最新迭代：V10 · 文件结构治理与候选映射分层（2026-11-22）

**变化文件**：`api_extractor/pipeline.py`、新增 `api_extractor/candidates.py`、`tests/test_candidates.py`；新增文档导航、项目目录规范、ADR 与脚本/测试索引；历史 ZIP 和 Dockerfile 备份移至 `archive/legacy/`。

**修复的设计问题**：根目录混放有效源码、旧版打包及 Dockerfile 备份；主流水线承担了过多直接字典映射；缺少正式模块边界、目录维护约定与文档导航。

**采取的架构**：`pipeline` 管理预算和阶段，`candidates` 只把 HTML 表单与浏览器网络观察转换成候选，`normalization` 归一化，`evidence` 审计，`output` 负责最终 JSON Schema。保留 `api_extractor` 包路径和所有运行入口。旧归档移动时保留原来的 Git Blob SHA，避免历史资料丢失。

**验证**：本次新纯函数及 `tests/test_candidates.py` 的 **8 项离线测试通过**，Python `compileall` 通过。原有完整 GitHub 分支测试、Docker/Chromium 和授权站点端到端均未重新执行，不宣称全部满足考核。原根目录归档路径变更是本轮唯一的历史文件路径兼容调整。

**遗留约束**：考核清单推荐 `src/`，目前项目仍使用根目录 `api_extractor/`；未验证 Docker 之前不进行破坏性移包。见 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 和 [ADR-0001](adr/0001-compatibility-first.md)。

## 最新迭代：V9 · 日志脱敏与本轮证据关联（2026-11-22）

**代码提交**：[旧提交链接已撤销]  
**类型**：安全性、精确率与证据链可靠性；无 CLI、JSON Schema 或 Dockerfile 变动。  
**修改文件**：`api_extractor/jsonl_logger.py`、`api_extractor/evidence.py`、`api_extractor/pipeline.py`、`tests/test_evidence_audit.py`、`tests/test_logger_redaction.py`、`tests/test_evidence_linking.py`。

### 问题与修复理由

1. **URL 凭据泄露风险**：旧版 `redact_url()` 只遍历 Query，不会删除 `https://user:password@host/` 里的用户名和密码；`key`、`jwt`、`csrf` 等查询字段也不一定脱敏。V9 明确删除 URL userinfo，识别这些敏感键，并在畸形 URL 时返回占位符而不是原始 URL。对 `design` / `barcode` 等普通字段不做粗暴子串脱敏，以免丢失业务信息。
2. **跨轮旧日志误背书**：`tool.log` 采取 append 模式；旧版证据审计遍历全部历史请求，只匹配方法、主机、路径。这可能把前一轮的日志当成本轮 HAR 的有效请求。V9 在 JsonlLogger 初始化时记录当轮起始**字节偏移**，审计仅读取该偏移之后的记录。
3. **HAR/日志绑定不充分**：V9 进一步要求 HAR 的 `request_index`、`response.status` 和日志内的索引、状态码一致。失败状态码不能当作正常 API 存在性的证据；`401/403` 仍可用作认证要求线索。
4. **异常文本包含秘密的风险**：管线诊断日志只报告异常类型，不把未经处理的异常消息原文写入 `tool.log`。需要更细致诊断时应在受控环境下另行排查。

### 验证与兼容性

在本地隔离副本中，以仓库最初源码为基础，加入**此次修订的日志/证据模块**与相应测试夹具，执行了以下命令，**30 项测试通过**，并通过 `compileall`。这里的 30 项是本次**针对性回归集**，不是 GitHub 当前全仓库的 47 项或其他总数保证：

```bash
python -m pytest -q \
  tests/test_evidence_audit.py tests/test_evidence_linking.py \
  tests/test_logger_redaction.py tests/test_scope.py \
  tests/test_normalization.py tests/test_output.py
python -m compileall -q api_extractor
```

**兼容性**：结果 JSON 字段不变；`tool.log` 保留原始字段，仅对 URL 的敏感内容作更严格遮蔽；证据审计拒绝旧日志提供的虚假支持。已有静态源码证据不依赖动态日志，仍可保留。

**仍未验证**：没有实际构建 Docker、启动 Chromium 或使用真实站点；也没有在本地完整复现 GitHub 当前主分支的所有源码及运行全部测试。旧日志仍保留在用户的输出目录，V9 的保护是**不再采纳旧日志进行证据背书**，并不会自动清除此前生成的敏感日志；需要用户自行在安全环境中处理历史日志。

**余留问题**：可能仍有第三方库输出的异常正文、原始下载的网页/JS 文件、其他未知类型的敏感 URL 参数；此轮不承诺全系统隐私审计完成。

## 最新迭代：V8 · 运行状态与部分结果可靠性（2026-11-22）

**代码提交**：[旧提交链接已撤销]  
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
| V0 | [旧提交链接已撤销] | 初始化 API Extractor 工程 | 初始架构 | 仅有代码，未据此认定验收 |
| V1 | [旧提交链接已撤销] | 修正 WS 路由调用与请求稳定等待 | 兼容性与稳定性 | 真实浏览器仍需验证 |
| V2 | [旧提交链接已撤销] | CLI 异常、域名安全、证据和镜像契约 | P0/P1 修复 | 具备新增回归测试 |
| V3 | [旧提交链接已撤销] | Body 签名判断与双轮验收工具 | 功能、测试 | Docker 双轮脚本未在真实环境执行 |
| V4 | [旧提交链接已撤销] | 限制浏览器临时目录写入范围 | 文件系统边界 | 需文件系统审计 |
| V5 | [旧提交链接已撤销] | S5 WebSocket/SSE 静态入口补全 | 协议识别 | 仅覆盖可静态定位的入口 |
| V6 | [旧提交链接已撤销] | 引入 EvidenceAuditor 独立证据审计 | 架构演进 | 验证引用一致性，不是端点可重放 |
| V7 | [旧提交链接已撤销] | 正式记录架构、算法及迭代依据 | 工程文档 | 文字对照源码，不是运行测试 |
| V8 | [旧提交链接已撤销] | 失败状态显式报告、预算取消保留部分 API | 可靠性与 R2 适配 | 35 项离线测试；真实 Docker 待验收 |
| V9 | [旧提交链接已撤销] | URL 凭据脱敏、跨轮日志隔离、HAR 索引和状态匹配 | 安全与证据质量 | 本次 30 项针对性离线测试；未全仓库实测 |
| V10 | 本次提交（见 Git 文件历史） | 归档旧版文件、抽离候选纯函数、文档规范化 | 架构整理 | 8 项定向离线测试；未完整回归 |
| V11 | [旧提交链接已撤销] | PSL 域名边界与 WS 共享限流器 | R5/R4 安全修复 | 19 项定向测试；正式 Docker 未验收 |
| V12 | [旧提交链接已撤销] | request-backed 正式结果与静态待验证 sidecar | R6 证据分级 | 50 项相关离线测试，未做真实重放 |
| V13 | [旧提交链接已撤销] | 本地显式 GET 授权与真实 HAR/日志核查 | 开发辅助/证据质量 | 87 项隔离离线测试；正式评测未验证 |
| V14 | 本次 Git 提交（见文件历史） | 合成真值、Recall/Precision、证据交叉核查与双轮稳定性 | 离线质量基准 | 开发副本 119 项通过，新增专项 32 项；Docker 未验收 |
| V15 | 本次 Git 提交（见 main 历史） | 全仓库 CI、Docker 合成站点双轮运行与证据核验 | 交付质量门禁 | 本地夹具测试 1 项；GitHub Actions 初次执行待核对 |
| V16 | 本次 main 提交 | SSR+SPA 四轮合成 Docker 安全验收、异域接收方日志 | R5/S2/R6 | 本地 3 项新夹具测试通过；CI 待运行 |

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


## V16 安全修补记录：浏览器 302 实际越界（2026-11-22）

V16 首次 GitHub Actions [运行记录](https://github.com/David-tiao/API/actions/runs/45017092637) 中，**143 项 pytest 成功**、Docker 33 秒构建（2,864,047,980 字节），四次 SPA/SSR 浏览器运行均有正确的 JSON/HAR/日志，但独立未授权容器确实收到 **两次 GET /forbidden-redirect**，因此总体安全验收 **FAIL**。

根因：`Playwright route.continue_()` 对重定向链的下一跳不保证重新调用 ScopeGuard。修补：普通 HTTP 路由统一用 `route.fetch(max_redirects=0)`，逐跳解析 Location 并在请求发生前重新执行 ScopeGuard，逐跳消耗 RequestGate RPS 预算，最多七跳。不在授权范围的目标立即拒绝；跨协议或未知非 GET/HEAD 重定向保守拒绝。保留真实容器接收端的负向断言，不通过放松测试掩盖漏洞。

**兼容代价**：路由 fetch 需要缓冲完整响应，可能影响 SSE 长连接或巨大资源；合法的 POST 登录跳转、HTTP 到 HTTPS 升级暂时采用 fail-closed 策略，后续需要在保持 R5 的前提下专项兼容性改进。新增七项模拟路由测试；修补的完整 GitHub CI 结果以新提交实际运行状态为准。
