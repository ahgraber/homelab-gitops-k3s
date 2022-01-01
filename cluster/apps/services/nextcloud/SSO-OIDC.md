# Single Sign-On SAML

- [Single Sign-On SAML](#single-sign-on-saml)
  - [Keycloak OIDC Configuration](#keycloak-oidc-configuration)
    - [Create client](#create-client)
    - [Update Settings](#update-settings)
    - [Create Roles (aka Groups)](#create-roles-aka-groups)
    - [Create Mappers (case-sensitive)](#create-mappers-case-sensitive)
    - [Manage Scope](#manage-scope)
  - [Nextcloud OIDC Configuration](#nextcloud-oidc-configuration)
    - [General Settings](#general-settings)
    - [Custom OpenID Connect](#custom-openid-connect)
    - [Add Group Mappings](#add-group-mappings)
  - [Test](#test)
  - [Resources](#resources)
    - [With Social Login](#with-social-login)
    - [With OIDC Login](#with-oidc-login)

## Keycloak OIDC Configuration

**NOTE:** OIDC single sign-on still seems to have some hitches
(i.e., usernames not parsed correctly, differences between serverside and IdP links, etc).
Therefore, SAML SSO is currently the preferred method.

### Create client

1. Ensure configuring for a `non-master` realm
2. Client > Create
3. `Client ID`: `nextcloud-oidc`
4. `Client Protocol`: `openid-connect`
5. `Root URL`: `https://<NEXTCLOUD_ADDRESS>/`

### Update Settings

1. Set `Access Type`: `confidential`
2. Add `Root URL`: `https://<NEXTCLOUD_ADDRESS>/`
3. Set `Valid Redirect URIs` to a url glob: `https://<NEXTCLOUD_ADDRESS>/*`
4. Save!

<!-- ### Update Keys

Import `public.cert` (generated above) as `Certificate PEM` format file -->

### Create Roles (aka Groups)

`Roles` created unter the Client will map to Groups within the Nextcloud application.
Suggest creating at least `admin` and `user` Roles/Groups.

### Create Mappers (case-sensitive)

```txt
Name: username
Mapper Type: User Property
Property: username
Token Claim Name: sub
Claim JSON Type: String
Add to ID token: On
Add to access token: On
Add to userinfo: On
```

> In Nextcloud, the username will be `keycloak-<USERNAME>`, but displayname will still be username

```txt
Name: email
Mapper Type: User Property
Property: email
Token Claim Name: email
Claim JSON Type: String
Add to ID token: On
Add to access token: On
Add to userinfo: On
```

```txt
Name: roles
Mapper Type: User Client Role
Client ID: nextcloud-openid # or whatever was set in Client setup
Client Role prefix: '' # blank
Multivalued: On
Token Claim Name: roles
Claim JSON Type: String
Add to ID token: On
Add to access token: On
Add to userinfo: On
```

> In addition the Single Role Attribute option needs to be enabled in a different section.
> Navigate to Configure > Client scopes > role_list > Mappers > role_list and toggle the Single Role Attribute to On.

```txt
Name: nextcloudquota
Mapper Type: User Attribute
User Attribute: nextcloudquota
Token Claim Name: nextcloudquota
Claim JSON Type: String
Add to ID token: On
Add to access token: On
Add to userinfo: On
Multivalued: Off
Aggregate attribute values: Off
```

> To set `nextcloudquota`, add it as a key per-user (or per-group) in Keycloak:
> _Note that these are **keycloak** users and groups, not **client**_
> Users > Edit > Attributes
> Key: `nextcloudquota`
> Value: `10 GB` (or whatever quota you wish to set)

### Manage Scope

To prevent global / realm-level roles from being set within the client application,
set `Full Scope Allowed`: False/Off

## Nextcloud OIDC Configuration

Install [Social Login](https://apps.nextcloud.com/apps/sociallogin) app in Nextcloud
For a more minimal install (not discussed in this guide) see [OIDC Login](https://apps.nextcloud.com/apps/oidc_login)

### General Settings

[ ] Disable auto create new users
[ ] Create users with disabled account
[ ] Allow users to connect social logins with their account
[x] Prevent creating an account if the email address exists in another account
[x] Update user profile every login
[ ] Do not prune not available user groups on login
[ ] Automatically create groups if they do not exist _This may propagate group names with `keycloak-` prefix_
[x] Restrict login for users without mapped groups
[x] Restrict login for users without assigned groups
[ ] Disable notify admins about new users
[x] Hide default login

### Custom OpenID Connect

> URLs can be found in the realm OpenID Configuration page (REALM > General > Endpoints > OpenID Endpoint Configuration)
> Generally in the format `https://<KEYCLOAK_ADDRESS>/auth/realms/<REALM_NAME>/protocol/openid-connect/<ENDPOINT>`

`Authorize URL`: `authorization_endpoint` from the realm OpenID Configuration page
`Token URL`: - `token_endpoint` from the realm OpenID Configuration page
`User info URL`: - `userinfo_endpoint`  from the realm OpenID Configuration page
`Logout URL`: - `end_session_endpoint` from the realm OpenID Configuration page
`Client Id`: `client-id` from keycloak configuration
`Client Secret`: Found in `Clients > Nextcloud-OpenID > Credentials > Secret`
`Scope`: openid
`Groups claim`: `roles` or name of role mapper

### Add Group Mappings

Add mapping from Keycloak:Nextcloud role:group names

## Test

```sh
# Setttings
KEYCLOAK_HOST=''
KEYCLOAK_USERNAME=''
KEYCLOAK_PASSWORD=''
KEYCLOAK_REALM=''
KEYCLOAK_CLIENT_SECRET=''
CLIENT_ID=''

# Get token
TOKEN=$(curl -s \
-d "client_id=$CLIENT_ID" \
-d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
-d "username=$KEYCLOAK_USERNAME" \
-d "password=$KEYCLOAK_PASSWORD" \
-d "grant_type=password" \
"https://$KEYCLOAK_HOST/auth/realms/$KEYCLOAK_REALM/protocol/openid-connect/token" | jq -r '.access_token')

# Use token to get userinfo
curl \
-H "Authorization: bearer $TOKEN" \
https://$KEYCLOAK_HOST/auth/realms/$KEYCLOAK_REALM/protocol/openid-connect/userinfo
```

## Resources

### With [Social Login](https://apps.nextcloud.com/apps/sociallogin)

[authenticating nextcloud with keycloak using openid-connect](https://blog.w3asel.com/2019/10/authenticating-nextcloud-with-keycloak-using-openid-connect/)
[openid-connect w nextcloud & keycloak](https://janikvonrotz.ch/2020/10/20/openid-connect-with-nextcloud-and-keycloak/)
[nextcloud part 3 SSO with keycloak](https://blog.lachlanlife.net/nextcloud-part-3-single-sign-on-with-keycloak/)

### With [OIDC Login](https://apps.nextcloud.com/apps/oidc_login)

[keycloak with 2fa as nextcloud-backend](https://blog.laubacher.io/keycloak-with-2fa-as-nextcloud-backend)
[sso with nextcloud & keycloak](https://blog.lachlanlife.net/nextcloud-part-3-single-sign-on-with-keycloak/)
