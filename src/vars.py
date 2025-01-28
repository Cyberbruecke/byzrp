import os
from pathlib import Path

try:
    D_RP_OUT = Path(os.environ["D_RP_OUT"])
    D_RP_CACHE = Path(os.environ["D_RP_CACHE"])
    TALS = list(Path(os.environ["D_RP_TALS"]).glob("*.tal"))
    D_CERTS = Path(os.environ["D_CERTS"])
    D_KEYS = Path(os.environ["D_KEYS"])
    F_SERVER_CRT = Path(os.environ["F_SERVER_CRT"])
    F_ROOT_CRT = Path(os.environ["F_ROOT_CRT"])
    F_SERVER_KEY = Path(os.environ["F_SERVER_KEY"])
    F_VRP = Path(os.environ["F_VRP"])
    N_VRP = Path(os.environ["N_VRP"])
    N_MASTER_VRP = Path(os.environ["N_MASTER_VRP"])
    N_SKIPLIST = Path(os.environ["N_SKIPLIST"])
    N_MASTER_SKIPLIST = Path(os.environ["N_MASTER_SKIPLIST"])
    N_PEER_LIST = Path(os.environ["N_PEER_LIST"])
    F_MASTER_VRP = Path(os.environ["F_MASTER_VRP"])
    F_SKIPLIST = Path(os.environ["F_SKIPLIST"])
    F_MASTER_SKIPLIST = Path(os.environ["F_MASTER_SKIPLIST"])
    F_PEER_LIST = Path(os.environ["F_PEER_LIST"])
    F_PEER_IP_LOG = Path(os.environ["F_PEER_IP_LOG"])
    F_PEER_CANDIDATES = Path(os.environ["F_PEER_CANDIDATES"])
    F_BL_DNSBOOK = Path(os.environ["F_BL_DNSBOOK"])
    F_BL_SKIPLIST_STATE = Path(os.environ["F_BL_SKIPLIST_STATE"])
    F_BL_CONN_STATE = Path(os.environ["F_BL_CONN_STATE"])
    F_BYZRP_METRICS = Path(os.environ["F_BYZRP_METRICS"])

    CONSENSUS = float(os.environ["CONSENSUS"])
    PEER_DISCOVERY = bool(int(os.environ["PEER_DISCOVERY"]))
    VALIDATION_INTERVAL = int(os.environ["VALIDATION_INTERVAL"])
    RP_POLL_INTERVAL = int(os.environ["RP_POLL_INTERVAL"])
    RP_TIMEOUT = int(os.environ["RP_TIMEOUT"])
    BLACKLIST_EXPIRY = int(os.environ["BLACKLIST_EXPIRY"])
    GLOBAL_TIMEOUT = int(os.environ["GLOBAL_TIMEOUT"])
    PEER_TIMEOUT = int(os.environ["PEER_TIMEOUT"])
    PEER_TIMEOUT = None if PEER_TIMEOUT < 0 else PEER_TIMEOUT
    PEER_POLL_INTERVAL = int(os.environ["PEER_POLL_INTERVAL"])
    SNIFF_IFACE = os.environ["SNIFF_IFACE"]
    PEER_RETRIES = int(os.environ["PEER_RETRIES"])
    STALLING_THRESHOLD = float(os.environ["STALLING_THRESHOLD"])


except KeyError as e:
    print(f"missing environment variable: {e.args[0]}")
    exit(1)

except ValueError as e:
    print(f"invalid value for environment variable: {e.args[0]}")
    exit(1)


if __name__ == '__main__':
    for file in (F_ROOT_CRT, F_SERVER_CRT, F_SERVER_KEY):
        if not file.exists():
            print(f"missing required file: {file}")
            exit(1)
