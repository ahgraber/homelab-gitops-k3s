# [Memos](https://usememos.com/)

An open source, lightweight note-taking service. Easily capture and share your great thoughts.

## Storage

Memos is currently using postgres for storage -- including files and images.
This is suggested for when text > image content. If lots of images or video are added, consider changing to S3.

See [Choosing a Storage for Your Resource: Database, S3 or Local Storage? - Memos](https://www.usememos.com/blog/choosing-a-storage-for-your-resource) for more info.

## Auth

For OAUTH/OIDC integration, first configure LLDAP/Authelia, then [configure the OAUTH2 endpoint in-app](https://github.com/usememos/memos/issues/528).
