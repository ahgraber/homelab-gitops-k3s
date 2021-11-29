# Data Restoration with Velero

> [Velero Documentation](https://velero.io/docs/main/)

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
   # restore pod
   velero restore create <restore_name> --from-backup <backup_name> --selector app.kubernetes.io/instance=<app_name> --wait
   # restore volumes
   velero restore create <restore_name> --from-backup <backup_name> --selector app.kubernetes.io/instance=<app_name> --include-resources persistentvolumeclaims,persistentvolumes --wait
   ```

4. Resume Flux

   ```sh
   flux resume kustomization core
   flux resume kustomization apps
   flux resume hr <helmrelease>
   ```

5. Profit
