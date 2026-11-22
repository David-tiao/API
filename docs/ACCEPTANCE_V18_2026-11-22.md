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


## CI 第一次运行：兼容性旧断言需升级，而非删除

[GitHub Actions 首轮](https://github.com/David-tiao/API/actions/runs/45021056967)：精确 checkout **200 passed / 2 failed**，Docker 因离线门禁失败而未执行。失败测试是 V16 旧的“任何 POST→302 都拒绝”和“HTTP→HTTPS 一概拒绝”断言；这两类行为正是 V18 受控放开范围。旧 FakeRoute 也没有请求 Header，无法验证新逻辑的敏感字段移除。

**整改**：为 FakeRoute 加入 Content-Type/Cookie 等模拟 Header，将两项改为正向强断言：相同 Host 的 POST 302 必须使用 GET 且 `post_data=""`、不得复制 Cookie/Auth/Header；同 Host GET 的 HTTP→HTTPS 升级须显式使用新 URL，仍不得复制敏感 Header。新 V18 测试与旧的跨域阻断及 POST 307 拒绝测试继续保留。此改动不放宽 R5/未知 POST 安全标准；最新完整 CI 和 Docker 结果另行确认。


## CI 第二轮：登录表单为 document 请求，修正真实日志检查

[GitHub Actions 第二轮](https://github.com/David-tiao/API/actions/runs/45021191967)：同一提交全仓库 **202 passed**，Docker 构建约 33 秒；SPA、SSR、SSE 双轮全部通过，首次 Login 场景运行到验收断言时失败。原因：测试要求登录 POST 必须标记 `phase=dynamic`，但页面表单 POST 的浏览器资源类型是 `document`，原动态 API 观察器仅记录 `fetch/xhr/eventsource`；该 POST 通过浏览器路由显式 `route.fetch` 实际发生，真实 303 则记在 `phase=redirect`。

**修正验收口径而不是绕过真实性**：未知 POST 仍不能发生；允许的唯一 POST 必须是 `/api/session`，且后续强制核验它具有 `phase=redirect, status=303` 的真实记录，目标 `GET /dashboard` 必须是 200。继续要求登录后的私有 `GET /api/private` 为正式结果且 HAR/日志状态 200。若登录 Cookie 不生效，下一轮仍会失败并继续修复。
