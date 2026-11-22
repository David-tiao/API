# V17 验收记录：真实 SSE 的有界采样

**日期**：2026-11-22。V16 已通过同一 GitHub 提交的 150 项测试、四轮 SPA/SSR Docker、独立越界服务器日志零违规。本轮重点处理 V16 逐跳 HTTP 安全适配对长期 SSE 的缓冲/超时限制。

> **最终验收快照**：代码 `0bd65699` 的 [GitHub Actions](https://github.com/David-tiao/API/actions/runs/45019475066) 完成并成功，**169 项全仓库测试、6/6 真实 Chromium、6/6 独立 Schema 通过**。以下保留初始测试计划，并在末尾记录失败→修复→成功的完整证据。

## 本轮主要风险与决策

Playwright 的 `route.fetch()` 适合有限 HTTP 响应，不适合等待无限 `text/event-stream` 结束；但简单恢复 `continue_()` 可能使 302 后续 Host 不受 R5 约束，V16 已在真实接收端证明越界风险。因此 SSE 有独立受限路径，普通 HTTP 仍保持 V16 逐跳安全审计。

SSE 路径只运行于域名授权的 GET/浏览器 `eventsource` 请求；使用 HTTPX 禁止跳转、读取真正上游事件而非造数据；要求 200 + text/event-stream，首个包含 `data:` 的完整帧，最多 32 KiB、5 秒和 3 次同 URL 尝试。共享 R4 的 RequestGate，所有失败都中止并释放并发槽。不发送用户账号/自定义 Header 或 Cookie。

## 验收测试清单

| 测试 | 输入/目标 | 本轮刚创建时的状态 |
|---|---|---|
| 11 项 SSE 核心测试 | HTTPX MockTransport；完整真实事件、分包、注释心跳、超时、302 禁跳、错误 Content-Type 和体积 | **本地 11 项通过** |
| 6 项浏览器事件路由测试 | fake Playwright Route；允许 URL、拒绝未授权、真实帧转发、拒绝非 GET、最多三次重连、资源释放 | 待 GitHub 精确提交全量 CI |
| 4 项合成服务测试 | SPA、SSR、跨域 302 和真实长期 SSE HTTP 头与第一行数据 | **本地 4 项通过** |
| 六轮真正 Docker Chromium | SPA×2、SSR×2、SSE×2；每轮独立 JSON Schema、有效 HAR/JSONL、各场景双轮稳定性 | 待 GitHub CI |
| R5 越界服务独立观察 | 302 与图片路径的禁止请求不得出现在接收端日志 | 待 GitHub CI |

**本地核对**：`python -m pytest -q tests/test_sse_sampling.py tests/test_docker_smoke_fixture.py` **15 项通过**；`compileall` 与 `bash -n` 通过；所有新增网络测试使用 MockTransport 或自建 loopback 服务，不调用公开站点。

**不是正式 S5 订阅复原**：只透传第一个真正的数据事件并主动关闭上游，可能触发 EventSource 重连；每 URL 上限三次。不能保证登录态 SSE、多事件订阅语义、长时间稳定流、真实代理层安全和隐藏考核的完整得分。需要另外的真实授权场景进行完整工程评测。

**保密事项**：仓库当前版本已删除内部资料，但旧 Git 提交历史和平台缓存清理仍需仓库所有者操作；本次测试、文档不包含内部资料正文。


## V17 最终实测：第一次 SSE 失败后的修复闭环（2026-11-22）

本节以真实 GitHub Actions 日志为最终依据，覆盖上面“创建时待 CI”的初始状态。

| 项目 | 首轮提交 | 修复后的最终代码提交 |
|---|---|---|
| Git SHA | `010bac24c01c3b270ae7928b9538a4d0633f925c` | **`0bd65699be167207ad15ff381719cfbad225da88`** |
| Actions | [首轮失败](https://github.com/David-tiao/API/actions/runs/45019132586) | **[复验成功](https://github.com/David-tiao/API/actions/runs/45019475066)** |
| 全仓库 pytest | 168 passed | **169 passed in 6.08s** |
| Docker 构建 | 成功 | **28 秒，2,864,226,562 字节** |
| SPA 双轮 | 通过 | **2/2 通过** |
| SSR 双轮 | 通过 | **2/2 通过** |
| SSE 双轮 | **首次 SSE 正式结果为空，失败** | **2/2 通过，每轮 1 条已观察 SSE API** |
| 独立 JSON Schema | 首轮前 5 次成功，SSE 断言失败 | **6/6 通过** |
| HAR ↔ tool.log | SSE 首轮没有可认可的正式结果 | **六次运行均关联成功** |
| 跨域未授权服务端 | 首轮未完成整体断言 | **无禁止请求，PASS** |
| 工作流整体 | **FAIL** | **completed/success** |

### 失败根因与实际修复

初版 SSE 解析器使用 `bytearray` 累计流数据，完成事件切片后仍返回 `bytearray`。Python 中该对象与等值 `bytes` 可以比较相等，使 MockTransport 的原测试没有发现类型错误；Playwright `route.fulfill(body=...)` 却要求实际的 `bytes` 或字符串，导致 SSE 请求未能成功完成，最终没有有效的请求证据。

补丁将事件切片显式转换为 `bytes`，并在 Fake Route 中要求 `type(body) is bytes`；另新增**真实本地长连接 HTTPX 测试**，模拟服务端发送第一帧后保持连接 20 秒，要求客户端 3 秒内取得真实事件字节，而不必等待 EOF。本地 SSE+fixture **16 项通过**。第二次 GitHub Actions 在**同一代码提交**上通过全部 169 项测试和六轮真实 Chromium。

**得到的结论**：V17 已在合成环境恢复“首次真实 SSE 数据事件”的观测，且 V16 已修复的跨域阻断仍有效。它不是通用持续 SSE 订阅代理：只传首条事件，限制每 URL 三次连接，默认不转发认证 Cookie/Header；多事件、授权登录态、SSE 重连业务语义与隐藏 S5 效果仍未验证。合法 POST 登录重定向、HTTP→HTTPS 升级和真正大型响应仍需后续独立改进。真实代理与 DNS 审计、正式考核评分、敏感 Git 历史清理也仍未完成。
