# 文档导航

| 目的 | 权威文档 |
|---|---|
| V10 当前验收结果、复现与整改项 | [ACCEPTANCE_V10_2026-11-22.md](ACCEPTANCE_V10_2026-11-22.md) |
| 每一轮改进的原因、文件及验证边界 | [CHANGELOG.md](CHANGELOG.md) |
| 故障、根因、修复经验与仍未验证的内容 | [FIXES_AND_LESSONS.md](FIXES_AND_LESSONS.md) |
| V10 后的目录、模块职责与兼容性要求 | [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) |
| 详细架构与底层算法 | [PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md](PROJECT_ITERATIONS_ARCHITECTURE_ALGORITHMS.md) |
| 简明数据流架构图 | [architecture.md](architecture.md) |
| AI 启动与排错操作说明 | [API_EXTRACTOR_AI_OPERATIONS.md](API_EXTRACTOR_AI_OPERATIONS.md) |
| 为什么不直接迁移全部源码到 src/ | [adr/0001-compatibility-first.md](adr/0001-compatibility-first.md) |

**维护约定**：源码每次变动同步更新 CHANGELOG，必要时更新架构图、故障经验、测试说明；记录离线测试、Docker、真实站点评测各自的范围。项目入口仍以根目录 [README](../README.md) 为准。
