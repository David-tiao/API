# 📚 API Extractor 文档中心

本目录采用**三条阅读路线**，让读者按照自己的需求选择内容，而不是从大量历史验收记录中寻找入口。

- **01-overview：零基础理解。** 精简不是删掉专业名词，而是将必要名词用通俗语言解释清楚，适当舍弃底层实现细节。本篇不放可执行运行命令。
- **02-technical：专业技术设计。** 解释架构、真实算法及数学推导、历次迭代变化，适合源码学习和技术答辩。
- **03-operations：实际运行。** 集中维护安装、启动、检查、测试、诊断所需命令及前置条件，避免在概念篇中混入操作教程。

## 1. 文件结构及用途

```text
docs/
├── README.md                          本文：文档设计与总导航
├── 01-overview/                       零基础精简篇
│   └── README.md                      项目、术语、架构、文件职责、能力边界
├── 02-technical/                      专业技术篇
│   ├── README.md                      专业篇阅读导航
│   ├── 01-ARCHITECTURE.md             详细架构与数据流、模块职责、安全边界
│   ├── 02-ALGORITHMS.md               底层算法、数学推导、复杂度与评分模型
│   └── 03-VERSION_HISTORY.md          V0–V18、PR #1/#2 的升级简史
├── 03-operations/                     运行操作篇
│   └── README.md                      命令行手册：安装、启动、测试、排错
├── adr/                               历史架构决策记录
├── ACCEPTANCE_*.md                    历史验收报告与证据索引
├── CHANGELOG.md                       详细迭代原始记录
├── CAPABILITIES_AND_LIMITS.md          完整能力与限制说明
├── BEGINNER_GUIDE.md                   旧版综合入门教程（历史参考）
└── 其他原始设计、故障和运行说明        保留旧链接与技术追溯
```

这里的三个编号目录是新的主阅读入口。原有文档没有删除或移动，保留历史路径是为了让旧 README、PR 与验收报告中的引用继续有效；历史记录中的“待合入”等措辞反映当时状态，不代表当前 main 状态。

## 2. 选择阅读路线

| 读者目标 | 推荐文档 |
|---|---|
| 完全不懂编程或 API，想读懂项目 | [01 零基础精简篇](01-overview/README.md) |
| 想研究系统架构与源码调用关系 | [02.1 专业架构设计](02-technical/01-ARCHITECTURE.md) |
| 想学习算法公式、复杂度分析、指标计算 | [02.2 算法与数学推导](02-technical/02-ALGORITHMS.md) |
| 想了解每一版究竟升级了什么 | [02.3 版本简史](02-technical/03-VERSION_HISTORY.md) |
| 想安装依赖、实际运行、复现验收和排错 | [03 运行操作手册](03-operations/README.md) |
| 想进一步核对能做什么、不能做什么 | [能力与限制完整说明](CAPABILITIES_AND_LIMITS.md) |
| 想看代码仓库与总体成果 | [项目首页](../README.md) |

推荐顺序：**零基础篇 → 专业篇或操作篇**。专业篇按架构、算法、版本顺序阅读；实际执行命令可以直接进入操作篇。

## 3. 文档维护原则

1. 通俗篇优先讲清楚概念、架构比喻和文件用途；不放命令、不复制专业推导。
2. 专业篇必须与实际源码一致：数学模型和理想复杂度应区别于实现，不宣称没有实现的算法；版本总结以原 CHANGELOG 和 PR 为依据。
3. 操作篇集中维护现行命令；在运行目标前说明授权、配置与网络前置条件，不擅自修改机器或其他容器。
4. 历史验收记录保留原始提交、测试范围、结果和失败信息；新文档不能将旧结果包装成新测试。
5. 任何功能增强都同步更新专业篇、能力边界和必要的操作命令；官方隐藏评测、系统级审计与本地/合成测试始终区分。

## 4. 原始资料与历史证据索引

以下是此前文档目录中的资料，作为进一步核查的入口。新读者优先从第 2 节选择阅读路线。

| 目的 | 权威文档 |
|---|---|
| **🎉 完结撒花版首页**：工程状态、快速开始、目录地图与验收边界 | [../README.md](../README.md) |
| **能力与边界（必读）**：支持什么、支持到什么程度、明确不支持什么及验证依据 | [CAPABILITIES_AND_LIMITS.md](CAPABILITIES_AND_LIMITS.md) |
| **零基础先读**：项目整体介绍、术语、文件夹含义、运行与输出详解 | [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) |
| **浏览器加载的 Lazy JS Chunk** 静态 AST 二次分析及请求证据分层 | [ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md](ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md) |
| **SPA Hash + Socket.IO** 受控路由发现、协议分类及双轮真实验证 | [ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md](ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md) |
| **Juice Shop** 独立双轮真实容器验收、浏览器关闭修复与静态字典过滤 | [ACCEPTANCE_JUICE_SHOP_2026-11-23.md](ACCEPTANCE_JUICE_SHOP_2026-11-23.md) |
| **历史开发过程**：登录后深层页面探索和当时待合并的记录（后续改动已合入 `main`） | [INTEGRATION_STATUS_2026-11-22.md](INTEGRATION_STATUS_2026-11-22.md) |
| **V18** 安全登录重定向与八轮 Docker 验收 | [ACCEPTANCE_V18_2026-11-22.md](ACCEPTANCE_V18_2026-11-22.md) |
| **V17** SSE 有界流观察与六轮 Docker 验收 | [ACCEPTANCE_V17_2026-11-22.md](ACCEPTANCE_V17_2026-11-22.md) |
| **V16** SSR/跨域负向验收与 CI 结果 | [ACCEPTANCE_V16_2026-11-22.md](ACCEPTANCE_V16_2026-11-22.md) |
| **V15** 当前提交的 CI、Docker 和双轮验收说明 | [ACCEPTANCE_V15_2026-11-22.md](ACCEPTANCE_V15_2026-11-22.md) |
| **V14** 离线评分验收与真实执行记录 | [ACCEPTANCE_V14_2026-11-22.md](ACCEPTANCE_V14_2026-11-22.md) |
| 离线评分器使用方法、公式与局限 | [OFFLINE_BENCHMARK.md](OFFLINE_BENCHMARK.md) |
| **V13** 本地 GET 验证、安全边界及验收 | [ACCEPTANCE_V13_2026-11-22.md](ACCEPTANCE_V13_2026-11-22.md) |
| **V12** R6 证据分级与正式输出风险 | [ACCEPTANCE_V12_2026-11-22.md](ACCEPTANCE_V12_2026-11-22.md) |
| **V11** 验收整改状态、风险与下轮重点 | [ACCEPTANCE_V11_2026-11-22.md](ACCEPTANCE_V11_2026-11-22.md) |
| V10 当前验收结果、复现与整改项 | [ACCEPTANCE_V10_2026-11-22.md](ACCEPTANCE_V10_2026-11-22.md) |
| 每一轮改进的原因、文件及验证边界 | [CHANGELOG.md](CHANGELOG.md) |
| 故障、根因、修复经验与仍未验证的内容 | [FIXES_AND_LESSONS.md](FIXES_AND_LESSONS.md) |
| V10 后的目录、模块职责与兼容性要求 | [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) |
| 详细架构与底层算法 | [PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md](PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md) |
| 简明数据流架构图 | [architecture.md](architecture.md) |
| AI 启动与排错操作说明 | [API_EXTRACTOR_AI_OPERATIONS.md](API_EXTRACTOR_AI_OPERATIONS.md) |
| 为什么不直接迁移全部源码到 src/ | [adr/0001-compatibility-first.md](adr/0001-compatibility-first.md) |
| 完结版之前的完整 README 文字存档（仅供追溯，不应作为最新运行指南） | [README_HISTORY_BEFORE_FINALE_2026-11-23.md](README_HISTORY_BEFORE_FINALE_2026-11-23.md) |
