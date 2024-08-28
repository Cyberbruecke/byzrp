# BRP

## Docker
- build (from project root): `docker build --tag byz-rpki .`
- run `./tools/run_byz_rpki.sh <N>` for N nodes

## tools
- `pip install rpki-rtr-client`
- `rtr_client -h <container IP> -p 8282`
