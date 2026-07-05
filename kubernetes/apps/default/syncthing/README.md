# [Syncthing](https://syncthing.net/)

Syncthing is a continuous P2P (peer to peer) file synchronization program.
It synchronizes files between _n_ computers in real time, safely protected from prying eyes.
Your data is your data alone and you deserve to choose where it is stored, whether it is shared with some third party, and how it's transmitted over the internet.

## References

- [Docs](https://docs.syncthing.net/users/index.html)
- [How to Set Up a Headless Syncthing Network](https://theselfhostingblog.com/posts/how-to-set-up-a-headless-syncthing-network/)
- [Use Syncthing to Create a Cloud Without a Cloud](https://everyday.codes/tutorials/use-syncthing-to-create-a-cloud-without-a-cloud/)

## Local-only Discovery Enforcement

This deployment is GitOps-managed to prefer local/private network discovery only.
On each pod start, an init container patches `/var/syncthing/config.xml` with:

- `globalAnnounceEnabled=false`
- `relaysEnabled=false`
- `natEnabled=false`
- `localAnnounceEnabled=true`

This disables Syncthing global discovery, public relays, and NAT traversal while keeping LAN discovery enabled.

## Configuring Edge Devices

The cluster runs the **central** Syncthing node; laptops, phones, and other edge devices peer with it directly.
Because global discovery, relays, and NAT traversal are disabled (see above), edge devices must add the central node by **Device ID + explicit address** — auto-discovery will not find it.

Two hostnames front the central node:

- `https://syncthing.${SECRET_DOMAIN}` — the web GUI (Envoy internal route, TLS on 443).
- `sync.${SECRET_DOMAIN}` — the sync/discovery listener (dedicated LoadBalancer IP `10.2.118.6`, TCP/UDP 22000 + UDP 21027).

1. **Get the central Device ID.**
   Open the GUI at `https://syncthing.${SECRET_DOMAIN}` → **Actions → Show ID**, and copy the Device ID.
2. **Add the central node on the edge device** (desktop GUI or mobile app):
   - **Add Remote Device** and paste the central Device ID.
   - Under **Advanced → Addresses**, replace `dynamic` with `tcp://sync.${SECRET_DOMAIN}:22000` (optionally also `quic://sync.${SECRET_DOMAIN}:22000`).
   - Save.
3. **Accept on the central node.**
   Back in the GUI, accept the incoming device prompt (or add the edge Device ID manually).
4. **Share folders.**
   On the central node, share (or create) a folder with the edge device, then accept the share on the edge device and pick its local path.
   Repeat per folder.

> **Networking note:** the sync protocol needs raw L4 reachability, so it is exposed via a dedicated Cilium LoadBalancer (`discovery` service) rather than the Envoy GUI route, which only speaks HTTP.
> `sync.${SECRET_DOMAIN}` is published to internal DNS by k8s-gateway from the service's `external-dns` hostname annotation and pinned to `10.2.118.6` via LBIPAM, so the address stays stable across redeploys.
