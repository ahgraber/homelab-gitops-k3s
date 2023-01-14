# Scrutiny

[Scrutiny](https://github.com/AnalogJ/scrutiny) is a utility that provides storage drive S.M.A.R.T monitoring,
historic trends, and real-world failure thresholds.

Scrutiny is deployed as hub-and-spoke format, where the web gui is hosted on k8s,
a collector runs as a replicaset on nodes where rook-ceph drives are hosted,
and a collector also runs on TrueNAS

See [supported OSes](https://github.com/AnalogJ/scrutiny/blob/master/docs/SUPPORTED_NAS_OS.md)
and the [TrueNAS-specific instructions](https://blog.stefandroid.com/2022/01/14/smart-scrutiny.html)
