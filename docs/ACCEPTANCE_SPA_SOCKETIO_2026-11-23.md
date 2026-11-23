# SPA Hash 路由发现与 Socket.IO 传输分类：真实双轮验收

> 记录日期：2026-11-23（Asia/Singapore）。本记录针对独立开发分支 `validation/juice-shop-selfhosted-20261123` 的实测；尚未合并到 `main`。不是考核组织方 S1–S5 隐藏站点结果。

## 修复动机与实现范围

1. **SPA 路由覆盖缺口**：旧链接采集丢弃 URL `#` 后的路由，无法通过页面已有的 `#/reports`、`#/search` 等锚点访问前端子页面。新实现只读取 `a[href]`、`a[routerlink]`、`a[ng-reflect-router-link]` 的属性，不点击未知按钮、不提交表单；允许有限的 `#/...` 客户端路由，并继续拒绝跨域、危险协议、`logout/delete/payment` 等路径及 query 操作。
2. **受控运行预算**：延续最多 200 个页面锚点采集检查、每页 24 个合格链接、48 个候选地址及最多 12 次浏览器导航。SPA hash 仅用于页面导航，不自行伪造 API 证据。
3. **Socket.IO 请求分类**：Engine.IO `EIO=<版本>&transport=polling` 的 GET/POST 与 `transport=websocket` 的 WS 握手是协议传输，不应描述为三条普通业务 REST 接口。新 `transport_semantics.py` 在真正观察到相应协议和 URL 查询字段后添加显式备注，保留原 HTTP 方法与对应 HAR。
4. **协议帧脱敏**：Socket.IO 轮询 POST 的消息体属于非表单协议帧，不能让 `parse_qsl` 误把整个消息体当作参数名。现在不从这类消息提取表单字段，也不从其帧体推断签名。只保留安全的 query 字段名与字段类型，不导出 `sid` 的值。
5. **静态资源不误报**：维持之前的 `GET fetch /assets/i18n/<语言>.json` 过滤，不影响普通 `/api/*.json`、POST 或 WebSocket。

## 针对性回归

- `tests/test_authenticated_navigation.py`：新增 SPA hash URL、普通 fragment、编码危险路径、退出登录与跨域路径等测试。
- `tests/fixtures/docker_smoke_site.py`：新增 `/spa-hash` 合成页面。只有浏览器真正访问 `#/reports`，才会触发 `GET /api/hash-report`；静态字符串不能直接通过验收。
- `scripts/ci_docker_smoke.sh`：新增 `spa_hash` 双轮浏览器场景，原 8 轮变成 **10 轮**；所有正式输出必须有真实 HAR 与 tool.log 请求对应记录。
- `tests/test_socketio_transport_semantics.py`：验证轮询 GET/POST、WebSocket 分类及不泄露原始协议帧、密钥、sid 和不误标普通 REST 请求。

## 已经获得的真实 GitHub Actions 证据

**同一代码提交：`45ca47da0d7cccff1c090784f05b087a5adee883`**

| 范围 | 运行与结果 |
|---|---|
| 完整仓库回归 | [GitHub Actions #45131303499](https://github.com/David-tiao/API/actions/runs/45131303499)：**259 passed**；两个作业均 completed/success |
| Docker/Chromium 合成 | 同一次 CI，Docker 构建 **28 秒**、镜像 **2,864,255,065 bytes**，SPA、SPA hash、SSR、SSE、登录 **5 类场景 × 2 次 = 10/10** 成功 |
| 越界合成接收端 | 同一 CI，未授权容器未收到被禁止的请求（合成检查通过） |
| Juice Shop 独立双轮 | [GitHub Actions #45131297364](https://github.com/David-tiao/API/actions/runs/45131297364)：两次均 completed，各 **9 条有 HAR 证据的记录**，Jaccard **1.0000**，每轮 Socket.IO 传输 **3/3** 被标注 |

Juice Shop 的 9 条记录中，3 条是 Socket.IO 传输（GET、POST、WS），另外 6 条是其他网络 API 类型记录；**不能把 9 条全部当作不同业务 REST API**。这次新增 SPA 导航没有让 Juice Shop 的观测数量超过之前的 9 条，因此暂不声明该站点的覆盖率提高；它在专门的独立 hash-route 合成场景中证明了功能有效。

## 未完成的正式验收

- 无组织方隐藏 S1–S5 真值，**不计算 Recall、Precision、总分或真实漏报数量**。
- 未对任意站点的复杂 SSO/MFA、主动表单操作或签名算法还原作保证。
- 代理/DNS egress 与文件系统审计尚未按最终考核机完整复现；禁止访问越界合成服务只是其中一部分。
- Juice Shop 使用**自己启动、无公网出口且无公开端口**的固定摘要镜像；从不对 OWASP 公共演示服务器运行扫描。
- 所有修复位于 GitHub PR #2，未合并到 `main`，需要审查后再决定是否合并。

## 复现入口

- 原全仓库 CI：`.github/workflows/quality-gate.yml`
- 原合成站点：`tests/fixtures/docker_smoke_site.py`
- Docker 双轮脚本：`scripts/ci_docker_smoke.sh`
- 独立 Juice Shop：`.github/workflows/owasp-juice-shop-lab.yml`、`scripts/ci_lab_juiceshop.sh`
- 前一轮浏览器关闭与静态资源误报记录：[ACCEPTANCE_JUICE_SHOP_2026-11-23.md](ACCEPTANCE_JUICE_SHOP_2026-11-23.md)
