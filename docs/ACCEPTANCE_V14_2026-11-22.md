# V14：可重复的离线质量评分验收（2026-11-22）

> 对照《考核细则》§3.2、§3.5、§3.5.1、§3.6。本页是开发期测试结果，不是组织方正式评审成绩。

## 已完成的变更

- 新增 `api_extractor/offline_benchmark.py`：本地只读评分器与 CLI，无网络连接、无目标探测、无生产 API 运行路径修改。
- 新增 `tests/fixtures/benchmark/ground_truth.synthetic.json`：五条人工标注的 T1/T2/T3 纯合成真值，不含任何隐蔽评测站点信息。
- 新增 `tests/test_offline_benchmark.py` 与 `tests/test_benchmark_pipeline.py`：真实评分公式、异常输入、证据链、跨轮稳定性和离线生成的真实 `result.json` 输出测试。
- 补充 [OFFLINE_BENCHMARK.md](OFFLINE_BENCHMARK.md) 的使用方法、准确评分范围、不能推断的官方字段。

## 实际执行（本轮开发工作副本）

- 环境：Python 3.13.5，既有 `v13_safe_get_sandbox` 复制为独立的 `v14_benchmark_work`，在其上添加 V14 模块和测试。
- 命令：`python -m pytest -q -o addopts='' --disable-warnings` → **119 passed in 1.63s**。
- `python -m compileall -q api_extractor tests` → **通过**。
- 新测试覆盖：合成真值中权重 `1.0/1.4/1.8`、`FP > TP` 精确率计 0、空清单不产生伪 100% Precision、重复/第三方域 FP、数字/UUID/哈希/占位符路径等价、两次运行的 0.7/0.3 修正、业务语义字段差异、HAR 与本轮 JSONL 方法/路径/状态/索引一致性、WebSocket GET 握手、GraphQL POST、恶意符号链接、Schema 校验和质量阈值门槛。
- 与生产管线相连的离线集成：假本地页面声明 `fetch("/api/items")`，HTTPX MockTransport 仅对本地显式批准 URL 返回 200 JSON；对独立 `run-a` 和 `run-b` 真正执行流水线，各自生成结果、HAR 和日志，两个运行的离线 Recall/Precision 均为 100%，客观局部分数 60/60、证据交叉核查率 100%、集合 Jaccard 1.0。**注意：站点、动态浏览器和 HTTP 响应均是模拟内容，并不是公网站点验证。**
- 未批准主动 GET 时同一静态页面的 `result.json` 为空，离线部分得分 0/60，`static_candidates.json` 仍保存一条候选；这是 V12 证据门槛对 T1 Recall 的可量化影响，而非评分器错误。

**重要精度说明**：这 119 项来自隔离组合工作副本，而非 GitHub 当前 commit 的完整精确 checkout；V14 新模块及测试在提交后应检查与其测试版本 Git blob 相同。Docker daemon、真实 Chromium、外部授权站点、评测代理的 R4/R5/R7/R8 流量和运行期文件系统均未实测。不能宣布 R1～R8 或 S1～S5 整体验收通过。

## 评分定义、剩余风险

1. **只计算官方可客观核查的 Recall(40)+Precision(20)**；官方的语义 20、证据 10、工程质量 10 未由本程序评分。报告中的 `official_100_point_score` 固定为 `null`。
2. 证据一致率来自本地 HAR/JSONL 文件交叉检查，只证明文件内一致，无法证明日志不是伪造的，更不代表实际重放率超过 80%。
3. 本地无人工复核能力，真值外的可访问接口也会先被计为 FP，官方允许手动纠正，可能产生差异。重复结果按 FP 处理属更保守口径。
4. 当前 V12 默认必须观察实际请求才让 API 进入正式清单；即使本地模拟 60/60，隐藏 T1 仍可能因未触发而严重损失 Recall。V13 的显式允许 URL 仅用于本地授权练习，不可作为官方每站路径适配策略。
5. 若测试失败、真值重复、结果 Schema 不合法或报告质量门槛未达标，工具必须以非零退出；门槛失败时仍保留原子写出的报告供排错。

**结论：V14 建立了可重复的开发期质量回归基准，不是“正式拿到 60 分或 100 分”。** 下一轮应先跑 GitHub 最新完整 checkout、验证 Docker 及代理，再针对真实授权站点记录可审计的网络请求和重放统计。
