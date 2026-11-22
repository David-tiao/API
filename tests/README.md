# tests：回归测试组织

项目规模较小，保留现有 `tests/test_*.py` 的平铺布局，避免移动旧测试影响用户命令和脚本。`pyproject.toml` 已以 `tests` 为 pytest 收集根目录。

- `test_scope.py`：域名与授权范围。
- `test_normalization.py`：方法、路径、鉴权和参数。
- `test_output.py`：JSON Schema。
- `test_evidence_audit.py`、`test_evidence_linking.py`、`test_logger_redaction.py`：证据与敏感信息。
- `test_run_outcomes.py`：预算、浏览器失败与部分结果。
- `test_integration_local_http.py`：本地 HTTP 静态采集集成。
- `test_contract_regressions.py`：历史关键缺陷。
- **`test_candidates.py`**：V10 表单/网络记录转换的 8 项无网络测试。

完整运行 `python -m pytest -q` 需要当前仓库依赖。V10 仅独立运行 8 项新增测试，并执行相关 Python 语法检查；**当前 GitHub 全仓库 pytest、Docker、真实 Playwright 未重新执行**。


- **V14** `test_offline_benchmark.py`、`test_benchmark_pipeline.py`：评分规则、T1/T2/T3、FP/重复/第三方域、独立 HAR/日志与双轮稳定性（32 项新增测试）；`tests/fixtures/benchmark/` 是**纯合成**真值。Python 3.13.5 隔离开发副本完整 119 项通过，新增专项 32 项通过；未在真实 Docker/Chromium 中执行。


- **V15** `test_docker_smoke_fixture.py`：独立运行合成 HTTP 服务，通过本地 loopback 真实请求 HTML、JS、JSON（本地 **1 项通过**）；`fixtures/docker_smoke_site.py` 供 CI Docker synthetic smoke 使用。配置在同一 GitHub commit 上运行全仓库 `pytest` 后再执行 Docker 镜像构建与两个真实浏览器样本。**CI 尚未返回结果之前，不能说完整仓库或 Docker 已通过**。


**V15 真实 CI 记录**：首次 GitHub Actions commit `466dde4` 全仓库 **137 passed in 4.03s**（含新夹具测试），Docker 双轮各 1 条合成 API；后续每次 main 提交都将触发测试，最新版以其 Actions 运行状态为准。


- **V16** 新增 `test_crawler_redirect_scope.py` 四项 HTTPX 重定向安全回归；`test_docker_smoke_fixture.py` 扩展到 SPA、SSR、302 共 3 项。真实 Docker 四轮安全验收见 V16 文档及 GitHub Actions 日志。


- **V17** `test_sse_sampling.py` 新增 11 项 HTTPX MockTransport 有界真实帧、重定向/超时/大小/注释判断；`test_sse_route.py` 新增 6 项浏览器 SSE 路由与限流/作用域测试；`test_docker_smoke_fixture.py` 添加一项 20 秒未关闭的真实 SSE fixture 检查。CI 由四轮拓展为 SPA/SSR/SSE 各两轮，检查最终结果和对方真实访问日志。本地 SSE 和合成 HTTP fixture 合计 15 项通过，完整精确提交以 Actions 结果为准。


- **V18** `test_redirect_policy.py`（24 项纯规则参数化测试）与 `test_browser_auth_redirect.py`（8 项假 Playwright 路由测试）：合法 POST 302/303→GET、清除敏感 Header 和 Body、拒绝 307 POST 重放/HTTP 降级/跨域与不同端口、核对真实首跳状态；合成站 fixture 多一项 session cookie + 303 测试。GitHub Actions 将额外运行八轮真实 Chromium（SPA、SSR、SSE、Login 各两次）；精确结果见 V18 报告。
