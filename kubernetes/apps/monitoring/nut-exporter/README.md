# Network UPS Tools (NUT) Exporter

The helm-release acts as a translation layer between the NUT server (on OPNSense) and prometheus.
An AdditionalScrapeConfig job is configured to watch this exporter and track metrics.

> See ansible role in `homelab-ansible` for `nut-client` configuration on k3s nodes,
> which handles node configuration and shutdown

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
