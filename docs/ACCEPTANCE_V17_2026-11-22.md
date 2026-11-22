# V17 验收记录：真实 SSE 的有界采样

**日期**：2026-11-22。V16 已通过同一 GitHub 提交的 150 项测试、四轮 SPA/SSR Docker、独立越界服务器日志零违规。本轮重点处理 V16 逐跳 HTTP 安全适配对长期 SSE 的缓冲/超时限制。

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
