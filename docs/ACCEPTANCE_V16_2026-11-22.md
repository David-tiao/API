# V16：SSR 与异域重定向负向验收

**基准**：V15 的精确 GitHub 提交已经通过 137 项 pytest、Docker 构建、双轮合成 SPA。V16 增加真正的 SSR/form 与未授权 Host 接收端安全验证。

## 预期行为

| 环节 | 必须观测 | 不允许发生 |
|---|---|---|
| SPA `/` | `GET /api/items`，本轮日志、HAR 与 JSON Schema 有效 | 静态 API 当作已请求 |
| SSR `/ssr` | `GET /api/ssr-items` 真正观察成功；表单在 `static_candidates.json` 中保留 | 自动提交 `POST /api/submit` 或将其输出为真实 API |
| SSR 图片 | 浏览器截获 `http://offscope:8765/forbidden-resource` | 未授权容器实际收到该请求 |
| SSR 302 | 可以请求 `fixture` 的首跳 | 未授权容器收到 `/forbidden-redirect` |
| 独立运行 | SPA/SSR 各两轮，分别真实启动 Chromium，并对每轮 Schema 与 HAR/日志交叉核查 | 空接口列表或只靠内部日志自证 |
| R5 额外单测 | 4 项跨域、同域、带凭据、循环的 HTTPX 模拟 | 继续访问无权 Host |

## 执行记录（创建时）

- 已执行：Python 3.13 环境下新 fixture 的 **3 项真实本地 loopback HTTP 测试通过**；`python -m compileall` 和 `bash -n` 通过。
- GitHub 最新完整 checkout 及四轮 Docker 的结果：**待 CI 返回后追加**。不能从 V15 结果推导 V16 已通过。
- 安全：网络仅包含自己构造的两个合成服务，无公网目标、实际账号或内部评测资料。

## 尚未覆盖

实际代理、DNS 重绑定、复杂认证/签名、SSE/WS/GraphQL 的真实站点行为、S1～S5 隐藏基准、系统级文件读写审计、历史内部资料清除。当前仍为公开仓库，完整隐私历史清理是独立未完成任务。


## 首次 Docker 执行结果：真实越界，已修复待复测

[GitHub Actions V16 首轮](https://github.com/David-tiao/API/actions/runs/45017092637)：精确 checkout **143 passed**，Docker **33 秒**，镜像 **2,864,047,980 字节**；两轮 SPA 与两轮 SSR 均输出预期 GET，并经过独立 Schema/HAR/日志验证，未提交未知 POST；但 `offscope` 服务端接收到两次 `GET /forbidden-redirect`，说明浏览器 302 重定向**突破 R5**，总体 **FAIL**。

当前提交针对根因加入禁用自动重定向、逐跳作用域/限速检查和七项路由单元测试。**是否修复成功仍须后续 GitHub Actions 真实运行确认**，不得凭代码提交直接判定 PASS。已知 SSE、巨大资源、跨协议或 POST 重定向可能受到保守处理影响。
