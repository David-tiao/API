# V13 验收快照：明确授权的本地 GET 请求验证（2026-11-22）

**代码基线**：[旧提交链接已撤销]。前续 [V12 报告](ACCEPTANCE_V12_2026-11-22.md) 已从 V12 原始文档提交恢复，历史记录保持连续。

## 本轮改进

| 检查 | 设计行为 | 验收范围 |
|---|---|---|
| 默认无主动探测 | 标准配置 `explicit_readonly_get_urls=[]`，不新发 GET | MockTransport 单元/主流程通过 |
| 授权与作用域 | 只命中显式 URL 列表和已发现静态 GET，ScopeGuard 允许 | 越界、未列入、POST/DELETE 均不发送 |
| 参数、凭证与跳转 | 拒绝 Query、fragment、凭据、占位符、歧义点段；不自动转发认证 Header，不跟随 3xx | 定向模拟验证 |
| 证据链 | 实际 2xx JSON 返回后写 `phase=probe` 日志、`probe.har`，再经 normalization/EvidenceAuditor 校验 | MockTransport 全流程成功；未真实重放 |
| 预算/限流 | 顺序最多五次，使用现有 RequestGate，8 秒超时，纳入 pipeline 的 `wait_for` | 代码/模拟审查；代理层待验证 |

**执行记录**：隔离 Python 3.13.5 工作副本 `python -m pytest -v --disable-warnings`，**87 passed in 1.53s**，本轮新增 23 项 MockTransport/纯单元/模拟主流程测试；`python -m compileall -q api_extractor tests` 通过。未进行最新 GitHub commit 的完整检出实测、实际网络 Docker、Chromium、隐藏 S1～S5 ground truth 和真实重放。

**安全限制**：GET 方法不能证明服务端无副作用，必须由操作者确认自己允许调用的具体 URL。未授权或不确定只读的接口一律不得加入允许列表。HTTP 200 JSON 的一次成功不等于跨会话稳定重放；带认证、Query、非 JSON、重定向的接口不会被本功能晋升为正式输出。

**官方考核限制**：第 3.6 节允许适配的 `--config` 字段不包括“手工提供某站 API 路径列表”；因此该能力只用于本地开发调试，不能用于隐藏站点特化。默认官方配置下依然采取 V12 的证据分级方式，T1 Recall 仍可能较低。

**综合结论**：本地显式 GET 验证路径通过模拟测试；官方 R6 重放门槛、R1～R8 全部要求和 S1～S5 评分仍未完成最终验收。
