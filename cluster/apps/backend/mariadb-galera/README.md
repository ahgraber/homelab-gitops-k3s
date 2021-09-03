# **mariadb**

MariaDB is a community-developed, commercially supported fork of the MySQL relational database management system, intended to remain free and open-source software under the GNU General Public License.

MariaDB _Galera_ Cluster is a virtually synchronous multi-primary cluster for MariaDB. It requires at least 3 _nodes_ so pods can run in HA.

---

# Installation

Install with helm or rancher using [bitnami/mariadb](https://artifacthub.io/packages/helm/bitnami/mariadb), <br>
or install[bitnami/mariadb-galera](https://artifacthub.io/packages/helm/bitnami/mariadb-galera)

1. Create namespace

   ```sh
   kubectl create namespace mariadb
   ```

2. Create secret for username/password

   - From command line:

     1. Calculate secrets with

        ```sh
        # kubectl create secret TYPE -n NAMESPACE SECRETNAME --from-literal=KEY=LITERAL,KEY-LITERAL
        kubectl create secret generic mariadb-secret -n mariadb \
        --from-literal=mariadb-root-password=<ROOT_PWD> \
        --from-literal=mariadb-password=<DB_PWD> \
        --from-literal=mariadb-replication-password=<BKUP_PWD> \
        --from-literal=mariadb-galera-mariabackup-password=<BKUP_PWD>
        # or
        kubectl create secret generic mariadb-secret -n mariadb \
        --from-file=mariadb-root-password=../.secrets/db_root_pwd.txt \
        --from-file=mariadb-password=../.secrets/db_pwd.txt \
        --from-file=mariadb-replication-password=../.secrets/db_bkup_pwd.txt \
        --from-file=mariadb-galera-mariabackup-password=../.secrets/db_bkup_pwd.txt
        ```

   - From yaml: edit mariadb-secret.yaml and apply

<!-- 3. Create Persistent Volume Claim to [allow volume persistence across upgrades](https://docs.bitnami.com/general/how-to/troubleshoot-helm-chart-issues/)
   * In Rancher:
     1. Cluster > local > Default
     2. Workloads > Volumes
     3. Add Volume -->

4. Install mariadb or mariadb-galera

   - In Rancher
     1. Cluster > local > Default
     2. Apps > Launch
     3. mariadb
     4. Copy values from [`mariadb-values.yaml`](./mariadb-values.yaml) into values 'edit as yaml'
   - create ingressRoute to provide access; add to firewall dns override:
     `kubectl apply -f ./ingressroute-mariadb.yaml`

5. [optional] Install [`phpmyadmin`]()

   - In Rancher
     1. Cluster > local > Default
     2. Apps > Launch
     3. mariadb
     4. Copy values from [`phpmyadmin-values.yaml`](./phpmyadmin-values.yaml) into values 'edit as yaml'
   - create ingressRoute to provide access; add to firewall dns override:
     `kubectl apply -f ./ingressroute-phpmyadmin.yaml`

6.

### _Notes:_

- [Galera inter-cluster TLS/SSL appears to be nonfunctional (May, 2021)](https://github.com/bitnami/charts/issues/5765)
  ... that said, even if it works, we'd have to create a new secret in the `mariadb` namespace or mount a cert file

_Hints:_

- May have to disable liveness/readiness probes or set to extended timeout on init and then reset to default after
- May want to create additional loadBalancer service to provide stable IP for non-k8s apps (or administration)

_Debug:_
If restarting and get CrashLoopBackoff due to _"It may not be safe to bootstrap the cluster from this node. It was not the last one to leave the cluster and may not contain all the updates. To force cluster bootstrap with this node, edit the grastate.dat file manually and set safe_to_bootstrap to 1."_

```yaml
galera:
  #   ## Galera cluster name
  #   name: galera

  ## Bootstraping options
  ## ref: https://github.com/bitnami/bitnami-docker-mariadb-galera#bootstraping
  bootstrap:
    ## Node to bootstrap from, you will need to change this parameter in case you want to bootstrap from other node
    bootstrapFromNode: 0
    ## Force safe_to_bootstrap in grastate.date file.
    ## This will set safe_to_bootstrap=1 in the node indicated by bootstrapFromNode.
    forceSafeToBootstrap: true
```

---

# MySQL Workbench

https://docs.bitnami.com/general/infrastructure/mariadb/configuration/configure-workbench/

---

# Backup / Restore

See [mariadb docs](https://docs.bitnami.com/general/infrastructure/mariadb/administration/backup-restore-mysql-mariadb/)

- Backup

  ```sh
  # single database
  mysqldump -u root -p <DB_NAME> > backup.sql
  # all DBs
  mysqldump -A -u root -p > backup.sql
  ```

- Restore

  ```sh
  # single database
  mysql -u root -p -D <DB_NAME> < backup.sql
  # all DBs
  mysql -u root -p < backup.sql
  ```
