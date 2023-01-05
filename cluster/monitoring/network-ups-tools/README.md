# Network UPS Tools (NUT)

The helm-release here simply enables a Prometheus Service Monitor to watch the UPS and track metrics.
See ansible role in `homelab-ansible` for `nut-client` configuration on k3s nodes

## Network UPS Tools integration

Refs:
<!-- markdownlint-disable MD034 -->
- https://schnerring.net/blog/configure-nut-for-opnsense-and-truenas-with-the-cyberpower-pr750ert2u-ups/
- https://forum.opnsense.org/index.php?topic=27936.0
<!-- markdownlint-enable MD034 -->

1. Ensure NUT configured on OPNsense (acting as NUT server)

2. From both OPNsense (server) and client nodes, test with:

   ```sh
   upsc <UPS_NAME>@<OPNSENSE_IP>:3493
   ```

3. Test that it actually shuts devices down:

   ```sh
   # from server (OPNsense)
   upsmon -c fsd
   ```
