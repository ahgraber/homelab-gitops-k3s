# Scrutiny

[Scrutiny](https://github.com/AnalogJ/scrutiny) is a utility that provides storage drive S.M.A.R.T monitoring,
historic trends, and real-world failure thresholds.

Scrutiny is deployed as hub-and-spoke format, where the web gui is hosted on k8s,
a collector runs as a replicaset on nodes where rook-ceph drives are hosted,
and a collector also runs on TrueNAS

See [supported OSes](https://github.com/AnalogJ/scrutiny/blob/master/docs/SUPPORTED_NAS_OS.md)

## Application

Scrutiny is deployed as 3 distinct components:

1. `helmrelease-scrutiny` is the web application front end and data collection endpoint
2. `helmrelease-influxdb` stores the data
3. `helmrelease-collector` deploys a daemonset so that each k8s node can log SMART data to Scrutiny

## [TrueNAS setup](https://github.com/AnalogJ/scrutiny/blob/master/docs/INSTALL_HUB_SPOKE.md)

> Add'l references:
>
> - [docker-compose](https://github.com/AnalogJ/scrutiny/blob/master/docker/example.hubspoke.docker-compose.yml)
> - [Monitor the Health of Multiple SMART Disks with Scrutiny | Stefandroid Blog](https://blog.stefandroid.com/2022/01/14/smart-scrutiny.html)
>
> NOTE: Scrutiny collector may need to be installed after every TrueNAS update!

1. Scrutiny needs Smartmontools version 7+. Check on the TrueNAS terminal that version 7 is installed.

   ```sh
   sudo su  # must be run as root!
   smartctl -V
   ```

2. Download the Collector agent binary (below link is for version 0.3.13 - the latest as of January 2022).
   Then copy it to `/usr/local` and make it executable. In short, execute the following as root:

   ```sh
   mkdir -p /mnt/ssdpool/Users/admin/scrutiny
   wget "https://github.com/AnalogJ/scrutiny/releases/latest/download/scrutiny-collector-metrics-$(uname | tr "[:upper:]" "[:lower:]")-amd64" -P /mnt/ssdpool/Users/admin/scrutiny/bin
   chmod +x /mnt/ssdpool/Users/admin/scrutiny/bin/scrutiny-collector-metrics-$(uname | tr "[:upper:]" "[:lower:]")-amd64
   ```

3. Create the configuration file by downloading the sample collector.yaml from the GitHub repo.

   ```sh
   mkdir -p /mnt/ssdpool/Users/admin/scrutiny/config
   wget https://raw.githubusercontent.com/AnalogJ/scrutiny/master/example.collector.yaml -O /mnt/ssdpool/Users/admin/scrutiny/config/collector.yaml
   ```

4. Edit the configuration and change the following parameters:

   - `host.id` should be an identifier for your TrueNAS server
   - `api.endpoint` should be the HTTP endpoint of the Scrutiny Web server that we deployed

   ```yaml
   version: 1
   host:
     id: truenas
   api:
     endpoint: https://scrutiny.${SECRET_DOMAIN}
   ```

5. Create a TrueNAS cron job (System Settings → Advanced → Cron Jobs):

   | Key         | Value                                                                                                                                                             |
   | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | Description | Scrutiny                                                                                                                                                          |
   | Command     | . /etc/profile; /mnt/ssdpool/Users/admin/scrutiny/bin/scrutiny-collector-metrics-linux-amd64 run --config /mnt/ssdpool/Users/admin/scrutiny/config/collector.yaml |
   | Run As User | root                                                                                                                                                              |
   | Schedule    | Hourly                                                                                                                                                            |
