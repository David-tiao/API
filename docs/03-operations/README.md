# 03｜运行操作篇：命令行手册

> 本目录集中存放安装、启动、检查、测试和排错命令。只想了解项目而不执行命令，请阅读 [01 零基础篇](../01-overview/README.md)。以下命令以 Linux / Bash、仓库根目录为默认环境。
>
> **授权前提：** 只对自行部署或明确获授权的目标运行。准备好站点、配置和网络再执行扫描；不要把真实账号、Token、Cookie、HAR 或站点源码提交到公开仓库。下面使用本地练习地址和隔离合成环境。

## 1. 获取项目、检查环境

首次获取代码：

```bash
git clone https://github.com/David-tiao/API.git
cd API
```

已经克隆过且工作区无未保存改动时，使用：

```bash
git status
git switch main
git pull --ff-only origin main
```

检查基础依赖（本地模式需要 Python 3.11+、Node.js 和 npm；Docker 模式需要可用的 Docker Engine）：

```bash
python3 --version
node --version
npm --version
docker --version
docker info
bash scripts/diagnose_environment_stage10.sh check
```

诊断脚本默认不安装、不重启 Docker、不清理其他容器，但会在 out/operations/ 保存诊断资料。没有安装 Docker 时，本地 Python 模式仍可使用；Docker 相关检查可能报告不可用。

## 2. 安装依赖与离线自检

先阅读初始化脚本；确认信任仓库并允许安装依赖。第一次安装需要网络下载 Python/Node 包及 Chromium。

```bash
bash scripts/bootstrap_project_stage1_to_10.sh

.venv/bin/python -m pytest -q
.venv/bin/python -m api_extractor.cli --help
```

如需手动安装，可选择下面这一组代替初始化脚本（系统仍需满足 Chromium 运行库等前置要求）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --no-audit --no-fund
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest -q
```

## 3. 第一次扫描：本地 Python 模式

**前置条件：** 自己的练习站已经在宿主机 `127.0.0.1:3000` 监听。若尚无网站，优先执行第 6 节的隔离合成测试；下面的命令不负责启动目标站。

使用仓库示例配置，不修改真实站点或提交秘密：

```bash
mkdir -p out/local-practice
cp examples/site.example.json out/local-practice/site.json

API_EXTRACTOR_MODE=local bash scripts/start_extractor_stage8.sh \
  "http://127.0.0.1:3000/" \
  "./out/local-practice/site.json" \
  "./out/local-practice/result.json" \
  120
```

或者直接调用相同 CLI（二选一，不需要重复执行）：

```bash
.venv/bin/python -m api_extractor.cli \
  --target "http://127.0.0.1:3000/" \
  --config "./out/local-practice/site.json" \
  --out "./out/local-practice/result.json" \
  --budget 120
```

四个参数含义：target 为授权入口；config 为 JSON 配置；out 为结果文件；budget 为秒级任务预算。默认预算为 1200 秒。示例配置的 allowed_hosts 为 127.0.0.1，credentials 与 headers 默认为空。若改用自己的授权目标，必须同时核对实际目标地址、allowed_hosts 与网络。配置建议放在已被 Git 忽略的 out/ 或安全的私有位置。

## 4. Docker 方式：已有自己的练习容器

**前置条件：** 已经存在仅用于授权练习的 Docker 网络 practice-lab-net，自己的站点容器网络别名为 practice-web，端口为 3000。以下命令只展示如何运行扫描器，不启动站点；实际使用时用真实网络与服务名替换。容器中的 127.0.0.1 指向容器自身，不是宿主机。

```bash
docker build -t api-extractor:0.1.0 .
docker network inspect practice-lab-net
docker image inspect api-extractor:0.1.0 --format '{{.Size}}'
mkdir -p out/docker-practice

cat > out/docker-practice/site.json <<'JSON'
{
  "site_id": "docker-practice",
  "entry": "http://practice-web:3000/",
  "allowed_hosts": ["practice-web"],
  "credentials": [],
  "headers": {},
  "notes": "self-hosted authorized practice"
}
JSON

API_EXTRACTOR_NETWORK=practice-lab-net \
  bash scripts/start_safe_stage8.sh start \
  "http://practice-web:3000/" \
  "out/docker-practice/site.json" \
  "out/docker-practice/result.json" \
  120
```

查看和停止本项目自己的 Docker 任务（不要对无关容器操作）：

```bash
bash scripts/start_safe_stage8.sh status
bash scripts/start_safe_stage8.sh logs
bash scripts/start_safe_stage8.sh stop
```

任务是有限时间扫描，不是需要永久启动的 Web 服务。若已结束，不需要再次停止；如需重跑，先检查状态并选择新的独立输出目录。

正式评测形态的前台命令示例（同样需要已准备的网络、配置和目标；使用新输出目录）：

```bash
mkdir -p out/docker-run

docker run --rm --pull=never \
  --network practice-lab-net \
  --read-only --shm-size=512m \
  --user "$(id -u):$(id -g)" \
  -e HOME=/out/home -e TMPDIR=/out/tmp -e XDG_CACHE_HOME=/out/cache \
  -v "$PWD/out/docker-practice/site.json:/cfg/site.json:ro" \
  -v "$PWD/out/docker-run:/out" \
  api-extractor:0.1.0 \
  --target "http://practice-web:3000/" \
  --config /cfg/site.json \
  --out /out/result.json \
  --budget 120
```

网络应由操作者建立为符合实际授权和隔离要求的环境。此命令不保证官方代理/DNS/文件系统审计全部通过。

## 5. 查看结果和诊断运行状态

对应第 3 节的本地输出：

```bash
ls -lah out/local-practice
.venv/bin/python -m json.tool out/local-practice/result.json
.venv/bin/python -m json.tool out/local-practice/static_candidates.json
tail -n 12 out/local-practice/tool.log
grep 'run_status:' out/local-practice/tool.log
```

如果输出位置不同，请将上述路径一并修改。多次运行建议每轮使用新目录，避免旧证据干扰人工阅读。completed 表示流程结束；partial_browser_failure 或 incomplete_budget 表示部分结果；failed 表示致命失败。退出码 0 与 JSON 格式正确不等于完整接口覆盖。

## 6. 在自己机器上复现隔离合成验收

这是最推荐的无外部目标测试：脚本自行创建临时 Docker 内网和合成目标，不需要另找练习网站或填写真实账号。需要 Docker、宿主机 Python3 和 timeout。

```bash
docker build -t api-extractor-ci:latest .
bash scripts/ci_docker_smoke.sh api-extractor-ci:latest
```

该脚本原为 CI 设计，按 SPA、SPA Hash、SSR、SSE、模拟登录各两次运行。检查实际请求、Schema、HAR/日志证据、端点一致性以及越界合成接收端；只清理自己创建的容器与网络。结果以本次终端输出为准。历史证据：[主分支 CI](https://github.com/David-tiao/API/actions/runs/45140723425)。

### 6.1 自建 Juice Shop 独立双轮验证（可选）

此命令仅启动自行部署的内网靶场，不向公网发布端口。需要先完成镜像构建和下载（构建/下载阶段需要联网），实际测试在隔离网络运行。确保 Docker 资源充足。

```bash
docker build -t api-extractor-juice-lab:latest .
docker pull bkimminich/juice-shop@sha256:adaf6a6ca50f772dff7d2fe56972c659e81a61e0dbbe607c2b39fefd436e6153
GITHUB_WORKSPACE="$PWD/out/juice-shop" bash scripts/ci_lab_juiceshop.sh
cat out/juice-shop/lab-output/summary.json
```

脚本将去敏摘要保存至上述位置，临时环境由脚本清理。不要把 Juice Shop 公共演示站替换成扫描目标。历史双轮实测：[报告](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/ACCEPTANCE_RUNTIME_LAZY_CHUNKS_2026-11-23.md)。

### 6.2 对已有授权练习站执行两轮验收

满足第 4 节的网络、镜像和配置条件后：

```bash
API_EXTRACTOR_NETWORK=practice-lab-net \
  bash scripts/acceptance_stage10.sh \
  "http://practice-web:3000/" \
  "./out/docker-practice/site.json" \
  180
```

验收材料位于 out/acceptance/ 的本轮目录。该脚本的输出检查不是系统级安全审计；仍需人工核对运行状态、真实真值和证据。

## 7. 离线评分（必须提前准备独立真值）

评分器不访问网络。你需要为自己的练习站提供人工核实的 ground_truth.json，并准备两份独立实际运行目录。以下目录名为示例；它们需要真实存在，不能直接用空目录或不匹配的站点数据。

```bash
.venv/bin/python -m pytest -q \
  tests/test_offline_benchmark.py tests/test_benchmark_pipeline.py

.venv/bin/python -m api_extractor.offline_benchmark \
  --truth ./out/benchmark/ground_truth.json \
  --run-a ./out/benchmark/run-a \
  --run-b ./out/benchmark/run-b \
  --report ./out/benchmark/score.json
```

真值文件的最小结构示例（必须按自己的练习站实际接口填写，不能把示例当成真实真值）：

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

site 必须与两次运行结果一致；每个方法加归一化路径只能出现一次。完整历史格式说明见 [OFFLINE_BENCHMARK](https://github.com/David-tiao/API/blob/64e20a0f0d985ce78f29647e220ae88cec6122cb/docs/OFFLINE_BENCHMARK.md)，公式见 [算法篇](../02-technical/02-ALGORITHMS.md)。只有 Recall 40 与 Precision 20 的部分指标被计算；不能输出正式 100 分成绩。Jaccard 一致性也不是召回率。

## 8. 故障排查：先诊断，再做必要修复

```bash
bash scripts/diagnose_environment_stage10.sh check
bash scripts/diagnose_environment_stage10.sh env
bash scripts/diagnose_environment_stage10.sh deps
bash scripts/diagnose_environment_stage10.sh report
bash scripts/diagnose_environment_stage10.sh logs
```

如果明确需要重新构建或测试现有镜像，可分别执行：

```bash
bash scripts/diagnose_environment_stage10.sh build
bash scripts/diagnose_environment_stage10.sh test
```

| 症状 | 优先检查 |
|---|---|
| 找不到 Python/Node/Chromium | 基础依赖、初始化脚本输出、系统运行库 |
| Docker 无法使用 | Docker daemon 与当前用户权限；不要擅自重启全局服务 |
| 容器访问不到网站 | 容器网络、服务别名、端口、allowed_hosts；宿主机回环地址不等于容器回环 |
| 结果为零 | 目标是否响应、本轮状态、是否实际触发 API、授权范围是否正确 |
| 有静态候选但没有正式结果 | 查看本次 HAR 和日志；不能把候选手工冒充真实请求 |
| 预算耗尽 | 检查日志中耗时阶段；根据授权和实际任务合理设定预算 |

专门的 apt / 浏览器修复脚本可能改变环境；先读脚本和 [脚本说明](../../scripts/README.md)，确认必要性后再执行，不要盲目使用 sudo 或清理其他容器。

## 9. 常用入口速查

| 需求 | 查看位置 |
|---|---|
| CLI 参数 | 第 3 节 |
| 本地依赖 | 第 2 节 |
| Docker 生命周期 | 第 4 节 |
| 阅读结果 | 第 5 节 |
| 合成站及 Juice Shop 实测 | 第 6 节 |
| 本地评分 | 第 7 节 |
| 环境排错 | 第 8 节 |

返回 [文档总导航](../README.md) · [零基础篇](../01-overview/README.md) · [专业篇](../02-technical/README.md)。
