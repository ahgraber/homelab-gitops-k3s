#!/bin/bash
# ref: # https://github.com/spender0/kubernetes-sandbox/blob/master/generate-kubeconfig-with-keycloak-token.sh

set -e

KEYCLOAK_URL=https://localhost:8443
REALM=kubernetes-sandbox
CLIENT_ID=kubernetes-sandbox
UNAME=k8s-user1
PASSWORD=k8s-user1-password

TOKENS_JSON=`curl -k -f \
  -d "scope=openid" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$UNAME" -d "password=$PASSWORD" \
  -d "grant_type=password" \
  "$KEYCLOAK_URL/auth/realms/$REALM/protocol/openid-connect/token"`

ID_TOKEN=`echo $TOKENS_JSON | jq -r '.id_token'`

REFRESH_TOKEN=`echo $TOKENS_JSON | jq -r '.refresh_token'`

export KUBECONFIG=conf/k8s-user1-kubeconfig.conf

kubectl config set-credentials k8s-user1 \
   --auth-provider=oidc \
   --auth-provider-arg=idp-issuer-url=${KEYCLOAK_URL}/auth/realms/${REALM} \
   --auth-provider-arg=client-id=${CLIENT_ID} \
   --auth-provider-arg=refresh-token=${REFRESH_TOKEN} \
   --auth-provider-arg=idp-certificate-authority=certs/keycloak/ca.crt \
   --auth-provider-arg=id-token=${ID_TOKEN}

kubectl config set-cluster default-cluster --server=https://localhost:6443 --certificate-authority certs/kubernetes-ca-bundle.crt --embed-certs
kubectl config set-context default-system --cluster default-cluster --user k8s-user1
kubectl config use-context default-system
