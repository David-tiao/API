# API Extractor V11：整改验证状态（2026-11-22）

> 代码基线：[`951a50afd34561f0a36f67afb630a656905eb7c6`](https://github.com/David-tiao/API/commit/951a50afd34561f0a36f67afb630a656905eb7c6)。  
> 与 [V10 验收报告](ACCEPTANCE_V10_2026-11-22.md) 对照；V10 结论是历史验收快照，不应覆盖或删除。  
> 依照《RECRUIT-2026-考核细则》3.4、3.6 的 R4/R5/R6 硬性要求。

## 本轮修复结果

| 事项 | V10 问题 | V11 代码状态 | 本轮证据 |
|---|---|---|---|
| R5 注册域边界 | 手动后缀表遗漏 `co.za` 等，可能越界 | **已修复已知代码缺陷**：完整 PSL 离线查询；缺库时保守拒绝不确定兄弟域 | 8 项新边界 + 5 项原作用域测试通过 |
| R4 WebSocket 并发和 RPS | WS 握手绕过共用 RequestGate | **实现层修复**：WS 长连接持续占用槽位，关闭时释放；建立连接按 RequestGate 限频 | 6 项模拟 WS 生命周期与限速测试通过 |
| R6 静态接口真实性 | JS 静态候选存在，但无实际后端请求与重放证明 | **仍未解决**：源码证据只证明代码存在，不能冒充实际请求 | 已明确保留阻断项 |

## 复现与测试

```bash
python -m pytest -q tests/test_scope.py tests/test_scope_psl.py tests/test_ws_gate.py
python -m compileall -q api_extractor tests
```

本轮在隔离 Python 工作副本运行上述相关的 **19 项测试通过**，并通过 Python 编译检查。用于范围检查的 V11 `scope.py` 与 GitHub Blob SHA 一致（`17d85cf98cc8bbea66d0af02d07b11e91f23f9ee`）；Playwright 门控在模拟 Route 上验证，**没有**真实 Chromium/WS 网络连接测试。不同提交、不同工作副本的测试数量不能累加为当前 GitHub 整仓库测试数。

已验证的具体样本：`app.example.co.za` 对 `unrelated.co.za` 拒绝；授权 `api.example.co.za` 可以通过；`foo.github.io` 不会误放行 `bar.github.io`；`127.0.0.1` 不会误放行另一个 IP；不存在 libpsl 时退化为严格同主机/后代策略。WS 连接关闭、上游关闭、建立异常均释放占用，并发为 1 时第二个连接等待；限流模拟在 20 RPS 配置下保留最小请求间隔。

## 尚未通过的正式门槛

1. **R6 + 3.6：** 当前输出仍可能包含仅由静态源码推断的接口，无法保证 `tool.log` 有对应的真实请求或其可重放成功。不能为了达到日志表面一致而记录虚构状态码，也不能对未知 POST/DELETE 自动盲发。需要单独设计安全验证与明确的证据强度分级。
2. **R4/R5 代理审计：** 仅从函数测试可验证代码门控与域名判断，没有实测真正的 Chromium/WebSocket 和代理侧统计。长连接占用共享槽位也可能牺牲可用并发，需真实场景评估。
3. **镜像依赖：** `libpsl` 由 OS 系统库提供，可能因镜像环境不同而不可用。缺失时安全地收紧作用域，可能漏掉授权兄弟子域。仍须验证 Docker 镜像包含可用的 PSL 数据库。
4. **全仓库/端到端：** GitHub 当前主分支所有 pytest、Docker 15 分钟/6GB、预算、R7 文件系统写入边界、S1～S5 hidden benchmark 无实测记录。

## 下一个优先级

先建立**不伪造 HTTP 请求、不会触发非只读副作用**的静态候选真实性机制和评估基准，处理 R6/3.6。然后在 Docker 里做真实 WS/HTTP 联合限流审计。项目架构保持现有大小，不为达到表面规则而引入大型服务或爬虫集群。

**结论**：V11 修复了两个确定的实现缺陷，但不是正式 PASS；R6 仍是首要阻断，其他硬性条款仍有真实环境待验收项。
