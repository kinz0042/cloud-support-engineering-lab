#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/cselab-app.log /dev/console) 2>&1
shutdown -h +30
trap 'echo "CSELAB_APP_FAILED line=$LINENO"' ERR
dnf install -y docker
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins /opt/cselab
cd /tmp
compose_version=v5.6.1
curl -fsSL --retry 2 --max-time 90 "https://github.com/docker/compose/releases/download/${compose_version}/docker-compose-linux-x86_64" -o docker-compose-linux-x86_64
curl -fsSL --retry 2 --max-time 90 "https://github.com/docker/compose/releases/download/${compose_version}/checksums.txt" -o checksums.txt
awk '$2 ~ /(^|\/|\*)docker-compose-linux-x86_64$/ {print $1 "  docker-compose-linux-x86_64"}' checksums.txt > selected-checksum.txt
if ! test -s selected-checksum.txt; then head -n 4 checksums.txt; exit 1; fi
sha256sum -c selected-checksum.txt
install -m 0755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
source_revision=837c5a86a92b5fa23c055eb5a1554737ef138189
curl -fsSL --retry 2 --max-time 90 "https://codeload.github.com/kinz0042/cloud-support-engineering-lab/tar.gz/${source_revision}" -o /tmp/source.tar.gz
tar -xzf /tmp/source.tar.gz --strip-components=1 -C /opt/cselab
cd /opt/cselab
export DOCKER_BUILDKIT=0
docker build -t cselab:local .
cat > compose.ec2.yaml <<'EOF'
services:
  api:
    image: cselab:local
  worker:
    image: cselab:local
  partner:
    image: cselab:local
EOF
export COMPOSE_FILE=compose.yaml:compose.ec2.yaml
trap 'rc=$?; docker compose down -v || true; if [ "$rc" -ne 0 ]; then echo CSELAB_APP_FAILED; fi' EXIT
docker compose up -d --no-build
python3 scripts/compose_smoke.py
echo CSELAB_APP_SMOKE_PASSED
docker compose logs --no-color --tail=8 api worker partner
docker compose down -v
echo "CSELAB_SOURCE_REVISION=$source_revision"
docker --version
docker compose version
echo CSELAB_APP_PASS
