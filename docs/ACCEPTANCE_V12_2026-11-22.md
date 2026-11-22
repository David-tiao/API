# V12 验收状态：R6 证据分级（2026-11-22）

代码基线：[3efe6a3e2](https://github.com/David-tiao/API/commit/3efe6a3e2f28d4b4cebbc9f224cfca39dced3bf9)。根据《RECRUIT-2026-考核细则.md》第 3.4、3.5 和 3.6 节评估。V10/V11 报告保留为历史快照。

## 与 V11 的差别

| 事项 | V11 | V12 |
|---|---|---|
| JS 中静态 `fetch(...)` | 有效静态文件即可进入 `result.json` | 如果没有本轮真实请求与已审计 HAR，只进入 `static_candidates.json` |
| 正式 API 请求证据 | 混有静态文件与已观察 HAR | 只保留至少一条已审计通过的 HAR |
| `tool.log` | 正常记录浏览器或爬虫真实请求 | 不增加伪造请求，另记 `request_proof_gate:confirmed=N,static_only=M` 汇总 |
| CLI / Schema | 固定 | 完全不变 |
| 部分浏览器失败 | 可能因无正式接口而返回失败 | 如果已有合法 JSON 交付，则退出码 0，日志明确 `partial_browser_failure`；真正管线异常仍失败 |

## 离线验收依据

- 针对证据分级的 8 项测试覆盖：源码-only 不认证、已审核 HAR 通过、混合来源保留、诊断 sidecar 脱敏、反复运行覆盖、无磁盘副作用。
- 4 项主流程模拟测试覆盖：静态-only → 正式清单为空；模拟有效 HAR 和对应请求日志 → 正式保留；无 HAR → 不认证；第二轮不遗留上一轮侧边文件。
- 现有规范化、作用域、审计、输出等测试一起运行，在隔离组合工作副本中 **50 项相关测试通过**，并通过 Python `compileall`。
- **未运行**：GitHub 当前 main 最新精确全量 checkout 的 `pytest`、真实 Docker、Chromium、代理限流审计及未知 S1～S5 的请求重放。

## 对 R6 / 3.6 的评估

**改善：** 至少能证明正式结果具备本轮真实观察到的请求证据，与文件、索引、方法、Host、Path、HTTP 状态一致。避免把静态代码中的声明当成已经执行的网络请求。

**不能证明：** 这些接口能够在另一会话中重放成功，或达到抽查 80% 命中率；签名、Cookie、登录状态可能使复现失败。仍不能判 R6/3.6 正式 PASS。

**分数风险：** 仅静态可见的 T1 在评分中权重为 1.0，Recall 计 40 分。V12 默认不把未观测的 T1 输出，因此可能显著降低 Recall。必须结合后续**有授权且安全**的只读验证或更好的浏览器探索改善召回，而不能直接向任意未知 POST/DELETE 自动发请求。

## 下一轮建议

1. 在授权练习站点设计安全只读验证，明确可探测方法/路径，带共享 RequestGate、ScopeGuard 与预算，不擅自扩展到状态变更请求。
2. 另建立可重复的固定 mock ground truth，比较 V11 与 V12 的 TP、FP、FN，而不仅是 pytest 通过数量。
3. 在 Ubuntu Docker 环境实测 `result.json`、`tool.log`、HAR 的可重放率，记录至少 10 条真实请求重放统计。
4. 补齐 Python 依赖 hash/uv.lock、镜像容量与真实代理安全检查。

**结论：V12 是证据完整性与诚实输出方面的局部改进，不是综合验收合格。**
