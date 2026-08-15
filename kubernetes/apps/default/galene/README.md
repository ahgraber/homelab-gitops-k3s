# [Galene](https://galene.org/)

Galene is a WebRTC videoconference server (an SFU) written in Go by Juliusz Chroboczek.
This deployment serves small group calls at `meet.${SECRET_DOMAIN}`.

## Using it

The landing page lists only groups marked `public`.
If no public groups exist, it shows an empty list and a join form.
Enter the desired group name (e.g. `guests`).

```text
https://meet.${SECRET_DOMAIN}/group/guests/
```

### Signing in

Galene asks for a username and password.
The user account is associated with the group field of the `homelab/default.galene` item, whose top-level keys are the usernames; see [Hashing a password](#hashing-a-password) to set or reset one.

### You join first

`autolock: true` locks the group whenever no operator is present, re-evaluated on every join and leave.
The lock check skips operator users (`op`); operators can enter and everyone else waits until an operator is present (and possibly the group is `/unlock`ed).
The group relocks when `op` leaves.

`/unlock` clears the lock for the current session and `/lock [message]` sets it again.
Both are operator-only.

### Inviting people

Click your own name, the first entry in the participant list, and select _Invite user_.
The chat command `/invite [username] [expiration]` does the same, with both arguments optional.
Either returns a link of the form `https://meet.${SECRET_DOMAIN}/group/guests/?token=XXX` that grants password-less entry.

It is possible to use a single link to admit multiple users to a call - or multiple calls - the link works until it expires or is retired.
Guests pick their own display name unless the token carries a username, which then overrides what the browser sends.
Issue a link per person when access has to be revocable individually, or when you need participant names you can trust; `/revoke` then removes one guest instead of all of them.

### Invite lifetime

Links expire 48 hours after creation.
The invite dialog prefills that value and accepts any other date, plus an optional `not-before` date for a link that becomes valid later.
Permanent links are impossible.

Operators manage existing links from the chat box:

| Command                         | Effect                                                        |
| ------------------------------- | ------------------------------------------------------------- |
| `/invite [username] [expiry]`   | Creates a link, anonymous and 48-hour by default              |
| `/listtokens`                   | Lists outstanding invitation links                            |
| `/revoke <link>`                | Expires a link immediately                                    |
| `/reinvite <link> [expiration]` | Extends a link, defaulting to one day if no duration is given |

Durations take a compact syntax (`30min`, `2h`, `7d`, `1yr`) or a full date string.
Expired tokens are deleted from `tokens.jsonl` seven days after they lapse.

Galene has no web administration page.
`/stats.html` reports server statistics behind the `adminUsername` credentials and cannot create accounts or links.

## Why Galene

The cluster has no inbound public port: its only public ingress is a Cloudflare Tunnel, and the home network is double-NATed.
That rules out most self-hosted conferencing software.
A Cloudflare Tunnel proxies no UDP, and its TCP service type requires each client to run `cloudflared access tcp`, which guests joining by link will not do.
No SFU carries RTP inside HTTP or WebSocket, so the tunnel cannot carry media at all.
Jitsi's videobridge needs a reachable public address, and the TCP ICE fallback that might have substituted for one was disabled upstream around 2022.

Galene handles this case directly.
From the installation guide:

> If the server is not accessible from the Internet, e.g. because of NAT or because it is behind a restrictive firewall, then you should configure a TURN server that runs on a host that is accessible by both Galene and the clients.

Galene relays its own media through an external TURN service, so only signalling crosses the tunnel and no inbound port opens.

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
The PVC state, group definitions, and recordings mount only into Galene, so the TURN containers cannot read password hashes, invite tokens, or recordings.

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

Galene stores bcrypt hashes as a JSON object, not a bare string.
Go's bcrypt accepts the `$2a$`, `$2b$`, and `$2y$` prefixes, so any bcrypt tool works.

`htpasswd` prints `user:hash`, and an empty username leaves a leading colon that is not part of the hash:

```bash
htpasswd -bnBC 10 "" <password> | cut -d: -f2
```

`galenectl` ships in the image and generates hashes too:

```bash
docker run --rm --entrypoint /usr/local/bin/galenectl ghcr.io/ahgraber/galene hash-password -help
```

`adminPasswordHash` holds one such object.
`guests` holds a map of usernames, each pairing an object with a group permission: `op`, `present`, `message`, `observe`, or `caption`.

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

Both fields are templated into JSON unquoted, so store each as a bare object; a quoted string produces a config or group file that will not parse.

### Cloudflare Realtime TURN

Calls fail without a working TURN key, so create one before the first call.

1. In the Cloudflare dashboard, open **Realtime**, then **TURN Server**, then **Create**.
2. Copy the Turn Token ID into `turnKeyId`.
3. Copy the API Token into `turnApiToken`.
   Cloudflare displays this token once.

`turn_rotate.py` then calls `POST /v1/turn/keys/<turnKeyId>/credentials/generate-ice-servers` to mint the short-lived credentials Galene hands to clients.

Cloudflare bills per relayed GB above a 1,000 GB allowance; see [Cost](#cost).
The key is a standards-compliant TURN service, so moving to a self-hosted coturn later means replacing `ice-servers.json` and removing the rotation sidecar.

### Access control

A group exists only when `groups/<name>.json` exists, so an unrecognised URL cannot create a room.
`guests.json` is restrictive by default:

| Setting            | Effect                                                                              |
| ------------------ | ----------------------------------------------------------------------------------- |
| no `wildcard-user` | Only named users authenticate; the field would enable shared-password or open joins |
| `public: false`    | Keeps the group off the landing page                                                |
| `max-clients`      | Caps concurrency, which also bounds the TURN bill                                   |
| `autolock: true`   | Locks the group whenever no operator is present                                     |

The `allow-anonymous` field is obsolete; current Galene ignores it and logs a warning.
See [You join first](#you-join-first) for how the lock behaves during a call.

### Account model

Named accounts come from the JSON files, `galenectl`, or the administrative HTTP API at `/galene-api/v0/`.
Pyrite, the one third-party web admin, is described by upstream as "currently on hold and out of date"; the remaining integrations are a WordPress plugin and an Openfire plugin.

This deployment expects one named account, yours, holding `op`, with invite links for everyone else, so adding a guest needs no repository change.
Invite tokens live in `data/var/tokens.jsonl` on the PVC, which is why that volume is backed up.

To manage accounts at runtime, set `writableGroups: true` in `config.json` and move `/groups` from the read-only Secret mount onto the PVC as a `groups` subPath.
`galenectl` can then create groups and users through the admin API.
Group definitions stop being declarative in exchange: access control becomes runtime state that is backed up rather than reviewed in git.

### TURN credential rotation

Galene sends its ICE configuration verbatim to every client that joins a group, so any credential in `ice-servers.json` is readable by every participant.
Galene can mint ephemeral credentials itself with coturn's `use-auth-secret` scheme (`credentialType: hmac-sha1`), but Cloudflare does not implement it; its only credential path is a server-to-server REST call.
`turn_rotate.py` closes the gap.
It mints short-lived credentials, validates the response, and writes the file atomically, and Galene re-reads that file within about five minutes without a restart.

Rotation happens halfway through the credential lifetime, and replaced credentials are not revoked.
A browser retains the ICE configuration it received on joining, and the overlap lets it open another peer connection or restart ICE; the old credential then expires at Cloudflare on its original schedule.
If the provider returns an empty or malformed response, the helper exits and leaves the last valid file in place.

Only people already authorised to join a call can read the credential, which limits exposure without removing it.
Cloudflare provides no hard spend cap, and its budget alerts do not pause usage.

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
This repository builds its own from `containers/galene/Containerfile`, a versioned release tag on a distroless base running as UID 65532, and `.github/workflows/container-images.yaml` publishes it to `ghcr.io/ahgraber/galene`.

Renovate tracks the base images natively and reads the annotated `ARG VERSION` for Galene release tags.
The HelmRelease still references mutable tags for both Galene and the Python helper.
Pin both by digest, and verify the Galene source commit or archive checksum, before treating the build as reproducible.

## Known issues

`-turn=` is set explicitly rather than left at the `auto` default, which disables the built-in TURN server only once `ice-servers.json` exists.
A cold start would otherwise bind a TURN port nothing can reach.

The Deployment uses the `Recreate` strategy because Galene keeps conference state in memory and uses one RWO PVC.
A rollout ends active calls and pauses while the TURN init container mints a credential, but never runs two Galene instances at once.

`data/var/tokens.jsonl` on the PVC holds outstanding invite links, so restoring an old snapshot invalidates links already shared.

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
