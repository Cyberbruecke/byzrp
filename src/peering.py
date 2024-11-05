import json
import os
import re
from datetime import datetime
from math import floor
from time import sleep
from typing import Set, Iterable

import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError, JSONDecodeError, SSLError, RequestException

from utils import write_lines, write_json, read_lines, log, get_host_ip, RPKI_OBJTYPES
from vars import PEER_DISCOVERY, F_PEER_LIST, CONSENSUS, F_MASTER_VRP, F_MASTER_SKIPLIST, N_VRP, N_SKIPLIST, F_ROOT_CRT, F_SERVER_KEY, F_SERVER_CRT, F_PEER_CANDIDATES, \
    PEER_TIMEOUT, PEER_POLL_INTERVAL, N_PEER_LIST, PEER_RETRIES

cons_threshold = 1
peers = set()
last_modified = {}
current_vrps = {}
current_skiplists = {}
self_ips = {"localhost", "127.0.0.1", "172.17.0.1"}


def main():
    global peers, cons_threshold

    log(__file__, "running")
    while True:
        sleep(PEER_POLL_INTERVAL)

        if PEER_DISCOVERY:
            peers = peers.union(discover_peers(peers.union(read_peer_req_ips()))) - self_ips
            write_lines(peers, filename=F_PEER_LIST)
            cons_threshold = floor(CONSENSUS * len(peers)) + 1

        current_vrps.update(fetch_from_peers(peers, resource=N_VRP, is_json=True))
        master_vrp = aggregate_master_vrp(current_vrps)
        write_json(master_vrp, filename=F_MASTER_VRP)

        current_skiplists.update(fetch_from_peers(peers, resource=N_SKIPLIST, is_json=False))
        master_skiplist = aggregate_master_skiplist(current_skiplists)
        write_lines(master_skiplist, filename=F_MASTER_SKIPLIST)


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
                    output[peer_addr] = current_vrps[peer_addr]
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
            for entry_str in {json.dumps(entry) for entry in vrp.get(objtype, [])}:
                vote[objtype][entry_str] = vote[objtype].get(entry_str, 0) + 1

    master_vrp = {"metadata": {"buildtime": datetime.now().astimezone().isoformat()}}
    master_vrp.update({objtype: [json.loads(entry_str) for entry_str, votes in entries.items() if votes >= cons_threshold] for objtype, entries in vote.items()})
    n_uniq_entries = sum(len(entries) for entries in vote.values())
    n_cons_entries = sum(votes >= cons_threshold for entries in vote.values() for votes in entries.values())
    log(__file__, f"updated master VRP (found {n_uniq_entries} unique entries among peers, {n_cons_entries} with {cons_threshold}+ votes)")
    return master_vrp


def aggregate_master_skiplist(peer_skiplists: dict) -> Set[str]:
    vote = {}
    for peer, skiplist in peer_skiplists.items():
        for domain in set(skiplist):
            vote[domain] = vote.get(domain, 0) + 1
    master_list = {domain for domain, votes in vote.items() if votes >= cons_threshold}
    log(__file__, f"updated master skiplist (found {len(vote)} unique entries, {len(master_list)} with {cons_threshold}+ votes)")
    return master_list


def discover_peers(bootstrap_list: Set[str]) -> Set[str]:
    confirmed_peers = set()
    new_peers = {peer for peer in bootstrap_list}
    while new_peers:
        found_peers = {new_peer for peerlist in fetch_from_peers(new_peers - self_ips, N_PEER_LIST, is_json=False).values() for new_peer in peerlist} - self_ips
        confirmed_peers = confirmed_peers.union(new_peers.intersection(found_peers))
        new_peers = found_peers - confirmed_peers

    add_peers = confirmed_peers - peers
    if add_peers:
        log(__file__, f"added peers: {', '.join(add_peers)}")
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
    self_ips = self_ips.union({self_ip, host_ip})
    peers = set(read_lines(F_PEER_LIST)).union({self_ip})
    main()
