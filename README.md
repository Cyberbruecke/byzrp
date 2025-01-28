# Byzantine Secure Relying Party for Resilient RPKI

The code in this repository is based on a paper published at ACM CCS 2024: [The Paper](https://dl.acm.org/doi/pdf/10.1145/3658644.3690368)

## 1. Description

ByzRP is a RP-as-a-service architecture. It consists of distributed nodes that independently 
perform relying party functionalities. These nodes are enhanced with a security monitor to protect them from stalling 
and crashing. They are located within a permissioned network, where all nodes asynchronously peer with each 
other to reach a byzantine-secure majority consensus on the final VRP output.

## 2. How to use ByzRP

### As a deployer

ByzRP can be set up as a public service for clients looking to outsource the responsibility of maintaining RPs locally. It can 
also be used internally by any entity operating RPKI-enabled routers to ensure that their RPKI protection is not
downgraded by stalling attacks or RP crashes. Check Section 3 on how to deploy ByzRP.

### As a client

Our team is currently offering a live 3-node deployment of ByzRP for anyone interested in working with our network
or simply testing it. Our RTR API offers TLS protected connections via domain `www.byzrp.net` and port `8282`.

Users can use RTR software as middleware to connect to our infrastructure and periodically download our VRPs. Alternatively,
they can also connect RPKI-enabled BGP routers directly with it. The software must allow  TLS-based connections for RTR.

### Recommendations
To interact with our deployment, we recommend using [`rtrdump`](https://github.com/bgp/stayrtr) to download the VRP dataset from our platform.
Example command:
```
rtrdump -type tls -connect www.byzrp.net:8282
```

## 3. Setup

### Local Deployment

You can deploy a local ByzRP network with docker containers on your local machine. To do so,
build the docker image from root with the `byzrp` tag:
```
docker build --tag byzrp .
```
Then run the setup script:
```
cd tools
./run_local_byzrp.sh <N> for N nodes
```

### Remote Deployment

To deploy the ByzRP infrastructure on a network of hosts, use the ansible scripts. Define your hosts and SSH info in `ansible/hosts.yml`.
Then run the following playbooks to provision, build and run the remote hosts. This setup includes Prometheus for monitoring.
```
ansible-playbook -i ansible/hosts.yml ansible/setup-hosts.playbook.yml
ansible-playbook -i ansible/hosts.yml ansible/deploy.playbook.yml
```
To stop ByzRP, run:
```
ansible-playbook -i ansible/hosts.yml ansible/shutdown.playbook.yml
```

## 4. Notes
- `PEER_POLL_INTERVAL` should be a divisor of 60
- `INIT_PEERING_DELAY` should be a multiple of `PEER_POLL_INTERVAL`

### Testing RTR
- `pip install rpki-rtr-client`
- `rtr_client -h <container IP> -p 8282`
- note: does not support RTR-over-TLS

### Testing with Curl
- e.g. `curl --cacert root.crt --cert client.crt --key client.key https://<address>/metrics/byzrp.metrics`
