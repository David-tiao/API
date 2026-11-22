# V18 验收记录：登录后重定向与 R5/R6 完整性

**日期**：2026-11-22。**代码基线**：V17 最新 `321f7d1`；本文件随 V18 代码一起创建，GitHub Actions 实测结果在提交后另行追加，不能提前宣称新功能通过。

## 本轮目标

此前的安全路由 V16/V17 会拒绝任何 POST 后的 302/303，可能阻断模拟用户登录。V18 只允许已经由明确配置的登录交互触发的 POST 在**同主机、同协议、同有效端口**的 301/302/303 后转 GET，禁止复用请求体和敏感 Header。授权 GET 可同主机 HTTP→HTTPS 升级，但不允许 HTTPS→HTTP 降级；其他非幂等 HTTP 方法或 307/308 POST 不自动重放。始终使用 Route.fetch(max_redirects=0) 手动逐跳验证，原 R5 禁止越界不松绑。

另外必须保持请求真实性：首个 POST 返回 303 就在 `tool.log`、HAR 中如实记 303，后续 GET 的实际 200 在独立 `redirect` 阶段记录，不能因为最后页面为 200 就伪造初始 POST 200。

## 合成登录验收

已授权的内部 Docker 网络目标 `fixture:8765`：`GET /login` 返回表单，显式合成账号提交 `POST /api/session` 后服务器设置 `Set-Cookie: synthetic-session=ok; HttpOnly; Path=/` 并 303 到 `/dashboard`。`/dashboard` 再请求 `GET /api/private`，服务器只有在携带有效 Cookie 时返回 200，否则 401。已登录页面故意含有跨域图片请求，实际越界接收服务端不能收到 `/forbidden-auth`。其它 SPA/SSR/SSE 场景不得擅自 POST。

## 交付质量门槛

| 验证项 | V18 首次提交时状态 |
|---|---|
| 24 项重定向纯规则测试 | 本地 24/24 通过 |
| 8 项路由模拟测试 | 待 GitHub 完整源码执行 |
| 合成 HTTP fixture | 本地 5/5 通过 |
| 精确 GitHub checkout 全仓库 pytest | 待 GitHub Actions |
| Docker 构建 ≤ 900 秒 / 镜像 ≤ 6 GiB | 待 GitHub Actions |
| SPA、SSR、SSE、登录各 2 次真实 Chromium | 待 GitHub Actions |
| 每轮 Schema、HAR/JSONL 与双轮稳定性 | 待 GitHub Actions |
| 未授权接收端禁止路径请求 | 待 GitHub Actions |
| 真正 HTTP→HTTPS TLS 证书端到端 | **未构造，仅规则/假浏览器层面** |

若 Docker 中实际 Cookie 不工作或 POST 被误记 200，必须保留失败证据并修复；不得以删除断言来通过验收。

**边界**：这只是合成授权目标上的登录模拟，不代表实际 S3 隐藏站点、跨域 SSO、验证码或复杂 CSRF；R4/R5 代理层与系统级 R7/R8 审计、正式业务重放率、内部资料旧 Git 历史清理仍未完成。
