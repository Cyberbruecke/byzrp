from datetime import datetime

import psutil

from utils import write_json, write_lines, read_json, log
from vars import GLOBAL_TIMEOUT, BLACKLIST_EXPIRY, F_BL_SKIPLIST_STATE, F_SKIPLIST, F_BL_DNSBOOK, F_BL_CONN_STATE, STALLING_THRESHOLD

CONN_TO = STALLING_THRESHOLD * GLOBAL_TIMEOUT / 4


def find_pid(proc_name):
    pids = []
    for proc in psutil.process_iter():
        if len(proc.cmdline()) > 1:
            if proc_name in proc.cmdline()[1]:
                pids.append(proc.pid)
    return pids


def update_skiplist(anomalous):
    bl = read_json(F_BL_SKIPLIST_STATE)
    expire = datetime.timestamp(datetime.now())
    n_expired = 0

    for k, v in bl.items():
        if expire - v >= BLACKLIST_EXPIRY:
            del bl[k]
            n_expired += 1

    for a in anomalous:
        bl[a] = datetime.timestamp(datetime.now())

    write_json(bl, F_BL_SKIPLIST_STATE)
    write_lines([*bl], F_SKIPLIST)
    if n_expired != 0 or len(anomalous) != 0:
        log(__file__, f"skiplist updated: {n_expired} expired, {len(anomalous)} added, {len(bl)} current entries")


def stalling_detection(start):
    anomalous = []
    dnsbook = read_json(F_BL_DNSBOOK)
    connections = read_json(F_BL_CONN_STATE)

    for k in connections.keys():
        if connections[k]["end_time"] is None and connections[k]["established"]:
            if start - connections[k]["start_time"] >= CONN_TO:
                if dnsbook.get(k):
                    anomalous.append(dnsbook[k])
                    log(__file__, f"RP stalled on {dnsbook[k]}")
    return anomalous


def crash_detection():
    anomalous = []
    dnsbook = read_json(F_BL_DNSBOOK)
    connections = read_json(F_BL_CONN_STATE)

    for k in connections.keys():
        if connections[k]["end_time"] is None and connections[k]["established"]:
            if dnsbook.get(k):
                anomalous.append(dnsbook[k])
                log(__file__, f"RP crashed on {dnsbook[k]}")
    return anomalous
