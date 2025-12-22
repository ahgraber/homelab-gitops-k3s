# Preventing Sleep on Debian When Network Connections Are Active

When running remote servers or SSH-accessible systems, you don't want your linux (Debian) machine to suspend while you're connected or performing remote tasks. This approach blocks system suspend whenever an SSH session is open — without requiring root, sudo, or system-wide configuration.

It is designed for:

- Headless servers
- Homelab nodes
- Remote-admin systems

## What This Does

When you log in via SSH:

- A background process registers a **sleep inhibitor** with `systemd-logind`

- The inhibitor remains active for the lifetime of the SSH session

- While the inhibitor is active:

  - Idle suspend is prevented
  - Manual suspend requests are delayed/refused

- When the SSH session ends:

  - The inhibitor exits automatically
  - Suspend behavior returns to normal

### 1. Set Polkit policy to skip authentication requirement

By default, using `systemd-inhibit --mode=block` requires authentication. This is a frustrating experience and can conflict with other on-login hooks (like neofetch/fastfetch) in interactive shells.
We can set a policy to skip the authentication requirement specifically for specific actions associated with `ssh-inhibit`.

1. Create policy

   ```sh
   sudo nano /etc/polkit-1/rules.d/49-ssh-inhibit.rules
   ```

2. Paste the rule definition

   ```sh
   polkit.addRule(function(action, subject) {
       if (
           subject.active === true &&
           subject.isInGroup("ssh-inhibit") &&
           (
               action.id === "org.freedesktop.login1.inhibit-block-sleep" ||
               action.id === "org.freedesktop.login1.inhibit-delay-sleep" ||
               action.id === "org.freedesktop.login1.inhibit-block-idle"
           )
       ) {
           return polkit.Result.YES;
       }
   });
   ```

3. Apply the rule

   ```sh
   sudo chown root:root /etc/polkit-1/rules.d/49-ssh-inhibit.rules
   sudo chmod 644 /etc/polkit-1/rules.d/49-ssh-inhibit.rules
   sudo systemctl restart polkit
   ```

### 2. Add the SSH login hook to inhibit sleep

1. Edit `/etc/ssh/sshrc`

   ```sh
   sudo nano /etc/ssh/sshrc
   ```

2. Add this block near the end:

   ```sh
   # Prevent sleep while SSH session is active
   systemd-inhibit \
     --what=sleep \
     --mode=block \
     --who="SSH session" \
     --why="Active SSH connection" \
     sleep infinity \
     </dev/null >/dev/null 2>&1 &
   ```

   This inhibits sleep during an SSH connection by blocking sleep:

   - `sleep infinity`
     Keeps the inhibitor alive for the duration of the session

   - `</dev/null`
     Prevents interactive authentication prompts

   - `>/dev/null 2>&1`
     Keeps SSH login output clean (no banner interference)

   - `&`
     Runs in the background so login continues normally

### 3. Verify active inhibitors

1. SSH into your Debian host (or log out & log in)

2. Run:

   ```sh
   systemd-inhibit --list
   ```

Check for `SSH session ... systemd-inhibit`.
Example output:

```txt
WHO            UID  USER   PID  COMM            WHAT         WHY           >
ModemManager   0    root   1365 ModemManager    sleep        ModemManager n>
NetworkManager 0    root   1251 NetworkManager  sleep        NetworkManager>
UPower         0    root   1642 upowerd         sleep        Pause device p>
GNOME Shell    1000 <USER> 2173 gnome-shell     sleep        GNOME needs to>
SSH session    1000 <USER> 5214 systemd-inhibit sleep        Active SSH con>
...
```

That confirms your SSH inhibitor is active.

### 4. Test the inhibitor

Try to suspend manually:

```sh
systemctl suspend
```

You should see something like:

```txt
Operation inhibited by "systemd-inhibit (SSH session)"
```
