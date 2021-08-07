# :sailboat:&nbsp; Installing k3s with k3sup

:round_pushpin: Here we will be install [k3s](https://k3s.io/) with [k3sup](https://github.com/alexellis/k3sup).
After completion, k3sup will drop a `kubeconfig` in your present working directory for use with interacting with your cluster with `kubectl`.

1. Ensure you are able to SSH into you nodes with using your private ssh key. This is how k3sup is able to connect to your remote node.

2. Install the master node

   > - `--cluster` creates a HA cluster with embedded etcd db
   > - `--tls-san` adds the LoadBalancer’s virtual ip to the cert

   ```sh
   echo "export USER=nrl" >> .envrc
   echo "export KEYPATH='~/.ssh/id_rsa'" >> .envrc
   echo "export KVIP=10.2.113.113" >> .envrc
   echo "export K3S_VERSION=v1.21.3+k3s1" >> .envrc
   direnv allow .
   
   HOST="k01.ninerealmlabs.com"
   k3sup install \
     --host=${HOST} \
     --user=${USER} \
     --ssh-key=${KEYPATH} \
     --k3s-version=${K3S_VERSION} \
     --cluster \
     --tls-san ${KVIP} \
     --k3s-extra-args="--disable servicelb --disable traefik"
   ```

   Test the cluster initialization:

   ```sh
   kubectl config set-context default
   kubectl get node -o wide
   ```

3. Install [`kube-vip`](./2a%20-%20kube-vip.md)

   Wait until VIP is live on both k3s node and local machine before proceeding

   ```sh
   ping ${KVIP}
   ```

4. Add the remaining **server** nodes

   ```sh
   CONTROL=(
     "k02.ninerealmlabs.com"
     "k03.ninerealmlabs.com"
   )
   for HOST in ${CONTROL[@]}; do
     k3sup join \
       --host=${HOST} \
       --user=${USER} \
       --server-host=${KVIP} \
       --server-user=${USER} \
       --ssh-key=${KEYPATH} \
       --k3s-version=${K3S_VERSION} \
       --server \
       --k3s-extra-args="--disable servicelb --disable traefik "
   done
   ```

5. Check cluster status:

   ```sh
   # export KUBECONFIG=$(pwd)/kubeconfig
   kubectl config set-context default
   kubectl get node -o wide
   ```

6. Join worker nodes (optional)

   ```sh
   WORKER=(
     ""
     ""
   )
   for HOST in ${WORKER[@]}; do
     k3sup join \
       --host=${HOST} \
       --user=${USER} \
       --server-host=${KVIP} \
       --server-user=${USER}
     --ssh-key=${KEYPATH} \
       --k3s-version=${K3S_VERSION}
   done
   ```

7. Check cluster status:

   ```sh
   # export KUBECONFIG=$(pwd)/kubeconfig
   kubectl config set-context default
   kubectl get node -o wide
   ```
