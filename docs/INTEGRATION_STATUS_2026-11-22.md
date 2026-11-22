# API Extractor：完整仓库集成进度（2026-11-22）

> 本文记录 **GitHub 开发分支实际包含的改动**，与历史独立 ZIP/补丁包中的 V19–V27 草稿严格区分。本分支尚未合并至 main；不得把本文件当作正式发布说明。

## 当前工作基线

- 来源：GitHub `David-tiao/API`，V18 基线 `0607b7e1dcaaf4db5b5100fe1471fd131a40a81b`。
- 开发分支：`integration/authenticated-navigation-20261122`。
- 工作范围：增加登录后的只读站内链接采集、受控页面导航以及真实合成站点验收；保留现有 CLI、Schema、证据审计、全局限流和重定向安全策略。
- 代码结构未迁移，正式扫描入口仍是 `python -m api_extractor.cli`。

## 本分支的实际改动

1. `api_extractor/dynamic_analysis.py`：浏览器登录后获取最多 24 个当前页面的安全锚点链接；每个访问成功的页面继续发现锚点。最多收集 48 个候选地址，最多进行 12 次页面导航。
2. 只处理明确授权主机下的 HTTP(S) 网址；拒绝 URL 凭据、非 Web 协议以及常见退出登录、删除、支付等动作路径；绝不为了发现链接而点击按钮或提交未知表单。
3. `tests/test_authenticated_navigation.py`：验证 URL 解析、范围限制、危险链接拦截、去重、数量限制与异常处理。
4. `tests/fixtures/docker_smoke_site.py`：登录后通过 Dashboard → Reports → Annual report 两级页面才能触发 `GET /api/annual-report`，未登录访问必须返回 401。
5. `scripts/ci_docker_smoke.sh`：登录场景除 `/api/private` 外，还必须找到有真实 HAR/日志对应证据的 `/api/annual-report`。保持双轮运行与禁止访问未授权接收端的检查。
6. `.github/workflows/quality-gate.yml`：增加 Pull Request CI 触发，不再需要先把实验代码合并到 main 才能测试。

## 验收门槛

- 当前分支全仓库 pytest 和语法检查通过。
- Docker 实际构建成功，镜像在限额内。
- 四个合成场景（SPA/SSR/SSE/Login）各独立运行两次；Login 场景要求两个有真实请求证据的授权 API。
- 未授权 Host 不接收请求；未知 POST 未被提交；每轮 HAR 与 tool.log 方法、URL、状态、索引相互对应。
- 合成结果与真实 S1–S5 隐藏站点评分严格区分。

**状态记录原则**：上述门槛是 CI 要求，并不代表 CI 已运行或通过。只有实际 GitHub Actions 结果为 completed/success 后才补写真实执行记录。

## 仍未集成的内容

此前本地交付的 V20–V27 离线补丁（日志阶段兼容、签名/GraphQL 增强、离线证据审计和整合器等）**尚未在本分支执行完整集成**，不得借用其中专项测试数量宣称 GitHub 最新代码已完成这些增强。

正式交付尚需：逐项合入并回归 V20–V27、代理/DNS 范围审计、真实 TLS/SSO 兼容、S4/S5 授权场景覆盖率、数据安全与公开仓库历史材料审查，以及最终 Docker/Chromium 与陌生站点验证。
