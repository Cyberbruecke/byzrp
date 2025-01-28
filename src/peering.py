import json
import os
import re
from datetime import datetime
from math import ceil
from time import sleep, time
from typing import Set, Iterable

import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError, JSONDecodeError, SSLError, RequestException

from utils import write_lines, write_json, read_lines, log, get_host_ip, RPKI_OBJTYPES, write_metrics
from vars import PEER_DISCOVERY, F_PEER_LIST, CONSENSUS, F_MASTER_VRP, F_MASTER_SKIPLIST, N_VRP, N_SKIPLIST, F_ROOT_CRT, F_SERVER_KEY, F_SERVER_CRT, F_PEER_CANDIDATES, \
    PEER_TIMEOUT, PEER_POLL_INTERVAL, N_PEER_LIST, PEER_RETRIES, F_BYZRP_METRICS, INIT_PEERING_DELAY

cons_threshold = 1
peers = set()
last_modified = {}
current_vrps = {}
current_skiplists = {}
localhosts = {"localhost", "127.0.0.1", "172.17.0.1"}
metrics = {metric: 0 for metric in RPKI_OBJTYPES +
                                   [f"union_{objtype}" for objtype in RPKI_OBJTYPES] +
                                   [f"intersection_{objtype}" for objtype in RPKI_OBJTYPES] +
                                   [f"consensus_{objtype}" for objtype in RPKI_OBJTYPES] +
                                   ["all_obj", "union_all_obj", "intersection_all_obj", "consensus_all_obj"] +
                                   ["peers", "skiplisted", "union_skiplisted", "consensus_skiplisted"]}
metrics["consensus_threshold"] = cons_threshold


def main():
    global peers, cons_threshold

    last_round_start = (int(time() / 60) + 1) * 60 + INIT_PEERING_DELAY
    log(__file__, "running")
    while True:
        while time() < last_round_start + PEER_POLL_INTERVAL:
            sleep(0.5)
        last_round_start += PEER_POLL_INTERVAL

        if PEER_DISCOVERY:
            peers = peers.union(discover_peers(peers.union(read_peer_req_ips())))
            write_lines(peers, filename=F_PEER_LIST)
            cons_threshold = ceil(CONSENSUS * len(peers))
            metrics["consensus_threshold"] = cons_threshold

        current_vrps.update(fetch_from_peers(peers, resource=N_VRP, is_json=True))
        master_vrp = aggregate_master_vrp(current_vrps)
        write_json(master_vrp, filename=F_MASTER_VRP)

        current_skiplists.update(fetch_from_peers(peers, resource=N_SKIPLIST, is_json=False))
        master_skiplist = aggregate_master_skiplist(current_skiplists)
        write_lines(master_skiplist, filename=F_MASTER_SKIPLIST)

        write_metrics(metrics, F_BYZRP_METRICS)


def fetch_from_peers(peer_addrs: Iterable[str], resource: str, is_json: bool = False) -> dict:
    output = {}
    for peer_addr in peer_addrs:
        url = f"https://{peer_addr}/{resource}"

        for retry in range(PEER_RETRIES):
            try:
                headers = {"User-Agent": "ByzRP Peer"}
                try:
                    headers["If-Modified-Since"] = last_modified[peer_addr][resource]
                except KeyError:
                    pass

                r = requests.get(url, headers=headers, timeout=PEER_TIMEOUT, verify=F_ROOT_CRT, cert=(F_SERVER_CRT, F_SERVER_KEY))
                r.raise_for_status()

                if r.status_code == 304:
                    log(__file__, f"{url} unmodified{f' (retry {retry})' if retry else ''}")
                else:
                    output[peer_addr] = r.json() if is_json else {line.strip() for line in r.text.split("\n") if line.strip() != ""}
                    log(__file__, f"fetched {url}{f' (retry {retry})' if retry else ''}")

                    if r.headers.get("Last-Modified"):
                        last_modified.setdefault(peer_addr, {})
                        last_modified[peer_addr][resource] = r.headers.get("Last-Modified")
                break

            except (Timeout, ConnectionError, SSLError, HTTPError, RequestException, JSONDecodeError) as e:
                err_class = re.search("<class '(.*?)'>", str(e.__class__)).group(1)
                log(__file__, f"{err_class} fetching {url}{f' (retry {retry})' if retry else ''} - {e}")
                if isinstance(e, JSONDecodeError):
                    sleep(2)
    return output


def aggregate_master_vrp(peer_vrps: dict) -> dict:
    vote = {objtype: {} for objtype in RPKI_OBJTYPES}

    for peer, vrp in peer_vrps.items():
        for objtype in RPKI_OBJTYPES:
            for entry_str in {json.dumps(entry, sort_keys=True) for entry in vrp.get(objtype, [])}:
                vote[objtype][entry_str] = vote[objtype].get(entry_str, 0) + 1

    master_vrp = {"metadata": {"buildtime": datetime.now().astimezone().isoformat()}}
    master_vrp.update({objtype: [json.loads(entry_str) for entry_str, votes in entries.items() if votes >= cons_threshold] for objtype, entries in vote.items()})

    metrics.update({f"{obtype}": len(entries) for obtype, entries in peer_vrps.get(self_ip, {}).items()})
    metrics.update({f"union_{obtype}": len(entries) for obtype, entries in vote.items()})
    metrics.update({f"consensus_{objtype}": sum(votes >= cons_threshold for votes in entries.values()) for objtype, entries in vote.items()})
    metrics.update({f"intersection_{objtype}": sum(votes >= len(peers) for votes in entries.values()) for objtype, entries in vote.items()})
    metrics.update({f"consensus_all_obj": sum(metrics[f"consensus_{objtype}"] for objtype in RPKI_OBJTYPES),
                    f"union_all_obj": sum(metrics[f"union_{objtype}"] for objtype in RPKI_OBJTYPES),
                    f"intersection_all_obj": sum(metrics[f"intersection_{objtype}"] for objtype in RPKI_OBJTYPES)})
    for objtype in RPKI_OBJTYPES + ["all_obj"]:
        log(__file__, f"updated master VRP (found {metrics[f'union_{objtype}']} unique entries ({objtype}) among peers, {metrics[f'consensus_{objtype}']} with {cons_threshold}+ votes)")

    return master_vrp


def aggregate_master_skiplist(peer_skiplists: dict) -> Set[str]:
    vote = {}
    for peer, skiplist in peer_skiplists.items():
        for domain in set(skiplist):
            vote[domain] = vote.get(domain, 0) + 1
    master_list = {domain for domain, votes in vote.items() if votes >= cons_threshold}

    metrics["skiplisted"] = len(set(peer_skiplists.get(self_ip, [])))
    metrics["union_skiplisted"] = len(vote)
    metrics["consensus_skiplisted"] = len(master_list)

    log(__file__, f"updated master skiplist (found {len(vote)} unique entries, {len(master_list)} with {cons_threshold}+ votes)")
    return master_list


def discover_peers(bootstrap_list: Set[str]) -> Set[str]:
    confirmed_peers = set()
    new_peers = {peer for peer in bootstrap_list}
    while new_peers:
        found_peers = {new_peer for peerlist in fetch_from_peers(new_peers - localhosts, N_PEER_LIST, is_json=False).values() for new_peer in peerlist} - localhosts
        confirmed_peers = confirmed_peers.union(new_peers.intersection(found_peers))
        new_peers = found_peers - confirmed_peers

    add_peers = confirmed_peers - peers
    if add_peers:
        metrics['peers'] = len(peers)
        log(__file__, f"added peers: {', '.join(add_peers)} ({metrics['peers']} active peers)")
    return add_peers


def read_peer_req_ips() -> Set[str]:
    try:
        req_ips = read_lines(F_PEER_CANDIDATES)
        F_PEER_CANDIDATES.unlink()
        return req_ips
    except FileNotFoundError:
        return set()


if __name__ == '__main__':
    host_ip = get_host_ip()
    self_ip = os.getenv("SELF_IP") or host_ip
    localhosts = localhosts.union({self_ip, host_ip})

    peers = set(read_lines(F_PEER_LIST)).union({self_ip})
    metrics['peers'] = len(peers)
    cons_threshold = ceil(CONSENSUS * len(peers))
    metrics["consensus_threshold"] = cons_threshold

    main()
