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
