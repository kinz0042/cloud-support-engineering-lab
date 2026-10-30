#!/bin/bash
exec > >(tee /var/log/cselab.log /dev/console) 2>&1
shutdown -h +20
: "${SERVICE_PRIVATE_IP:?Set the new lab service private IP before using this template}"
for n in $(seq 1 60); do
  text=$(curl --noproxy '*' --connect-timeout 2 --max-time 3 -fsS "http://${SERVICE_PRIVATE_IP}:8081/" 2>/dev/null)
  rc=$?
  echo "CSELAB_PROBE attempt=$n curl_exit=$rc body=$text"
  sleep 5
done
