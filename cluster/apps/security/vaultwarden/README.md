# Vaultwarden

Vaultwarden is a lightweight Bitwarden client written in Rust.

## Prerequisites

To use an existing sql server:

1. Create 'vaultwarden' database and account on server.  `phpmyadmin` is included in the gitops repo to access the mariadb sql server.  It will be easiest to try to create the `vaultwarden` user and select the _"Create database with same name and grant all privileges"_ checkbox during user creation

2. Provide connection string as secret

   > _If db is in different namespace, use <db_service_name>.<db_namespace>:<db_port> as address_
   > Since we're using mariadb, the connection string is something like:
   > `mysql://vaultwarden:{VAULTWARDEN_USER_PASSWORD}@mariadb-galera.mariadb:3306/vaultwarden`

## Setup

To create a new user, log in with admin token at `vaultwarden.domain.com/admin` (the service may take a few minutes to start up).  In the admin pane, you can invite a user via email.