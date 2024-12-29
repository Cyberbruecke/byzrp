FROM ubuntu:latest
RUN apt update && apt upgrade -y && apt autoremove -y

#python
RUN apt install curl python3 python3-pip wget git gcc npm gnupg2 apt-transport-https software-properties-common supervisor -y

#vars
ENV PEER_DISCOVERY=1
ENV CONSENSUS=0.5
ENV VALIDATION_INTERVAL=60
ENV RP_POLL_INTERVAL=10
ENV RP_TIMEOUT=600
ENV BLACKLIST_EXPIRY=7200
ENV GLOBAL_TIMEOUT=3600
ENV PEER_TIMEOUT=10
ENV PEER_POLL_INTERVAL=10
ENV SNIFF_IFACE=eth0
ENV PEER_RETRIES=3
ENV STALLING_THRESHOLD=0.9
ENV RTR_REFRESH=30

ENV SELF_IP=""

ENV D_DATA=/data/
ENV D_IN=$D_DATA/in/
ENV D_OUT=$D_DATA/out/
ENV D_RP_OUT=$D_OUT/rpki-out/
ENV D_RP_CACHE=$D_OUT/rpki-cache/
ENV D_RP_TALS=$D_IN/rpki-tals/
ENV D_SHARE=$D_OUT/share/
ENV D_METRICS=$D_SHARE/metrics/
ENV D_CERTS=/etc/ssl/certs/
ENV D_KEYS=/etc/ssl/private/
ENV F_ROOT_CRT=$D_CERTS/root.crt
ENV F_SERVER_CRT=$D_CERTS/server.crt
ENV F_SERVER_KEY=$D_KEYS/server.key
ENV F_RTR_CRT=$D_CERTS/rtr.crt
ENV F_RTR_KEY=$D_KEYS/rtr.key
ENV N_VRP=vrp.json
ENV N_MASTER_VRP=master-vrp.json
ENV N_SKIPLIST=skiplist.lst
ENV N_MASTER_SKIPLIST=master-skiplist.lst
ENV N_PEER_LIST=peers.lst
ENV F_VRP=$D_SHARE/$N_VRP
ENV F_MASTER_VRP=$D_SHARE/$N_MASTER_VRP
ENV F_SKIPLIST=$D_SHARE/$N_SKIPLIST
ENV F_MASTER_SKIPLIST=$D_SHARE/$N_MASTER_SKIPLIST
ENV F_PEER_LIST=$D_SHARE/$N_PEER_LIST
ENV F_PEER_IP_LOG=/tmp/peer_ip_log
ENV F_PEER_CANDIDATES=/tmp/peer_candidates
ENV F_BL_DNSBOOK=/tmp/dnsbook.json
ENV F_BL_SKIPLIST_STATE=/tmp/skiplist_state.json
ENV F_BL_CONN_STATE=/tmp/conn_state.json

ENV PROMETHEUS_VERSION=3.0.1
ENV NODE_EXPORTER_VERSION=1.8.2

#init
RUN mkdir -p $D_RP_OUT $D_RP_CACHE $D_RP_TALS $D_SHARE $D_METRICS
RUN chmod 777 $D_RP_OUT
RUN ln -sf $D_RP_OUT/metrics $D_METRICS/rpki-client.metrics
RUN touch $F_SKIPLIST $F_MASTER_SKIPLIST && echo '{}' > $F_VRP && echo '{}' > $F_MASTER_VRP
RUN echo '{}' > $F_MASTER_VRP && echo '{}' > $F_VRP && echo '{}' > $F_BL_CONN_STATE && echo '{}' > $F_BL_DNSBOOK && echo '{}' > $F_BL_SKIPLIST_STATE && touch $F_MASTER_SKIPLIST

#stayrtr
COPY --from=rpki/stayrtr /stayrtr /bin/stayrtr

#rpki-client
RUN apt install -y curl rsync build-essential libssl-dev libtls-dev
RUN touch /etc/rsyncd.conf
RUN curl https://ftp.openbsd.org/pub/OpenBSD/rpki-client/$(curl https://ftp.openbsd.org/pub/OpenBSD/rpki-client/ | egrep -o "rpki-client-[0-9.]+.tar.gz" | tail -n 1) -o /root/rpki-client.tar.gz
RUN cd /root/ && tar -xzvf rpki-client.tar.gz && cd /root/rpki-client-* && ./configure --with-output-dir=$D_RP_OUT && make && rm /root/rpki-client.tar.gz
RUN useradd _rpki-client && passwd -d _rpki-client
RUN ln -s /root/rpki-client-*/src/rpki-client /bin/rpki-client
RUN cp /root/rpki-client-*/*.tal $D_RP_TALS
RUN chown -R _rpki-client:_rpki-client $D_RP_OUT $D_RP_TALS $D_RP_CACHE
RUN curl https://www.arin.net/resources/manage/rpki/arin.tal -o $D_RP_TALS/arin.tal
RUN touch /data/out/rpki-out/metrics && chmod 644 /data/out/rpki-out/*

#nginx
RUN apt install -y nginx gettext
COPY /nginx/stayrtr-proxy.conf.temp /tmp/stayrtr-proxy.conf.temp
COPY /nginx/peering.conf.temp /tmp/peering.conf.temp
RUN envsubst < /tmp/stayrtr-proxy.conf.temp > /etc/nginx/sites-enabled/stayrtr-proxy.conf && rm /tmp/stayrtr-proxy.conf.temp
RUN envsubst < /tmp/peering.conf.temp > /etc/nginx/sites-enabled/peering.conf && rm /tmp/peering.conf.temp
RUN ln -sf /dev/stdout /var/log/nginx/access.log && ln -sf /dev/stderr /var/log/nginx/error.log
RUN sed -i 's/user www-data;/user root;/' /etc/nginx/nginx.conf
RUN sed -i 's/http {/http {\n\tlog_format peer_ip_log '\$remote_addr';\n\taccess_log \/tmp\/peer_ip_log peer_ip_log;/' /etc/nginx/nginx.conf
RUN mkfifo $F_PEER_IP_LOG

# prometheus
RUN wget https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz \
    && tar -xvzf prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz \
    && mv prometheus-${PROMETHEUS_VERSION}.linux-amd64 /prometheus \
    && rm prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz
COPY prometheus/prometheus.yml /prometheus/prometheus.yml 
RUN chmod +x /prometheus/prometheus && chmod 644 /prometheus/prometheus.yml

# node_exporter
RUN wget https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz \
    && tar -xvzf node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz \
    && mv node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64 /node_exporter \
    && rm node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
RUN chmod +x /node_exporter/node_exporter
RUN ln -s /data/out/rpki-out/metrics /node_exporter/metrics.prom

#app
RUN apt install -y libpcap-dev lsof
COPY src/ /app/
RUN pip3 install --break-system-packages -r /app/requirements.txt
COPY boot_services.sh /boot_services.sh
RUN chmod +x /boot_services.sh


EXPOSE 8282
EXPOSE 9090
EXPOSE 9100
EXPOSE 443

CMD ["/boot_services.sh"]

