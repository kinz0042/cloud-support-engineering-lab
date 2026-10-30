#!/bin/bash
exec > >(tee /var/log/cselab.log /dev/console) 2>&1
shutdown -h +20
mkdir -p /tmp/cselab
printf 'synthetic-network-ok\n' > /tmp/cselab/index.html
cd /tmp/cselab
python3 -m http.server 8081 --bind 0.0.0.0 >/tmp/cselab-server.log 2>&1 &
sleep 3
curl --noproxy '*' --max-time 3 http://127.0.0.1:8081/
echo CSELAB_SERVICE_READY
