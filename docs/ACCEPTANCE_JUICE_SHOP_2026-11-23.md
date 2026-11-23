# OWASP Juice Shop 独立双轮预验收：浏览器收尾与静态资源误报修复

日期：2026-11-23（Asia/Singapore）

> 仅测试本人启动的 OWASP Juice Shop 容器，Docker 内网不开放端口。不是 OWASP 公共演示站或官方隐藏 S1–S5 考场。本记录描述 **GitHub 独立验证分支**，未声明已合入 `main`。

## 测试版本和范围

- 扫描器基线：`main@6608f206dba7ba2543f117d7d5c9a749eab9fa8e`。
- 修复所在分支：`validation/juice-shop-selfhosted-20261123`。
- 靶场：OWASP Juice Shop 官方 Docker 镜像 `bkimminich/juice-shop@sha256:adaf6a6ca50f772dff7d2fe56972c659e81a61e0dbbe607c2b39fefd436e6153`。使用封闭的 `docker network --internal`，无 `-p` 主机端口映射，未使用任何真实凭据。
- 两轮独立扫描，均使用原 CLI 参数、单独的 `/out` 挂载、只读根文件系统、`--budget 120` 秒。
- 两轮均独立读取正式 JSON Schema 和 `tool.log`，逐项检查 API 的真实 HAR/JSONL 方法、请求 URL、状态与索引；只上传去敏摘要，**不上传原始 HAR、请求体或账号**。

## 先前实际失败

基线源码在调用 `context.close()` 后又发送 `browser.close()`。Juice Shop 两轮均在该次关闭期间触发 Playwright `KeyError`（堆栈位于 `_connection.py`），产生 `run_status:partial_browser_failure`；此前尽管发现 10 个请求证实的候选 API，也不能将其记作正式运行成功。

修复采用 `async_playwright()` 生命周期管理器完成进程/连接关闭，不在正常退出路径上重复发送浏览器关闭协议命令；上下文关闭仍正常等待，驱动退出若产生错误仍会报告失败。新增 `tests/test_browser_shutdown_lifecycle.py` 的离线模拟测试确认：正常退出必须释放驱动；驱动真正关闭失败不得伪装为成功。

## 完成一次真实修复验收（原始请求过滤前后对比）

- 原始基线：两轮各 10 条 HAR 支持的接口 + 69 条未证实的静态线索；均有浏览器关闭异常。
- 修改关闭生命周期后：[GitHub Actions #45127615226](https://github.com/David-tiao/API/actions/runs/45127615226) 返回成功，**两轮各 10 条有证据接口、运行状态 `completed`、Jaccard=1.0000**。
- 发现 `GET /assets/i18n/en.json` 是浏览器用 `fetch` 获取的静态翻译字典，不应当被混入 API 清单。
- 加入只针对 `/assets/i18n/<语言>.json` 的 GET 静态资源过滤，不影响 `/api/*.json`、`/rest/*`、POST、WebSocket 请求；保留原始 HAR/日志，不伪造证据。新增 `tests/test_static_i18n_candidate_filter.py`。
- [GitHub Actions #45127766014](https://github.com/David-tiao/API/actions/runs/45127766014) 成功：**两轮各 9 条有 HAR 证据的 API，Jaccard=1.0000，正常完成，无浏览器关闭错误**。

这些数量是对当前环境下运行期实际触发的接口的观察，不代表 Juice Shop 所有内部 API 的真值，也不能据此计算官方 Recall 或 Precision。静态分析另外发现的 69 条候选无足够请求证据，继续隔离在 `static_candidates.json`。

## 仍待执行的验收

- 在本分支最新提交运行完整仓库 pytest、Schema、Docker/Chromium 合成回归和 Juice Shop 双轮验收，实际结果以对应的 GitHub Actions SHA 为准。
- 需要另外测量真实站点的 TP/FP/FN，尤其是未登录可达 API 之外的登录流程、复杂 GraphQL、动态签名、Socket.IO 请求分类。
- 本轮的自建 Juice Shop 仅验证基本授权网络边界，不能替代系统级代理/DNS 和文件访问审计。

## 如何重跑

`scripts/ci_lab_juiceshop.sh` 配合 `.github/workflows/owasp-juice-shop-lab.yml` 使用。测试容器始终无主机端口映射；GitHub Actions 摘要构件不含敏感请求数据。

**合并纪律**：必须在开发分支最新提交上同时获得完整回归和 Juice Shop 两轮成功后，才将此修复标为可合入主分支，且不得以自动测试替代人工审查或官方隐藏评测。
