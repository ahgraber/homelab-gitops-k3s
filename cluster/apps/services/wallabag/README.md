# Wallabag

[wallabag](https://wallabag.org/en) is a self hostable application for saving web pages:
Save and classify articles.
Read them later.
Freely.

Reference:

- [documentation](https://doc.wallabag.org/en/)
- [console commands](https://doc.wallabag.org/en/admin/console_commands.html)

## Debugging

### Initialize database

Per [github issue](https://github.com/wallabag/docker/issues/242),
may have to manually initialize external postgres db.
In wallabag pod, run:

```sh
/var/www/wallabag/bin/console wallabag:install --env=prod
```

### Create User

In wallabag pod, run:

```sh
# add a user with username, email, password
/var/www/wallabag/bin/console fos:user:create <username> <email> <password> --env=prod
# give user admin rights
/var/www/wallabag/bin/console fos:user:promote --super <username> --env=prod
```
