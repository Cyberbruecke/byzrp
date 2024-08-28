#!/usr/bin/env bash

openssl genrsa -out $1.key
openssl req -new -key $1.key -out $1.csr -subj /C=DE/ST=Hessen/L=Darmstadt/O=FraunhoferSIT/OU=FraunhoferSIT/CN=$1 -addext "subjectAltName = IP:$1"
openssl x509 -req -in $1.csr -CA root.crt -CAkey root.key -CAcreateserial -out $1.crt -days 365 -copy_extensions copy
rm $1.csr
