# :sailboat:&nbsp; Installing k3s with k3sup

:round_pushpin: Here we will be install [k3s](https://k3s.io/) with [k3sup](https://github.com/alexellis/k3sup).
After completion, k3sup will drop a `kubeconfig` in your present working
directory for use with interacting with your cluster with `kubectl`.

1. Ensure you are able to SSH into you nodes with using your private ssh key. This is how k3sup is able to connect to your remote node.

2. Install the master node

    > * `--cluster` creates a HA cluster with embedded etcd db
    > * `--tls-san` adds the LoadBalancer’s virtual ip to the cert

   ```sh
   echo "export USER=nrl" >> .envrc
   echo "export KVIP=10.2.113.113" >> .envrc
   direnv allow .

   k3sup install \
       --host=k01.ninerealmlabs.com \
       --user=${USER} \
       --ssh-key=~/.ssh/ahg_ninerealmlabs_id_rsa \
       --k3s-version=v1.20.6+k3s1 \
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
   k3sup join \
       --host=k02.ninerealmlabs.com \
       --user=${USER} \
       --server-host=${KVIP} \
       --server-user=${USER} \
       --ssh-key=~/.ssh/ahg_ninerealmlabs_id_rsa \
       --k3s-version=v1.20.6+k3s1 \
       --server \
       --k3s-extra-args="--disable servicelb --disable traefik "

   k3sup join \
       --host=k03.ninerealmlabs.com \
       --user=${USER} \
       --server-host=${KVIP} \
       --server-user=${USER} \
       --ssh-key=~/.ssh/ahg_ninerealmlabs_id_rsa \
       --k3s-version=v1.20.6+k3s1 \
       --server \
       --k3s-extra-args="--disable servicelb --disable traefik"
   ```

5. Check cluster status:

   ```sh
   # export KUBECONFIG=$(pwd)/kubeconfig
   kubectl config set-context default
   kubectl get node -o wide
   ```

6. Join worker nodes (optional)

   ```sh
   HOST=10.2.113.***
   k3sup join \
       --host=${HOST} \
       --user=nrl \
       --server-host=${KVIP} \
       --server-user=nrl
       --ssh-key=~/.ssh/ahg_ninerealmlabs_id_rsa \
       --k3s-version=v1.20.6+k3s1
   ```

7. Check cluster status:

   ```sh
   # export KUBECONFIG=$(pwd)/kubeconfig
   kubectl config set-context default
   kubectl get node -o wide
   ```
