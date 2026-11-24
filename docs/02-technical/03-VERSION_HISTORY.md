# 02.3｜项目版本简史：每次升级改变了什么

> V0–V18 是开发迭代编号，并非独立软件发布版本；软件版本仍为 v0.1.0。PR #1、PR #2 是后续集成记录。下面按 [CHANGELOG 原文](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/CHANGELOG.md) 压缩整理；旧验收文件里的“待合入”“待测试”描述的是当时快照，不是现在的主分支状态。

## 1. 从基础功能到可靠交付

| 阶段 | 升级内容 | 为什么升级 |
|---|---|---|
| V0 | Python CLI、资源采集、AST/Regex、浏览器观察、归一化、Docker 输出骨架 | 先建立完整流程 |
| V1 | 修复 WebSocket 调用与动态等待策略 | 减少浏览器连接异常及异步响应漏记 |
| V2 | 收紧授权范围、错误状态处理与静态候选过滤；完善依赖和运行契约 | 避免错误被当成成功、范围越界及资源误报 |
| V3 | 增加请求体签名字段推断、模拟 HTTP 测试及双轮验收脚本 | 增强 S4 线索与可复现验证 |
| V4 | 调整浏览器 HOME、临时目录和缓存位置 | 使输出和运行文件边界更容易审计 |
| V5 | 增加 WebSocket、SSE 静态构造器识别；AST 与 Regex 合并 | 扩大协议线索覆盖 |
| V6 | 引入 EvidenceAuditor，审核文件、HAR 索引、端点及日志 | 证据由“有引用”升级为“引用可核对” |
| V7 | 补充架构、算法和演进文档 | 让后续维护者理解设计原因 |
| V8 | 区分完整完成、浏览器部分失败、预算耗尽与致命失败 | 合法部分结果不冒充完整成功 |
| V9 | 日志脱敏与当次运行证据关联 | 减少敏感信息暴露、旧日志误匹配 |
| V10 | 拆出候选适配层、治理文件结构、保留兼容入口 | 降低模块耦合，便于独立测试 |
| V11 | 引入本地公共后缀库；WebSocket 纳入共享门控 | 改善可注册域判定与并发管理 |
| V12 | 正式结果要求真实请求证据，静态线索单独输出 | 降低静态猜测误报；也可能牺牲召回 |
| V13 | 增加仅在本地显式授权时启用的有限 GET 验证 | 安全地补充少量静态线索的请求证据 |
| V14 | 新增独立离线评分器、双轮稳定性和证据检查 | 有真值时才能客观量化局部质量 |
| V15 | 建立 GitHub Actions 完整回归、Docker/Chromium 双轮验收 | 不再只凭代码或离线测试判断交付能力 |
| V16 | 加入 SSR 与跨域负向验收，修复浏览器逐跳重定向越界问题 | 用独立接收端观察验证范围约束 |
| V17 | SSE 有界真实事件采样；六轮 Docker 测试 | 处理持续连接无法等待整个响应的问题 |
| V18 | 受控登录 POST→GET 重定向、Cookie 认证与八轮 Docker 验收 | 让常见登录后的接口可被真实观察 |

对应详细报告：[V10](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V10_2026-11-22.md) · [V11](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V11_2026-11-22.md) · [V12](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V12_2026-11-22.md) · [V13](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V13_2026-11-22.md) · [V14](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V14_2026-11-22.md) · [V15](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V15_2026-11-22.md) · [V16](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V16_2026-11-22.md) · [V17](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V17_2026-11-22.md) · [V18](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_V18_2026-11-22.md)。

## 2. 主分支集成与真实应用改进

| 阶段 | 主要升级 | 验证意义 |
|---|---|---|
| PR #1：集成 | 登录后深层只读导航、GraphQL 与签名字段识别、日志阶段兼容 | 243 项离线测试、8 次合成 Docker/Chromium 验收通过 |
| Juice Shop 初次实测 | 在隔离自建站点发现 Playwright 退出 KeyError | 暴露旧模拟测试遗漏的问题；两轮部分失败，不能算通过 |
| PR #2：浏览器收尾 | 修复 Playwright 生命周期关闭流程 | 两轮从部分失败变为正常完成 |
| PR #2：静态资源过滤 | 过滤 GET/fetch 的语言字典，保留普通 JSON API 和 WS | 每轮记录由 10 条变为 9 条；已观察的翻译文件不再计作 API |
| PR #2：SPA Hash | 保留安全 Hash 路由，新增真实路由触发的合成测试 | 合成测试从 8 次扩展到 10 次；没有证明 Juice Shop 覆盖率上升 |
| PR #2：Socket.IO | 标注 GET/POST 轮询、WS 握手，不导出不透明协议帧为参数 | 两轮各 3 条传输记录获得正确分类 |
| PR #2：运行时懒加载 | 复用浏览器已下载的 JS 做二次静态分析 | 未调用的声明进入静态线索文件，不冒充真实请求 |
| 收官 | PR #2 合并 main；增加新手教程、能力限制与首页文档 | 最终 267 项测试、10 次合成浏览器验收；隔离 Juice Shop 每轮 9 条证据记录 |

证据入口：[PR #1](https://github.com/David-tiao/API/pull/1) · [PR #2](https://github.com/David-tiao/API/pull/2) · [Juice Shop 报告](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_JUICE_SHOP_2026-11-23.md) · [SPA/Socket.IO 报告](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_SPA_SOCKETIO_2026-11-23.md) · [Lazy Chunk 报告](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md) · [收官主分支 CI](https://github.com/David-tiao/API/actions/runs/45140723425)。

## 3. 为什么会这样演进？

最早版本优先使整个流程跑通；中间版本逐步约束安全边界、修正候选语义和加强证据链；后期加入可重复的浏览器与 Docker 验收，再用真实自部署应用暴露问题并修补。主线由“尽可能发现”逐步变为“在授权和预算内发现，并证明每项正式记录”。

三个特别重要的取舍：

- **V12** 不再把静态声明当作请求已发生；正式输出更保守，潜在召回损失不能忽略。
- **V16–V18** 逐跳检查、SSE 有界采样、受控登录重定向以安全与可复现为先，不追求任意业务交互覆盖。
- **PR #2** 将真实站点失败变成回归测试；Socket.IO 分类、静态过滤与懒加载分析改进证据质量，不虚报真实业务接口数量增加。

**仍未完成的验证：** 官方 S1–S5 隐藏站点总分、未知站点的可靠召回率与精确率、完整系统级文件访问及代理/DNS 审计。参见 [能力边界](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/CAPABILITIES_AND_LIMITS.md)。

若需要每次修改的具体文件与故障细节，继续阅读 [CHANGELOG](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/CHANGELOG.md) 和 [故障经验](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/FIXES_AND_LESSONS.md)，本篇不替代原始记录。
