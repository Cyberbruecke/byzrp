from time import time as timestamp

from scapy.layers.dns import DNS, DNSRR, DNSQR
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6
from scapy.sendrecv import sniff

from utils import write_json, get_host_ip
from vars import F_BL_DNSBOOK, F_BL_CONN_STATE, SNIFF_IFACE

dnsbook = {}
conn_listing = {}
self_ip = ""


def dns_tracking(pkt):
    try:
        if pkt[DNS].qr == 1 and pkt[DNS].rcode == 0:
            qn = pkt[DNSQR].qname.decode("utf-8")
            for i in range(pkt[DNS].ancount):
                if DNSRR in pkt and (pkt[DNSRR][i].type == 1 or pkt[DNSRR][i].type == 28):
                    dnsbook[pkt[DNSRR][i].rdata] = qn
        write_json(dnsbook, F_BL_DNSBOOK)
    except:
        pass


def conns_processing(pkt):
    # 1 is F, 2 is S, 4 is R, 17 is FA, 18 is SA, 20 is RA, 16 is A, 24 is PA, 25 is FPA

    IPvX = IP if IP in pkt else (IPv6 if IPv6 in pkt else None)
    if IPvX:

        if (pkt[IPvX].dst == self_ip and pkt[TCP].dport in (443, 80, 8282)) or (pkt[IPvX].src == self_ip and pkt[TCP].sport in (443, 80, 8282)):
            # ignore peer and RTR communication
            return

        match pkt[TCP].flags.value:
            case 2:
                conn_listing.setdefault(pkt[IPvX].dst, {"start_time": timestamp(), "established": False, "end_time": None})

            case 18:
                conn_listing.setdefault(pkt[IPvX].src, {"start_time": timestamp(), "established": False, "end_time": None})
                conn_listing[pkt[IPvX].src]["established"] = True

            case v if v in [1, 4, 17, 20]:
                conn_listing.get(pkt[IPvX].src, {})["end_time"] = timestamp()
                conn_listing.get(pkt[IPvX].dst, {})["end_time"] = timestamp()

    write_json(conn_listing, F_BL_CONN_STATE)


def pkt_processing(pkt):
    if pkt.haslayer(UDP):
        dns_tracking(pkt)
    elif pkt.haslayer(TCP):
        conns_processing(pkt)


def pkt_sniffer(iface, filter):
    sniff(filter=filter, iface=iface, prn=pkt_processing, store=False)


if __name__ == "__main__":
    self_ip = get_host_ip()
    pkt_sniffer(SNIFF_IFACE, "udp port 53 or tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-rst) != 0")
