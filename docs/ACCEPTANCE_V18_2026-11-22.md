# V18 验收记录：登录后重定向与 R5/R6 完整性

**日期**：2026-11-22。

> **最新验收状态：V18 本地合成站点 Docker PASS**。代码基线 `fe9e8fc9`，GitHub Actions [第三轮](https://github.com/David-tiao/API/actions/runs/45021419911)：**202 项全仓库测试、8/8 浏览器合成场景与 8/8 Schema 检查通过**；下面保留早期计划/失败原因，末尾记录最终复测。**代码基线**：V17 最新 `321f7d1`；本文件随 V18 代码一起创建，GitHub Actions 实测结果在提交后另行追加，不能提前宣称新功能通过。

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


## V18 最终验收：安全登录流程 Docker 实测 PASS（2026-11-22）

**正式采用的代码基线**：`fe9e8fc96e98a7784fac363e15d5820ff220a196`；实际 [GitHub Actions 运行](https://github.com/David-tiao/API/actions/runs/45021419911) 为 **completed / success**，offline-tests 与 docker-synthetic 两个 Job 均成功。

| 结果项 | 实际数据及审核依据 |
|---|---|
| 同一提交完整 pytest | **202 passed in 6.60s** |
| Docker 镜像构建 | **35 秒**，小于 900 秒 |
| 镜像大小 | **2,864,233,591 字节（约 2.86 GB）**，小于 6 GiB |
| SPA 两轮 | **2/2 通过**，每轮 1 条真实 API |
| SSR 两轮 | **2/2 通过**，每轮 1 条真实 API，未知 POST 未执行 |
| SSE 两轮 | **2/2 通过**，每轮 1 条真实 EventSource API |
| Cookie 登录两轮 | **2/2 通过**，每轮 1 条 `GET /api/private` 真正认证 API |
| 独立 JSON Schema 校验 | **8/8 通过** |
| HAR / tool.log | **八轮均逐请求核对方法、URL、索引和状态码** |
| 原始 POST 303 的真实性 | **通过**：`phase=redirect` 记录 POST `/api/session` 实际 303，后续 GET `/dashboard` 为 200，不把 POST 伪记为最终 200 |
| R5 接收端检查 | **零禁止请求**，包括跨域图片、302 重定向和登录后跨域资源 |
| 八轮稳定性 | **四个场景各自两轮的接口集合一致** |

### 保留真实失败过程

- [首轮 Actions](https://github.com/David-tiao/API/actions/runs/45021056967)：**200 passed / 2 failed**。旧测试将所有 POST→302 和 HTTP→HTTPS 绝对拒绝；更新为仅允许满足同主机安全条件的明确断言，并检查 Body、Cookie/Auth/Content-Type 不泄露，原越界与 307 POST 不重放测试保留。
- [第二轮 Actions](https://github.com/David-tiao/API/actions/runs/45021191967)：**202 passed**、SPA/SSR/SSE 六轮成功，但 Login 的脚本错误要求 HTML `document` POST 必须在 `dynamic` API 相位。改为核对真实网络层 `redirect` POST=303 和 GET=200；同时严格核对私有 API 的真实 GET=200 与 HAR。
- [第三轮 Actions](https://github.com/David-tiao/API/actions/runs/45021419911)：**202 passed、八轮真实浏览器全部通过**，包括实际 Cookie 登录成功。所有失败断言都有保留记录和明确的验收口径依据。

### 仍未解决的问题

**这不是正式隐藏评测 PASS**：目前真正测试的是自建 Docker internal 网络，只有一个公开 Cookie 登录场景，没有多域 SSO、验证码、CSRF、真实 OAuth/OIDC 等复杂状态；HTTP→HTTPS 的真实证书握手尚无 Docker 专项，只通过纯函数和路由模拟验证。Playwright `route.fetch → route.fulfill` 的原始导航 URL 语义在复杂框架上可能仍不同于浏览器自动跳转。R4/R5 真实代理审计、R7 系统级访问监视、S1～S5 ground truth、R6 跨会话重放率和公开 Git 旧历史保密清理仍独立待做。

**解释原则**：此次局部验收能证明“一个授权的 Cookie 登录流程 + 原始 POST 303 真实记录 + 新的合成 R5 阻断”在精确 GitHub 版本通过；不允许扩大为任意网站登录、所有 HTTP 重定向或整项正式考核的结论。
