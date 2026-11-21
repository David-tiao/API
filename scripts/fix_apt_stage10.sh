#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Backing up Dockerfile..."
cp Dockerfile Dockerfile.backup

echo "[2/4] Configuring Debian mirrors..."

python3 - <<'PY'
from pathlib import Path

path = Path("Dockerfile")
content = path.read_text()

marker = "RUN python -m pip install --upgrade pip"

mirror_config = r"""RUN set -eux; \
    sed -i \
      -e 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
      -e 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' \
      -e 's|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' \
      /etc/apt/sources.list.d/debian.sources; \
    printf 'Acquire::Retries "5";\nAcquire::https::Timeout "45";\n' \
      > /etc/apt/apt.conf.d/80retry; \
    apt-get update

"""

if "mirrors.tuna.tsinghua.edu.cn" in content:
    print("Mirror configuration already exists.")
elif marker in content:
    content = content.replace(
        marker,
        mirror_config + marker,
        1
    )
    path.write_text(content)
    print("Dockerfile updated.")
else:
    raise SystemExit(
        "Cannot locate Python installation stage."
    )
PY

echo "[3/4] Building Docker image..."
docker build -t api-extractor:0.1.0 .

echo "[4/4] Checking CLI..."
docker run --rm --pull=never \
  api-extractor:0.1.0 --help

echo "Build and CLI check completed."
