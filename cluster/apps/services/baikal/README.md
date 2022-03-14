# [Baikal](https://sabre.io/baikal/)

Baïkal is a lightweight CalDAV+CardDAV server.
It offers an extensive web interface with easy management of users, address books and calendars.
It is fast and simple to install and only needs a basic php capable server.
The data can be stored in a MySQL or a SQLite database.

## Configuration

May have to set permissions on mounted volumes [ref](https://github.com/ckulka/baikal-docker/blob/master/examples/docker-compose.localvolumes.yaml):

```sh
kubectl exec -it <baikal-pod-name> -n <baikal-namespace> bash
...
cd /var/www/baikal
chown -R 101:101 config Specific # for nginx
chmod -R 766 config Specific
mkdir -p Specific/db
```
