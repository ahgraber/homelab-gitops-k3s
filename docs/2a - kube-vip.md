# :computer:&nbsp; High-Availability VirtualIP with kube-vip

`kube-vip` is a Kubernetes Virtual IP and Load-Balancer for both control plane
and Kubernetes services

_`kube-vip` creates a virtual IP for the control plane for high availability (and acts as a loadBalancer for services), whereas `metallb` **only** acts a loadBalancer for services_
However, most of `kube-vip`'s development is currently going to ensuring the
VIP works, so we'll use it for control plane vIP and also use `metallb` for
service load balancing.

https://kube-vip.io/hybrid/daemonset/

-----

1. SSH into control node

2. Download RBAC (Rule-Based Access Control) for kube-vip and save to control node's `manifiests` folder

   ```sh
   sudo su - # may have to act as root
   curl -s https://kube-vip.io/manifests/rbac.yaml > /var/lib/rancher/k3s/server/manifests/kube-vip-rbac.yaml
   ```

3. View/Edit the RBAC manifest to ensure that the following ruleset is present

   ```sh
   nano /var/lib/rancher/k3s/server/manifests/kube-vip-rbac.yaml
   ```

   ...

   ```yml
   rules:
       - apiGroups: ["coordination.k8s.io"]
       resources: ["leases"]
       verbs: ["list", "get", "watch", "update", "create"]
   ```

4. Fetch `kube-vip` container & create alias

   ```sh
   VERSION="v0.3.7"
   crictl pull docker.io/plndr/kube-vip:${VERSION}
   alias kube-vip="k3s ctr run --rm --net-host docker.io/plndr/kube-vip:${VERSION} vip /kube-vip"
   kube-vip version
   ```

   > If you get an error like _"ctr: image "docker.io/plndr/kube-vip:0.3.4": not found"_, edit alias:
   > `alias kube-vip="k3s ctr run --rm --net-host docker.io/plndr/kube-vip:${VERSION} vip /kube-vip"`

5. Create `kube-vip` manifest

   ```sh
   export KVIP=10.2.113.113  # same IP provided to tls-san flag
   export INTERFACE=ens192  # standard network interface

   kube-vip manifest daemonset \
       --arp \
       --interface ${INTERFACE} \
       --address ${KVIP} \
       --controlplane \
       --leaderElection \
       --taint \
       --inCluster | tee /var/lib/rancher/k3s/server/manifests/kube-vip.yaml
   ```

6. Check that the VIP is live on both k3s node and local machine

   ```sh
   ping ${KVIP}
   ```

7. Redirect kubeconfig to kube-vip

   ```sh
   sed -i.bak 's|server: https://.*:6443|server: https://'${KVIP}':6443|g' kubeconfig
   # test new kubeconfig
   kubectl get nodes -o wide
   # if works and looks good
   rm -f kubeconfig.bak
   ```
