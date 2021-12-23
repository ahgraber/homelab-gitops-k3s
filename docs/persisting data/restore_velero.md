# Data Restoration with Velero

Refer to [Velero Documentation](https://velero.io/docs/main/)

1. Suspend Flux

   ```sh
   flux suspend kustomization core  # don't auto reconcile namespaces, etc
   flux suspend kustomization apps  # don't auto reconcile applications
   flux suspend hr <helmrelease>  # don't auto reconcile specific helm release
   ```

2. Delete namespace to be restored

   ```sh
   kubectl delete namespace <namespace>
   ```

3. Restore namespace with Velero

   ```sh
   # this should simply recreate the namespace
   velero restore create <restore_name> --from-backup <backup_name>
   ### or restore specific resources only
   # # restore pod
   # velero restore create <restore_name> --from-backup <backup_name> --selector app.kubernetes.io/instance=<app_name> --wait
   # # restore volumes
   # velero restore create <restore_name> --from-backup <backup_name> \
   #   --selector app.kubernetes.io/instance=<app_name> \
   #   --include-resources persistentvolumeclaims,persistentvolumes \
   #   --wait
   ```

   > We can test by creating a duplicate namespace:
   >
   > ```sh
   > velero restore create <restore_name> --from-backup <backup_name> --namespace-mappings <old_ns>:<new_ns>
   > ```
   >
   > Connect to replicated namespace with `kubectl proxy`
   >
   > ```sh
   > # in terminal
   > kubectl proxy --port=8080
   > # access url from web page
   > # http://localhost:8080/api/v1/namespaces/<new_ns>/services/<service_name>:<service_port>/proxy/
   > ```

4. Resume Flux

   ```sh
   flux resume kustomization core
   flux resume kustomization apps
   flux resume hr <helmrelease>
   ```

5. Profit
