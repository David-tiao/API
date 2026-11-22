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
