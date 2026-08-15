# [Galene](https://galene.org/)

Galene is a WebRTC videoconference server (an SFU) written in Go by Juliusz Chroboczek.
This deployment serves small group calls at `meet.${SECRET_DOMAIN}`.

## Why Galene

The cluster has no inbound public port.
Its only public ingress is a Cloudflare Tunnel, and the home network is double-NATed.

That constraint eliminates most self-hosted conferencing software.
A Cloudflare Tunnel proxies no UDP, and its TCP service type requires the client to run `cloudflared access tcp`, which guests joining by link will not do.
No SFU carries RTP inside HTTP or WebSocket, so the tunnel cannot carry media at all.
Jitsi's videobridge needs a reachable public address, and the TCP ICE fallback that might have substituted for one was disabled upstream around 2022.

Galene supports this case directly.
From the installation guide:

> If the server is not accessible from the Internet, e.g. because of NAT or because it is behind a restrictive firewall, then you should configure a TURN server that runs on a host that is accessible by both Galene and the clients.

Galene therefore relays its own media through an external TURN service.
Only signalling crosses the tunnel, and no inbound port is opened.

```text
browsers --- HTTPS/WSS ---> Cloudflare Tunnel ---> envoy-external ---> galene   (signalling)
browsers <-- Cloudflare Realtime TURN ---------------------------->    galene   (media)
```

## Configuration

| Concern                           | Source                            | Path                       |
| --------------------------------- | --------------------------------- | -------------------------- |
| Server config (`proxyURL`, admin) | `galene-secret`                   | `/data/config.json`        |
| Group definitions and users       | `galene-groups`, read-only        | `/groups`                  |
| TURN credentials                  | minted by `config/turn_rotate.py` | `/data/ice-servers.json`   |
| Invite tokens, recordings         | PVC (`volsync` component)         | `/data/var`, `/recordings` |

The TURN file lives on a pod-local `emptyDir` shared by Galene and the two TURN containers.
The PVC state, group definitions, and recordings are mounted only into Galene, so the TURN containers cannot read password hashes, invite tokens, or recordings.

### Secrets

One 1Password item, `homelab/default.galene`, backs both ExternalSecrets.

| Field               | Type      | Purpose                                             |
| ------------------- | --------- | --------------------------------------------------- |
| `adminUsername`     | text      | Server admin; gates `/stats.html` and the admin API |
| `adminPasswordHash` | concealed | bcrypt object, `{"type":"bcrypt","key":"$2y$..."}`  |
| `guests`            | concealed | The `users` object for `groups/guests.json`         |
| `turnKeyId`         | concealed | Cloudflare Realtime TURN key ID                     |
| `turnApiToken`      | concealed | Cloudflare Realtime TURN API token                  |

To create the placeholder item and populate it, run:

```bash
just secrets create default galene \
  'adminUsername[text]' adminPasswordHash guests turnKeyId turnApiToken
just secrets sync
```

### Hashing a password

Galene stores bcrypt hashes as a JSON object rather than a bare string.
Go's bcrypt implementation accepts the `$2a$`, `$2b$`, and `$2y$` prefixes, so any bcrypt tool will work.

`htpasswd` prints `username:hash`.
An empty username leaves a leading colon, which is not part of the hash and must be removed:

```bash
# htpasswd output format is "user:hash", so this leading colon is an artifact
htpasswd -bnBC 10 "" <password>
# :$2y$10$...

# keep only the hash
htpasswd -bnBC 10 "" <password> | cut -d: -f2
```

`adminPasswordHash` holds the hash wrapped in the object Galene expects:

```json
{
  "type": "bcrypt",
  "key": "$2y$10$..."
}
```

`guests` holds a map of users.
Each entry pairs such an object with a group permission: `op`, `present`, `message`, `observe`, or `caption`.

```json
{
  "you": {
    "password": {
      "type": "bcrypt",
      "key": "$2y$10$..."
    },
    "permissions": "op"
  },
  "alice": {
    "password": {
      "type": "bcrypt",
      "key": "$2y$10$..."
    },
    "permissions": "present"
  }
}
```

Both fields are templated into JSON unquoted.
Store each as a bare JSON object; a quoted string produces a config or group file that will not parse.

`galenectl` ships in the image and can also generate hashes:

```bash
docker run --rm --entrypoint /usr/local/bin/galenectl ghcr.io/ahgraber/galene hash-password -help
```

### Cloudflare Realtime TURN

Calls fail without a working TURN key, so create one before the first call.

1. In the Cloudflare dashboard, open **Realtime**, then **TURN Server**, then **Create**.
2. Copy the Turn Token ID into `turnKeyId`.
3. Copy the API Token into `turnApiToken`.
   Cloudflare displays this token once.

`turn_rotate.py` then calls `POST /v1/turn/keys/<turnKeyId>/credentials/generate-ice-servers` with that token to mint the short-lived credentials Galene hands to clients.

Cloudflare bills per relayed GB above a 1,000 GB allowance; see [Cost](#cost).
The key is a standards-compliant TURN service, so migrating to a self-hosted coturn later requires only replacing `ice-servers.json` and removing the rotation sidecar.

### Access control

A group exists only when `groups/<name>.json` exists, so an unrecognised URL cannot create a room.
`guests.json` is restrictive by default:

| Setting            | Effect                                                                              |
| ------------------ | ----------------------------------------------------------------------------------- |
| no `wildcard-user` | Only named users authenticate; the field would enable shared-password or open joins |
| `public: false`    | Keeps the group off the landing page                                                |
| `max-clients`      | Caps concurrency, which also bounds the TURN bill                                   |
| `autolock: true`   | Locks the group once the last operator leaves                                       |

The `allow-anonymous` field is obsolete and plays no part here.
Current Galene ignores it and logs a warning.

### Adding people

Galene has no web UI for creating accounts.
Named accounts come from the JSON files, from `galenectl`, or from the administrative HTTP API at `/galene-api/v0/`.
Pyrite, the one third-party web admin, is described by upstream as "currently on hold and out of date"; the other listed integrations are a WordPress plugin and an Openfire plugin.

Most access does not require an account.
An operator selects _Invite user_ in the group menu to generate a link of the form `https://meet.${SECRET_DOMAIN}/group/guests/?token=XXX`, which grants password-less entry.

This deployment therefore expects one named account, yours, holding `op`, with invite links for everyone else.
Adding a guest needs no repository change, and access stays revocable from the browser.
Invite tokens are stored in `data/var/tokens.jsonl` on the PVC, which is why that volume is backed up.

#### Invite lifetime and revocation

Invite links expire 48 hours after creation.
The invite dialog prefills that value and accepts any other date, along with an optional `not-before` date for a link that becomes valid later.
A link with no expiry is not possible: the server rejects a token that does not expire, and validation treats a missing expiry as already expired.

Operators manage existing links from the chat box:

| Command                         | Effect                                                        |
| ------------------------------- | ------------------------------------------------------------- |
| `/listtokens`                   | Lists outstanding invitation links                            |
| `/revoke <link>`                | Expires a link immediately                                    |
| `/reinvite <link> [expiration]` | Extends a link, defaulting to one day if no duration is given |

Durations use a compact syntax (`30min`, `2h`, `7d`, `1yr`) or a full date string, so `/reinvite <link> 7d` gives someone another week.
Expired tokens are deleted from `tokens.jsonl` seven days after they lapse.

A link sent on Friday for a Sunday call still works, but one sent a month ago does not.
For someone who joins regularly, extend the link with `/reinvite` or give them a named account in the `guests` field.

To manage accounts at runtime instead, set `writableGroups: true` in `config.json` and move `/groups` from the read-only Secret mount onto the PVC as a `groups` subPath.
`galenectl` can then create groups and users through the admin API.
The cost is that group definitions stop being declarative: access control becomes runtime state that is backed up rather than reviewed in git.

### TURN credential rotation

Galene sends its ICE configuration verbatim to every client that joins a group, so any credential in `ice-servers.json` is readable by every participant.
Galene can mint ephemeral credentials itself with coturn's `use-auth-secret` scheme (`credentialType: hmac-sha1`), but Cloudflare does not implement that scheme; its only credential path is a server-to-server REST call.
`turn_rotate.py` closes the gap by minting short-lived credentials, validating the provider response, and writing it atomically.
Galene re-reads the file within about five minutes and needs no restart.

Rotation happens halfway through the credential lifetime.
Replaced credentials are not revoked because browsers can retain the ICE configuration they received when they joined.
The overlap lets an existing browser create another peer connection or restart ICE; the old credential then expires at Cloudflare on its original schedule.
If the provider returns an empty or malformed response, the helper exits without replacing the last valid file.

Only people already authorised to join a call can read the credential, which limits exposure but does not remove it.
Cloudflare provides no hard spend cap, and its budget alerts are informational and do not pause usage.

### Cost

All media crosses the relay in both directions.
The figures below assume no direct path ever succeeds, so they are worst-case:

| Call size | Relay traffic | At $0.05/GB               |
| --------- | ------------- | ------------------------- |
| 4 people  | ~9.5 GB/hr    | free tier covers ~100 hrs |
| 15 people | ~165 GB/hr    | free tier gone in ~6 hrs  |

For regular calls at the larger size, a flat-rate VPS running coturn costs less and carries less risk.
A Hetzner CX22 is about EUR 3.79/mo and includes 20 TB of traffic, which removes the uncapped billing exposure.
Galene's native `hmac-sha1` credentials work against coturn, so no credential reaches clients at all.

## Container image

Upstream publishes no official image, and its FAQ discourages containerising Galene.
Every community image surveyed was stale, ran as root, built from a floating branch, or omitted the `static/` web client.
This repository therefore builds its own from `containers/galene/Containerfile`: a versioned release tag on a distroless base, running as UID 65532.
The generic `.github/workflows/container-images.yaml` workflow publishes it to `ghcr.io/ahgraber/galene`.

The first rollout is a two-step operation: publish the image tag, then replace the Helm image reference with the published digest before enabling the Flux Kustomization.
The Python helper image must also be pinned to a registry digest before the first rollout.
The draft keeps tags only because neither digest exists in this repository yet.

Renovate tracks the base images natively and uses the annotated `ARG VERSION` to track Galene release tags.
The builder image, runtime image, and Galene source still use mutable tags.
Pin both base images by digest and verify the Galene source commit or archive checksum before treating the build as reproducible.

## Known issues

`-turn=` is set explicitly rather than left at the `auto` default.
`auto` disables the built-in TURN server only when `ice-servers.json` already exists, so a cold start would briefly bind a TURN port that nothing can reach.

The Deployment uses the `Recreate` strategy because Galene keeps conference state in memory and uses one RWO PVC.
A rollout ends active calls and has a short outage while the TURN init container mints a credential; it never overlaps two independent Galene instances.

The PVC holds live state.
`data/var/tokens.jsonl` stores outstanding invite links, so restoring an old snapshot invalidates links already shared.

Recording is disabled.
Enabling it writes WebM files to `/recordings` on the same PVC, so raise `VOLSYNC_CAPACITY` in `ks.yaml` first; growing the volume afterwards requires resizing the underlying Ceph RBD image.

Screen sharing does not work on any mobile browser, Android or iOS.
Desktop browsers and iOS Safari are otherwise supported.

Galene has one maintainer, who holds roughly 90% of its commits.
NLnet has funded development since 2024.

## Links

- [Upstream repository](https://github.com/jech/galene)
- [Installation guide](https://github.com/jech/galene/blob/master/galene-install.md)
- [Manual](https://github.com/jech/galene/blob/master/galene.md)
- [Administrative API](https://github.com/jech/galene/blob/master/galene-api.md)
- [Cloudflare Realtime TURN](https://developers.cloudflare.com/realtime/turn/)
