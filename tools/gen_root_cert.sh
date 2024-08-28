#!/usr/bin/env bash

openssl req -x509 -newkey rsa:4096 -keyout root.key -out root.crt -sha256 -days 3650 -nodes -subj "/C=DE/ST=Hessen/L=Darmstadt/O=FraunhoferSIT/OU=FraunhoferSIT/CN=ByzRPKIRoot"
