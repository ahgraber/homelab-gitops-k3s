# Keycloak

Keycloak is an open source software product to allow single sign-on with
Identity and Access Management aimed at modern applications and services.

[Documentation](https://wjw465150.gitbooks.io/keycloak-documentation)
[Keycloak & OIDC](https://www.keycloak.org/docs/latest/securing_apps/#other-openid-connect-libraries)
[OpenID Connect (OIDC)](https://openid.net/connect/)
[OAuth 2.0](https://oauth.net/2/)

## Terminology

- IdP
- Authn
- Authz
- Realm
- Client
- Client Scope
- User: user account configuration
- Role: define a type of user and applications assign permission and access control to roles.
- Group: collections of users to which you can apply and manage roles and attributes

> Use groups to manage users. Use roles to manage applications and services.

## Setup

### Realm

The first time accessing Keycloak, we should set up a separate realm from `master`.
Hover over the `master` realm name toward the top left, and `add realm`.

### Users

### Roles

Roles can be defined at a realm level or a client level.

### Groups

### Client Scopes

#### Create `user` scope

1. In **non-Master** realm, select `Client Scopes`
2. On `Client Scopes` tab, select `create`
3. Create `user` scope
   1. With `Settings`:

      | Key | Value |
      |-----|-------|
      | Name | user |
      | Protocol | openid-connect|
      | Display on Consent Screen | Off / False |
      | Include in Token Scope | On / True |

   2. Create `Mapper` with values:

      | Key | Value |
      |-----|-------|
      | Name | preferred_username |
      | Mapper Type | User Property |
      | Property | preferred_username |
      | Token Claim Name | preferred_username |
      | Claim JSON Type | String |
      | Add to ID Token | On / True |
      | Add to Access Token | On / True |
      | Add to userinfo | On / True |

   3. Repeat above mapper, but set `Name` and `Token Claim Name` to `username`
      _Property should remain `preferred_username`_!

4. On `Default Client Scopes` tab, move `user` scope from `Available Client Scopes` to `Assigned Default Client Scopes`

### Clients
