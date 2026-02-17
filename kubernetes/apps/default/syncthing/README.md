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
