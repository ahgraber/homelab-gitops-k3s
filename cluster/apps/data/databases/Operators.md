# Operators

Notes (Jul 2022) on current state of postgres operators for k8s.
Goal -- find a FOSS operator that is easy to deploy & maintain.

See also:

* [operatorhub.io](https://operatorhub.io/?category=Database)
* [Data on K8s](https://dok.community/)
* [Hackerrank discussion](https://news.ycombinator.com/item?id=31882256)
* [Comparing k8s operators for Postgres](https://blog.flant.com/comparing-kubernetes-operators-for-postgresql/)

## CloudNativePG

Pros:

* Good documentation
* Helm install
* Declarative cluster config

## Crunchydata

Pros:

* Good documentation
* Helm install
* Declaritive cluster/db/user creation/mgmt

Cons:

* Images provided under the terms of use of the Crunchy Data developer program
  which means you can't use them in production without an active subscription.

## Percona

Pros:

* Helm install

Cons:

* Sparse documentation / difficult to navigate
* Could not complete installation to get functional installation

## Stackgres

Pros:

* Good documentation
* Helm install
* Snazzy UI

Cons:

* Configuration via embedded scripts
* Some features (like [grafana autoimbed](https://gitlab.com/ongresinc/stackgres/-/issues/1849)) do not seem to work
* Gitlab issues search requires sign in, which requires gitlab user account

## Zalando

Pros:

* Good documentation
* Helm install
* Customizability

Cons:

* More customizability means more admin time
* User passwords are randomly generated at time of creation;
  to use a manually-defined password requires editing a secret after cluster creation

## Kubegres

Notes:  after reviewing the documentation, I have not experimented with kubegres

Pros:

* Good documentation

Cons:

* No helm install
