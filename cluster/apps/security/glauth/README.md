# [GLAuth](https://github.com/glauth/glauth)

Go-lang LDAP Authentication (GLAuth) is a secure, easy-to-use, LDAP server w/ configurable backends

## Repo configuration

1. Add/Update `.vscode/extensions.json`

   ```json
   {
     "files.associations": {
         "**/kubernetes/**/*.sops.toml": "plaintext"
     }
   }
   ```

2. Add/Update `.gitattributes`

   ```text
   *.sops.toml linguist-language=JSON
   ```

3. Add/Update `.sops.yaml`

   ```yaml
   - path_regex: kubernetes/.*\.sops\.toml
     key_groups:
       - age:
           - age...
   ```

## App Configuration

Static configuration can be [provided in files](https://glauth.github.io/docs/file.html)

> `passbcrypt` can be generated at <https://cyberschef.${SECRET_DOMAIN}/#recipe=Bcrypt(12)To_Hex(%27None%27,0>)
> (or <https://gchq.github.io/CyberChef/#recipe=Bcrypt(12)To_Hex(%27None%27,0>) if not yet self-hosted)

Decrypted examples:

1. `server.sops.toml`

   ```toml
   debug = true
   [ldap]
        enabled = true
        listen = "0.0.0.0:389"
   [ldaps]
        enabled = false
   [api]
        enabled = true
        tls = false
        listen = "0.0.0.0:5555"
   [backend]
        datastore = "config"
        baseDN = "dc=home,dc=arpa"
   ```

2. `groups.sops.toml`

   ```toml
   [[groups]]
        name = "svcaccts"
        gidnumber = 6500
   [[groups]]
        name = "admins"
        gidnumber = 6501
   [[groups]]
        name = "people"
        gidnumber = 6502
   ```

3. `users.sops.toml`

   ```toml
   [[users]]
        name = "search"
        uidnumber = 5000
        primarygroup = 6500
        passbcrypt = ""
        [[users.capabilities]]
            action = "search"
            object = "*"
   [[users]]
        name = "bar"
        mail = ""
        givenname = "Bar"
        sn = "Foo"
        uidnumber = 5001
        primarygroup = 6502
        othergroups = [ 6501 ]
        passbcrypt = ""
   [[users]]
        name = "baz"
        mail = ""
        givenname = "Baz"
        sn = "Foo"
        uidnumber = 5002
        primarygroup = 6502
        passbcrypt = ""
   ```
