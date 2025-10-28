# Preventing Sleep on Debian When Network Connections Are Active

When running remote servers or SSH-accessible systems, you don't want your Debian machine to suspend while you're connected or performing remote tasks.

This guide covers two practical methods:

1. **🥇 Recommended:** user-level SSH inhibitor (via `systemd-run`)
2. **🧩 Optional:** background service that blocks sleep when any network connection is active

## 🥇 Recommended: User-Level SSH Sleep Inhibitor

This approach blocks system suspend whenever an SSH session is open — without requiring root, sudo, or system-wide configuration.

It works by using `systemd-run --user` to create a temporary *inhibit scope* tied to your SSH login session.
When you log out, the inhibitor automatically disappears.

### Step 1 — Add inhibitor to SSH session

Edit `/etc/ssh/sshrc` and add this block near the end:

```bash
# Prevent sleep while SSH session is active
systemd-run --scope --user systemd-inhibit \
  --what=sleep \
  --who="SSH session" \
  --why="Active SSH connection" \
  sleep infinity >/dev/null 2>&1 &
```

> 🧠 This command starts a background process that tells `systemd-logind`
> "do not allow sleep" while the SSH session is active.

### Step 2 — (Recommended) Clean up on logout

To ensure no orphaned inhibitors remain if a session is interrupted, add this line to `/etc/bash.bash_logout`:

```bash
# Clean up SSH-based inhibitors on logout
pkill -f "systemd-inhibit.*SSH session" || true
```

### Step 3 — Verify active inhibitors

1. SSH into your Debian host.

2. Run:

   ```bash
   systemd-inhibit --list
   ```

Check for `SSH session ... systemd-inhibit`.
Example output:

```txt
WHO            UID  USER   PID  COMM            WHAT                                                     WHY           >
ModemManager   0    root   1365 ModemManager    sleep                                                    ModemManager n>
NetworkManager 0    root   1251 NetworkManager  sleep                                                    NetworkManager>
UPower         0    root   1642 upowerd         sleep                                                    Pause device p>
GNOME Shell    1000 <USER> 2173 gnome-shell     sleep                                                    GNOME needs to>
SSH session    1000 <USER> 5214 systemd-inhibit sleep                                                    Active SSH con>
...
```

That confirms your SSH inhibitor is active.

### Step 4 — Test it

Try to suspend manually:

```bash
systemctl suspend
```

You should see something like:

```txt
Operation inhibited by "systemd-inhibit (SSH session)"
```

### Why this method is ideal

| ✅ Benefit            | Description                                                  |
| --------------------- | ------------------------------------------------------------ |
| **No sudo required**  | Works as a normal user — no prompts or configuration changes |
| **Automatic cleanup** | Inhibitor ends when SSH session ends                         |
| **Low overhead**      | No polling or background daemons                             |
| **Works per user**    | Independent for multiple concurrent SSH sessions             |

## 🧩 Optional: Global Network Activity Monitor (systemd Service)

If you want to prevent sleep whenever *any* TCP connection is active — not just SSH — you can run a background systemd service.

Create `/usr/local/bin/net-activity-inhibit`:

```bash
#!/usr/bin/env bash
set -euo pipefail

while true; do
  conns=$(ss -t -H state established | grep -v '127\.0\.0\.1' | wc -l)

  if (( conns > 0 )); then
    systemd-inhibit --what=sleep \
      --who="net-activity-inhibit" \
      --why="Active TCP connections" \
      sleep 300 &
    pid=$!
    wait $pid
  else
    sleep 60
  fi
done
```

Make it executable:

```bash
chmod +x /usr/local/bin/net-activity-inhibit
```

Then define `/etc/systemd/system/net-activity-inhibit.service`:

```ini
[Unit]
Description=Prevent sleep when active network connections exist
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/net-activity-inhibit
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now net-activity-inhibit.service
```

## ✅ Summary

| Method                                     | Scope               | Privileges       | Complexity  | Recommended for         |
| ------------------------------------------ | ------------------- | ---------------- | ----------- | ----------------------- |
| SSH-based inhibitor (`systemd-run --user`) | Only SSH sessions   | No root required | ⭐ Simple   | Remote admin / homelab  |
| Network-activity monitor                   | All TCP connections | Root required    | ⚙️ Moderate | NAS / always-on servers |

For most Debian homelab servers and remote systems,
**the SSH-based approach is the cleanest and safest solution.**
