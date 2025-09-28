# External Services

This leverages Kubernetes networking resources (Service, Endpoint, HTTPRoute)
to allow k8s-gateway and the Cilium Gateway to act as reverse proxies for services
not hosted within the k8s cluster.

See also [proxy to external services](https://kristhecodingunicorn.com/post/k8s_proxy_svc/#proxy-to-external-services-with-service-without-selectors)
