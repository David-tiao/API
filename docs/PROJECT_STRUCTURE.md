# V10 项目目录与模块边界

```text
API/
├── api_extractor/          # Python 核心源码
│   ├── cli.py              # 固定 CLI 协议入口
│   ├── pipeline.py         # 任务编排/预算/阶段状态
│   ├── config.py           # 配置读取
│   ├── scope.py            # 授权范围过滤
│   ├── request_control.py  # 限流及并发约束
│   ├── crawler.py          # HTML/JS/CSS 资源采集
│   ├── static_analysis.py  # JS 静态接口发现
│   ├── dynamic_analysis.py # Playwright 动态请求观察
│   ├── candidates.py       # V10：记录转候选纯函数
│   ├── normalization.py    # 路径、参数、鉴权推断与去重
│   ├── evidence.py         # HAR/源码/本轮日志证据审计
│   ├── output.py           # Schema 验证与原子写入
│   └── result.schema.json
├── tools/                  # Node.js Babel AST
├── scripts/                # 原有启动/诊断/验收脚本，不重命名
├── tests/                  # pytest 与本地夹具
├── docs/                   # 架构、ADR、经验及版本记录
├── examples/               # 示例配置和结果
├── demo/                   # 演示材料
├── archive/legacy/         # 老 ZIP / Dockerfile 备份，不是当前运行入口
├── Dockerfile
├── README.md / TOPIC
├── requirements.txt / pyproject.toml
└── package.json / package-lock.json
```

## 单向职责边界

1. CLI 与 pipeline 负责生命周期和预算。
2. Config / ScopeGuard / RequestGate 约束授权范围与请求速率。
3. Crawler / StaticAnalyzer / DynamicAnalyzer 负责**采集事实**，不负责输出 JSON 的合法性。
4. V10 `candidates.py` 用无副作用的 `from_html_forms()` 和 `from_network_records()` 统一表单/浏览器候选格式，网络请求的状态与索引保留到后续阶段。
5. `normalization.py` 处理端点合并及参数/鉴权，`evidence.py` 审计源码、HAR 与当轮日志。
6. `output.py` 校验固定 Schema 并落盘。不得让低层模块直接改写结果文件。

### 兼容边界与当前结构差异

现有 `python -m api_extractor.cli`、`Dockerfile`、`tools/js_ast_analyzer.cjs`、`scripts/*.sh`、JSON Schema 路径均保留。**考核参考结构包含 `src/`，目前仓库使用根目录 `api_extractor/`，这是待正式兼容性验证的结构差异**。本轮没有创建空 `src/` 或复制第二份源码来假装完成迁移。见 [ADR-0001](adr/0001-compatibility-first.md)。

旧 ZIP/备份原始 Git Blob SHA 不变，仅移动至 `archive/legacy/`；不要从旧归档恢复代码覆盖当前 `api_extractor/`。本地 `site.json` 不应填写真实凭据再提交到公开仓库。
