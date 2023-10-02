# [Cilium](https://cilium.io/)

Cilium is an open source, cloud native solution for providing, securing, and observing network connectivity between workloads, fueled by the revolutionary Kernel technology eBPF

## [Preserving source IPs](https://github.com/JJGadgets/Biohazard/blob/main/kube/deploy/core/_networking/cilium/README.md)

There are 2 ways to preserve source IPs when using Cilium. A quick summary based on my understanding is provided here, read more on the official Cilium docs here: [https://docs.cilium.io/en/v1.13/network/kubernetes/kubeproxy-free/#client-source-ip-preservation](https://docs.cilium.io/en/v1.13/network/kubernetes/kubeproxy-free/#client-source-ip-preservation)

### `externalTrafficPolicy: Local` on LoadBalancer Service spec

Services create Endpoints that are like the "magic bridge" connecting traffic from Services to Nodes to Pods.

With `externalTrafficPolicy: Local`, traffic that hits a node's LoadBalancerIP must use that local node's Endpoint.

The upside is that this removes any further masquerading and hops to other nodes.
Since the request traffic has now established a "straight line" from source IP --> LBIP --> node --> pod, the return traffic can go out through the same straight line.

The downside is this creates uneven traffic distribution and potentially bottlenecks across all nodes that have a horizontally scalable workload's pod scheduled (e.g. replicaCount >= 2).

Read more about it here: [https://kubernetes.io/docs/tutorials/services/source-ip/#source-ip-for-services-with-type-loadbalancer](https://kubernetes.io/docs/tutorials/services/source-ip/#source-ip-for-services-with-type-loadbalancer)

### PREFERRED: Direct Server Return (DSR)

Cilium supports DSR, which returns the proper source IP **regardless of externalTrafficPolicy setting**.

The benefit of combining `externalTrafficPolicy: Cluster` and DSR is that you can get the best of both worlds: DSR's source IP preservation, and eTP=Cluster's Load Balancing across all nodes.

Read more about DSR here: [https://docs.cilium.io/en/v1.9/gettingstarted/kubeproxy-free/#dsr-mode](https://docs.cilium.io/en/v1.9/gettingstarted/kubeproxy-free/#dsr-mode)

## BGP Control Plane

The new Cilium BGP Control Plane, BGPCP for short in these docs, replaces the old MetalLB BGP implementation in Cilium with one based on GoBGP and is better integrated with Cilium's features.

(TODO: add stuff about the required Custom Resources, service selectors)

### Issues I've encountered

#### `externalTrafficPolicy: Local` when all nodes don't have an Endpoint

##### Problem

Services create Endpoints that are like the "magic bridge" connecting traffic from Services to Nodes to Pods.

BGP Control Plane, as of 27 May 2023, will advertise BGP routes to nodes that don't have Endpoints since a workload's Pods don't run on those nodes. This creates an additional issue with `externalTrafficPolicy: Local`

e.g. node1 is scheduled with 1 ingress-nginx Pod, thus has Endpoint, thus Service can route to Node.

e.g. node2 doesn't have any ingress-nginx Pods, thus no Endpoints, thus Service can't route to Node.

With `externalTrafficPolicy: Local`, since traffic that hits a node must use that local node's Endpoint, if the traffic hits a node that isn't running the workload's pods, **it errors out**, usually with a timeout.

Other LoadBalancers like MetalLB solve this by **only advertising** a LoadBalancer Service's LoadBalancerIP _from a node **with** that Service's Endpoint_. BGPCP doesn't have this check.

##### Solution

###### Preferred

Switch the service to `externalTrafficPolicy: Cluster`, and **use DSR (Direct Server Return)**.

###### Alternative

Refine CiliumBGPPeeringPolicy and the workload's scheduling policies to select the same service and node.

###### NOT RECOMMENDED (unless your workload supports it, like ingress-nginx)

Scale the workload onto all nodes that are advertising BGP (in my homelab, currently all nodes advertise).
