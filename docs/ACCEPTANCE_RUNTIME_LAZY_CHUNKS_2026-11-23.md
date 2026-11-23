# S3 懒加载 JS Chunk：浏览器响应复用与静态证据分层

记录日期：2026-11-23（Asia/Singapore）

> 这是一项针对前端 API 提取工具的独立开发分支增量，并非官方 S1–S5 隐藏站点评分。代码位于 PR #2 的 `validation/juice-shop-selfhosted-20261123`，尚未合并到 `main`。

## 要修复的覆盖率缺口

原有静态爬虫能获取入口 HTML 脚本和静态推导的部分懒加载 chunk，但浏览器导航后动态创建的 `<script src="...">` 资源并没有统一返回给 AST 进行二次分析。结果是“页面确实加载了新 JS，却漏掉 chunk 中未执行的 API 声明”。这尤其会影响 S3 的登录后懒加载和其他 SPA 子路由。

## 改动

- `api_extractor/dynamic_analysis.py`：观察浏览器已经完成的 `resource_type=script` 响应，仅在授权 ScopeGuard 允许、状态成功且脚本类型/扩展名符合 JS 时缓存响应体，**不额外请求和重放**该 URL。
- 防资源耗尽：最多 32 个脚本、单个最多 2 MiB、总量最多 8 MiB；声明的 Content-Length 超限直接跳过，实际响应体再次检查；相同 URL 去重。
- 文件保存在 `/out/evidence/js/runtime-<内容哈希>.js`，保持可核查的本地源码证据。不是 `result.json` 的真实 HAR 请求证明。
- `api_extractor/pipeline.py`：动态浏览器阶段结束后，将这些 `ScriptRecord` 交给已有 `StaticAnalyzer`，复用现有 AST/regex，不把单纯静态候选提升为“运行时发生过的 API”。
- `tests/fixtures/docker_smoke_site.py`：新增仅在 `#/reports` 才加载的 `/assets/lazy-reports.js`。Chunk 内有 `fetch("/api/lazy-declared-only")` 的声明，但**从不调用**。
- `scripts/ci_docker_smoke.sh`：确保脚本实际被缓存、声明被 AST/regex 发现并出现在 `static_candidates.json`，同时断言未出现在 `result.json`。继续检查实际运行的 `GET /api/hash-report` 有 HAR 与 tool.log 请求证据。
- `tests/test_runtime_lazy_chunk_capture.py`：8 项新增单元测试，覆盖授权范围、缓存与证据、拒绝非 JS、异常 Content-Length、单文件和总大小上限、重复 URL 与不越界写入。

## 实际 GitHub 验收证据

代码提交 `09694f137ae3df4f9652e25c375c494efad4d6c3`：

- [完整仓库 CI #45132914193](https://github.com/David-tiao/API/actions/runs/45132914193)：**267 passed**；Docker 构建 **33 秒**，镜像 **2,864,258,700 字节**；SPA、SPA Hash、SSR、SSE、登录共 **10 次真实 Chromium 合成测试全部成功**，包括懒加载 JS 的静态候选与正式请求证据隔离检查。越界合成接收端零禁止请求。
- [独立 Juice Shop #45132904982](https://github.com/David-tiao/API/actions/runs/45132904982)：自部署 Docker 内网镜像，两次都运行完成，每次有 **9 条真实 HAR 支持的 API/传输记录**（其中 3 条 Socket.IO 传输），Jaccard **1.0000**，每轮 3/3 Socket.IO 标注。
- Juice Shop 的已验证记录数**没有增加**，因此不能据此宣称对 Juice Shop 的 Recall 提升；在专门合成站点中证明了懒加载脚本声明能被独立发现。隐藏考场完整覆盖率尚未知。

## 限制与后续工作

- 只有浏览器真正加载过的、在 8 MiB / 32 个脚本预算内的 JS 会参与本轮二次分析。
- 不自动点击危险按钮，不重放未知 POST，也不将静态源码声明当成访问成功。
- 运行期无外部模型/搜索调用；所有新增读取来自授权站点已加载的脚本。正式系统级 R7 文件访问和 R8 代理/DNS 审计仍待组织方等价环境验收。
- 文件属于独立 PR #2；在正式合并前，应再次确认最终文档提交 SHA 的全量 CI 成功。
