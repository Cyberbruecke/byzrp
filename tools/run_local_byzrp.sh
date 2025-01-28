#!/usr/bin/env bash

if [ -z "$1" ]; then
    N=1
else
    N="$1"
fi

IMG=byzrp
DATE=$(date +%Y-%m-%d_%H-%M)
echo "preparing run_$DATE"
mkdir run_$DATE
cd run_$DATE
echo "generating root keypair"
./../gen_root_cert.sh > /dev/null 2> /dev/null

echo "creating peers.lst"
for ((i=1; i<=N; i++)); do
    IP="172.17.0.$(echo $i + 1 | bc)"
    printf "$IP\n" >> peers.lst
done

for ((i=1; i<=N; i++)); do
    IP="172.17.0.$(echo $i + 1 | bc)"
    echo "generating $IP keypair"
    ./../gen_cert.sh $IP > /dev/null 2> /dev/null
    cp $IP.crt $IP.rtr.crt
    cp $IP.key $IP.rtr.key
    echo "running byz$i"
    docker run -d --rm -v $PWD/$IP.crt:/etc/ssl/certs/server.crt -v $PWD/$IP.rtr.crt:/etc/ssl/certs/rtr.crt -v $PWD/$IP.key:/etc/ssl/private/server.key -v $PWD/$IP.rtr.key:/etc/ssl/private/rtr.key -v $PWD/root.crt:/etc/ssl/certs/root.crt -v $PWD/peers.lst:/data/out/share/peers.lst -e "PEER_DISCOVERY=0" --name byz$i $IMG #> /dev/null 2> /dev/null
    echo "adding $IP to peer.lst"
done

echo ""
docker ps
NAMES=$(docker ps --format '{{.Names}}' | egrep ^byz | xargs)

printf "\n\nto log docker stats:\ncd run_$DATE && ./../log_docker_stats.sh\n"
printf "\nto stop containers and save logs:\n(for name in $NAMES; do docker logs \$name > \$name.log 2>&1 && echo \$name.log; done;) && docker stop $NAMES\n\n"
