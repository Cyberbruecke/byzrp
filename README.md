# ByzRP

## Run Locally
- build (from project root): `docker build --tag byzrp .`
- `cd tools` and `./run_local_byzrp.sh <N>` for N nodes

## Deploy Remotely
- define node hosts in `ansible/hosts.yml` (including SSH info)
- run `ansible-playbook -i ansible/hosts.yml ansible/setup-hosts.playbook.yml` to provision remote hosts
- run `ansible-playbook -i ansible/hosts.yml ansible/deploy.playbook.yml` to build, upload and run ByzRP nodes and Prometheus container for monitoring
- run `ansible-playbook -i ansible/hosts.yml ansible/shutdown.playbook.yml` to stop ByzRP and monitoring containers

## Testing RTR
- `pip install rpki-rtr-client`
- `rtr_client -h <container IP> -p 8282`
- note: does not support RTR-over-TLS
