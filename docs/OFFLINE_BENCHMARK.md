# V14：可重复的离线评分基准（开发期，不是官方评测）

> 参照 `RECRUIT-2026-考核细则.md` 第 3.2、3.5、3.5.1、3.6 节。**数据源必须是明确标记的自建 / 授权模拟站点**。不得使用隐藏评测域名、硬编码真实考题接口，也不得把该基准的分数写成正式 100 分。

## 为什么做这个基准

V12 为满足 R6，将没有真实请求证据的静态接口移至 `static_candidates.json`；这改善证据一致性，却可能损失高权重的 Recall。V13 的额外 GET 探测只在本地显式批准的 URL 清单下启用，不是官方允许的逐站适配策略。单靠“pytest 通过多少项”，无法知道工具的 **TP / FP / FN**、稳定性以及证据是否一致。

V14 增加独立于生产管线的 `api_extractor/offline_benchmark.py`，**不会向站点联网，不会修改工具结果或证据**。它只读取自建 `ground_truth.json` 和两个独立运行的输出目录，用固定规则计算客观可度量的指标。

## 最小目录

```text
benchmark-local/
├── ground_truth.json        # 人工为自己搭建的 fixture 确认真值
├── run-a/
│   ├── result.json          # 第一次运行的实际输出
│   ├── tool.log             # 对应这次运行的日志
│   └── evidence/            # HAR 及其他证据
└── run-b/
    ├── result.json          # 第二次独立运行（必须用单独目录）
    ├── tool.log
    └── evidence/
```

`tests/fixtures/benchmark/ground_truth.synthetic.json` 是完全合成的五条 T1/T2/T3 演示真值；**不对应任何考核站点**。`tests/test_benchmark_pipeline.py` 使用 MockTransport 和模拟页面进行两次独立运行，演示如何对实际 `result.json` 与 `probe.har` 计分，**并不调用互联网接口**。

## 运行方法

在已安装仓库依赖的项目根目录：

```bash
python -m pytest -q tests/test_offline_benchmark.py tests/test_benchmark_pipeline.py
python -m pytest -q              # 建议同时执行完整回归
python -m api_extractor.offline_benchmark \
  --truth /path/to/your/ground_truth.json \
  --run-a /path/to/your/run-a \
  --run-b /path/to/your/run-b \
  --report /path/to/your/score.json \
  --min-recall 0.40 \
  --min-precision 0.75 \
  --min-evidence 0.90 \
  --min-jaccard 0.95
```

最后的阈值是**开发者自定义门槛示例，不是组织方合格线**。任一运行未达到阈值，命令退出 `1`，但会先原子写出完整 JSON 报告，方便排查。没有阈值时只出报告，不强制达标。若任一输入不符合结构或 `result.json` 不符合仓库 Schema，直接报错，不生成误导性的分数。

真值数据形状：

```json
{
  "site": "synthetic-offline",
  "allowed_hosts": ["app.example.test"],
  "endpoints": [
    {"method": "GET", "path": "/api/items", "tier": "T1"},
    {"method": "GET", "path": "/api/account", "tier": "T2"},
    {"method": "GQL", "path": "/graphql", "tier": "T3"}
  ]
}
```

`site` 必须与两次 `result.json` 的 site 一致。`allowed_hosts` 是离线真值中明确允许的主机集；预测条目即使命中 Method + Path，只要 Host 不属于该集合，仍作 FP。真值中不得重复 Method + 归一化 Path，否则拒绝评分。

## 与考核细则一致的客观规则

| 指标 | 离线实现 | 口径出处 |
|---|---|---|
| TP / FP / FN | 按 `METHOD + 归一化 PATH` 匹配；数字/UUID/长哈希/`{id}` 等归并；不同 Method 为不同条目 | §3.5.1 |
| T1/T2/T3 权重 | `1.0 / 1.4 / 1.8` | §3.5.1 |
| Recall（40 分） | `40 × Σ命中真值权重 / Σ全部真值权重` | §3.5 |
| Precision（20 分） | `20 × TP / (TP + FP)`；`FP > TP` 时**整项 0**；无输出时 Precision 为 `null`、得分 0 | §3.5 |
| 站点双轮修正 | `0.7 × (s1+s2)/2 + 0.3 × min(s1,s2)` | §3.5 |
| 站点权重 | S1/S2/S3/S4/S5：`1/1/1.2/1.3/1.5`；四站仅 S2–S5 | §3.2、3.5 |
| 稳定性诊断 | 端点集 Jaccard、只看业务字段的 SHA-256 指纹、两轮差异列表 | V14 附加指标，不属于官方打分 |
| 证据一致率 | 独立读取本次 `tool.log` 与文件系统 HAR，按 Method/Host/Path/索引/状态交叉核对 | V14 代理指标，不等于重放成功 |

报告的 `objective_points_60` 和 `adjusted_objective_points_60` **只覆盖官方 Recall 40 + Precision 20 的部分分值**；`official_100_point_score` 始终为 `null`。没有对业务语义 20、正式证据链 10、工程质量 10 作机器推断。查询参数集合及类型、auth、响应字段和业务用途属于语义评分范畴；本工具不伪造这些分数。

`aggregate_sites()` 仅在所有 S1–S5 或 S2–S5 都有合法局部结果时按官方站点权重聚合这些 **60 分以内的局部分数**；不提供官方总分。

## 证据一致率与真实证据的区别

- 有效 HAR 引用必须位于当前运行目录之内（拒绝路径穿越、越界符号链接），索引有效；HAR 的 HTTP 方法、Host、Path、状态码必须能在同一目录的 `tool.log` 里找到具有相同索引的 `dynamic` 或明确标记的 `probe` 请求。
- WebSocket 的 `WS` 对应底层 GET 握手，GraphQL 的 `GQL` 对应 GET/POST；两者分别核验。
- `evidence_rate_all_outputs` 是**全部预测接口**中具备有效 HAR/日志引用的比例，`evidence_rate_among_tp` 是 **TP** 中具备此类证明的比例；当分母为零时报告 `null`，不假定 100%。
- **重要限制**：自建 JSONL/HAR 可以相互一致但仍未真的在服务器上发生请求；本指标只验证文件与索引的一致性，不具备网络抓包级的反造假能力，不保证 HTTP 重放、跨会话认证或业务语义正确。正式 R6/§3.6 仍必须由真实授权站点和网络审计验证。

## 明确有意采用的保守差异

1. 真值清单外的接口一律暂记 FP。**组织方允许经人工验证真实可访问的漏标接口改记 TP**；本工具不能自动进行这一步，因此可能低估 Precision，报告不等同官方结果。
2. 输出同一个 Method + Path 两次，第一条满足真值可计 TP，多余的重复条目按 FP 处理；这是本地防回归的保守策略，官方是否去重由组织方决定。
3. Host 用于离线作用域核验；官方以 Method + 归一化 Path 为主要匹配键，但第三方域名是 FP。
4. 双轮“业务字段相同”指纹排除 `generated_at` 和 HAR request_index 等运行噪音，但对 auth、参数、响应、note 的变化敏感；没有把本地 Jaccard 数值当成官方稳定性分数。
5. 合成真值是测试夹具，不反映 S1～S5 隐藏站点难度分布，不能拿本地 60/60 的结果预测赛题得分。

## 质量门槛与保留历史

建议至少连续两轮使用**独立输出目录**，记录报告提交 SHA 和运行环境，在变更分析规则前后比较 `weighted_recall`、`precision`、`evidence_rate_all_outputs`、`endpoint_jaccard`。门槛失败时，优先看 `matched` / `missed` / `only_a` / `only_b`、`duplicate_fp`、`out_of_scope_fp`，不要仅增加测试条数。

本轮具体执行结果、已验证与未验证项目见 [ACCEPTANCE_V14_2026-11-22.md](ACCEPTANCE_V14_2026-11-22.md)，迭代原因见 [CHANGELOG.md](CHANGELOG.md) 的 V14。
