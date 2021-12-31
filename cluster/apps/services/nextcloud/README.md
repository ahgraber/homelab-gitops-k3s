# Nextcloud

- [Nextcloud](#nextcloud)
  - [Single Sign-On (SSO)](#single-sign-on-sso)
    - [OIDC](#oidc)
    - [SAML](#saml)
      - [Nextcloud SAML Configuration](#nextcloud-saml-configuration)
        - [_initial_ Global settings](#initial-global-settings)
        - [Service Provider Data](#service-provider-data)
        - [Identity Provider (IdP) Data](#identity-provider-idp-data)
        - [Attribute Mapping](#attribute-mapping)
        - [Security Settings](#security-settings)
      - [Keycloak SAML Configuration](#keycloak-saml-configuration)
        - [Create client](#create-client)
        - [Update Settings](#update-settings)
        - [Update Keys](#update-keys)
        - [Create Roles (aka Groups)](#create-roles-aka-groups)
        - [Create Mappers (case-sensitive)](#create-mappers-case-sensitive)
        - [Manage Scope](#manage-scope)

## Single Sign-On (SSO)

**Goal:** Managed all users from a single location, and allow users to only require
managing a single user profile across disparate webapps

Users and their permissions will be managed in [Keycloak](../../security/keycloak/README.md)

### OIDC

[openid-connect w nextcloud & keycloak](https://janikvonrotz.ch/2020/10/20/openid-connect-with-nextcloud-and-keycloak/)
[sso with nextcloud & keycloak](https://blog.lachlanlife.net/nextcloud-part-3-single-sign-on-with-keycloak/)

### SAML

[nextcloud sso with keycloak](https://www.muehlencord.de/wordpress/2019/12/14/nextcloud-sso-using-keycloak/)
[Configure SAML Authentication for Nextcloud with Keycloak](https://janikvonrotz.ch/2020/04/21/configure-saml-authentication-for-nextcloud-with-keycloack/)

#### Nextcloud SAML Configuration

Install [SSO & SAML Authentication](https://apps.nextcloud.com/apps/user_saml) app in Nextcloud

##### _initial_ Global settings

[ ] Only allow authentication if an account exists on some other backend (e.g. LDAP)
[ ] Use SAML auth for the Nextcloud desktop clients (requires user re-authentication)
[x] Allow the use of multiple user back-ends (e.g. LDAP)

##### Service Provider Data

Name ID Format: `unspecified`

1. Generate cert and key with

   ```sh
   openssl req  -nodes -new -x509  -keyout private.key -out public.cert
   ```

2. Copy text from `private.key` and `public.cert` to input boxes and ensure headings are included

   ```txt
   -----BEGIN CERTIFICATE-----
   <PUBLIC_CERT_STRING>
   -----END CERTIFICATE-----
   ```

   ```txt
   -----BEGIN PRIVATE KEY-----
   <PRIVATE_KEY_STRING>
   -----END PRIVATE KEY-----
   ```

##### Identity Provider (IdP) Data

- Identifier of the IdP:

  ```txt
  https://<KEYCLOAK_ADDRESS>/auth/realms/<REALM_NAME>
  ```

- URL Target of the IdP where the SP will send the Authentication Request Message:

  ```txt
  https://<KEYCLOAK_ADDRESS>/auth/realms/<REALM_NAME>/protocol/saml
  ```

- URL Location of IdP where the SP will send the SLO Request:

  ```txt
  https://<KEYCLOAK_ADDRESS>/auth/realms/<REALM_NAME>/protocol/saml
  ```

- Public X.509 certificate of the IdP:
  Copy the RSA certificate string from Keycloak: REALM_NAME > Configure / Realm Settings > Keys (tab)

  Ensure headers are included

  ```txt
  -----BEGIN CERTIFICATE-----
  <PUBLIC_CERT_STRING>
  -----END CERTIFICATE-----
  ```

##### Attribute Mapping

- Attribute to map the displayname to: `username`
- Attribute to map the email address to: `email`
- Attribute to map the user groups to: `roles`
- Attribute to map the quota to: `nextcloudquota`

##### Security Settings

Signatures and encryption offered
[ ] Indicates that the nameID of the `logoutRequest` sent by this SP will be encrypted
[x] Indicates wiether the `AuthnRequest` messages sent by this SP will be signed
    [Metadata of the SP will offer this info]
[x] Indicates whether the `logoutRequest` messages sent by this SP will be signed
[x] Indicates whether the `logoutResponse` messages sent by this SP will be signed
[ ] Whether the metadata should be signed

Signatures and encryption required
[x] Indicates a requirement for the `Response`, `LogoutRequest`, and `LogoutResponse`
    elements received by this SP to be signed
[x] Indicates a requirement for the `Assertion` elements received by this SP to be signed
    [Metadata of the SP will offer this info]
[ ] Indicates a requirement for the `Assertion` elements received by this SP to be encrypted
[ ] Indicates a requirement for the NameID element of the SAMLResponse received by this SP to be present
[ ] Indicates a requirement for the NameID received by this SP to be encrypted
[ ] Indicates if the SP will validate all received XML

> At this point, Nextcloud configuration is complete.
> Select `Download metadata XML` at bottom of settings page and save locally

#### Keycloak SAML Configuration

##### Create client

1. Ensure configuring for a `non-master` realm
2. Client > Create
3. Import the `metadata.xml` file that was exported from Nextcloud
4. `Client ID` should be a URL like `https://<NEXTCLOUD_ADDRESS>/apps/user_saml/saml/metadata`
5. `Client SAML Endpoint` should be set to `https://<KEYCLOAK_ADDRESS>/auth/realm/<REALM_NAME>`

##### Update Settings

1. Set `Name ID Format`: `username`
2. Add `Root URL`: `https://<NEXTCLOUD_ADDRESS>/`
3. Update `Valid Redirect URIs` to a url glob: `https://<NEXTCLOUD_ADDRESS>/*`

##### Update Keys

Import `public.cert` (generated above) as `Certificate PEM` format file

##### Create Roles (aka Groups)

`Roles` created unter the Client will map to Groups within the Nextcloud application.
Suggest creating at least `admin` and `user` Roles/Groups.

##### Create Mappers (case-sensitive)

```txt
Name: username
Mapper Type: User Property
Property: username
Friendly Name: username
SAML Attribute Name: username
SAML Attribute NameFormat: Basic
```

```txt
Name: email
Mapper Type: User Property
Property: email
Friendly Name: email
SAML Attribute Name: email
SAML Attribute NameFormat: Basic
```

```txt
Name: roles
Mapper Type: Role List
Role attribute name: roles
Friendly Name: roles
SAML Attribute NameFormat: Basic
Single Role Attribute: On
```

> In addition the Single Role Attribute option needs to be enabled in a different section.
> Navigate to Configure > Client scopes > role_list > Mappers > role_list and toggle the Single Role Attribute to On.

```txt
Name: nextcloudquota
Mapper Type: User Attribute
User Attribute: nextcloudquota
Friendly Name: nextcloudquota
SAML Attribute NameFormat: Basic
```

> To set `nextcloudquota`, add it as a key per-user (or per-group) in Keycloak:
> _Note that these are **keycloak** users and groups, not **client**_
> Users > Edit > Attributes
> Key: `nextcloudquota`
> Value: `10 GB` (or whatever quota you wish to set)

##### Manage Scope

To prevent global / realm-level roles from being set within the client application,
set `Full Scope Allowed`: False/Off
