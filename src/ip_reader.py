import re
from time import sleep

from vars import F_PEER_IP_LOG, F_PEER_CANDIDATES, PEER_POLL_INTERVAL

WAIT = PEER_POLL_INTERVAL / 4
seen = set()

while True:
    with open(F_PEER_IP_LOG) as f_in:
        for line in f_in:
            ip = line.strip()

            if re.match("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", ip):
                if not F_PEER_CANDIDATES.exists():
                    seen = set()

                if ip not in seen:
                    with open(F_PEER_CANDIDATES, "a") as f_out:
                        f_out.write(ip + "\n")
                    seen.add(ip)
    sleep(WAIT)
