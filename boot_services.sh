#!/bin/bash

ln -sf /proc/1/fd/1 /dev/stdout
ln -sf /proc/1/fd/2 /dev/stderr

python3 /app/vars.py &
python3 /app/ip_reader.py &
nginx -t && service nginx start
/prometheus/prometheus --config.file=/prometheus/prometheus.yml &
/node_exporter/node_exporter --collector.textfile.directory=/node_exporter/ &
stayrtr -bind '' -tls.bind 0.0.0.0:8282 -tls.key $F_RTR_KEY -tls.cert $F_RTR_CRT -cache http://localhost/$N_MASTER_VRP -refresh $RTR_REFRESH &
python3 -u /app/monitored_rp.py &
python3 -u /app/peering.py &

wait
