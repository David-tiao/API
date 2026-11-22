# V15：同一 GitHub 提交的完整 CI 与隔离 Docker 验收

**日期**：2026-11-22。**类型**：验收基础设施，不修改生产扫描策略。此文档在 CI 首次执行前创建；“设计的检查”不等于“已经运行通过”。

## 验收目标和可运行入口

- 质量门禁：[.github/workflows/quality-gate.yml](../.github/workflows/quality-gate.yml)，推送 `main`（有源码/依赖/工作流变化）时自动执行，也可在 GitHub Actions 手动触发。
- 合成模拟站：[tests/fixtures/docker_smoke_site.py](../tests/fixtures/docker_smoke_site.py)。仅返回自造的 HTML、JS 和 JSON：根页面加载 `/app.js`，浏览器 JS 必须真实调用 `GET /api/items`。
- Docker 验收脚本：[scripts/ci_docker_smoke.sh](../scripts/ci_docker_smoke.sh)，默认镜像名 `api-extractor-ci:latest`，需要本机 Docker，不会主动安装或删除用户的其他镜像/容器。

## 两阶段质量门禁

| 阶段 | 具体检查 | V15 初次提交时状态 |
|---|---|---|
| 独立离线测试 | GitHub 精确 checkout、Python 3.13 / Node 22、固定顶层依赖、npm ci、全部 pytest、Python/Bash/Node 语法、忽略规则核验 | **待 GitHub Actions 实测** |
| 容器构建 | 原 Dockerfile，`timeout 900s`，镜像不超过 6GiB | **待实测** |
| R1/R2/R6 合成站点 | 内部 Docker 网络、只读根 FS、真实 Chromium 页面触发 `/api/items`，输出非空合法 JSON、真实日志与 HAR 证据 | **待实测** |
| 双轮稳定性 | 两次独立容器与 `/out`，接口 Method/Host/Path 集合一致 | **待实测** |
| R4/R5/R7/R8 代理级审计 | 使用组织方真实环境的 TCP/HTTP 代理、文件访问监视和未知站点 | **本轮不执行，未通过正式审计** |
| S1～S5 隐藏站点评分 | 使用真实 ground truth 对照 Recall、Precision、语义与重放率 | **未执行** |

## 已实际运行的本地检查

1. 通过 Python 3.13.5 在本机启动合成服务，依次请求 `/`、`/app.js`、`/api/items`，响应均为预期的 200，JSON 字段可解析。
2. 执行 `python -m pytest -q -o addopts='' tests/test_docker_smoke_fixture.py`，**1 passed**。
3. 执行 Bash 语法、Python 编译检查与 workflow YAML 结构解析，均通过。
4. 本地工具无 Docker daemon，不能据此写入 Docker PASS；也无法通过普通 `git clone` 从当前环境直接取得远程完整仓库。

## R1～R8 真实验收界限

合成 Docker 用例可以在成功执行后增强 R1、R2、R3、R6、部分 R7/R8 的信心，但不能证明官方隐藏站点已通过。internal-only 网络限制该测试容器的外联；无法替代官方代理抓包和系统级文件读写审计。浏览器请求日志与 HAR 内容一致也不能保证跨会话接口业务语义与可重放性。

**保密事项未结束**：仓库仍为公开状态，历史对象仍可能暴露旧内部资料；请先 Private，之后使用仓库所有者的授权 Git 工具执行敏感历史清理，联系 GitHub Support 处理缓存。在此之前，不应把包含任何正式靶场凭据、内部细则或成绩的文件及测试日志上传到此仓库。

## 下一步记录

只有 GitHub Actions 已返回真实 run 状态和日志后，才能把上表从“待实测”改为 PASS/FAIL。若失败，按具体步骤、行号及工具退出码修复，严禁仅修改断言掩盖问题。所有后续修复继续写入 [CHANGELOG.md](CHANGELOG.md)。
