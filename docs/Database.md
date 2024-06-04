# Database Topics

## Cloudnative Postgres

### Recovery Steps

First, delete the original clusterxx.yaml deployment.

Then uncomment these lines in the clusterxx.yaml
```
  bootstrap:
    recovery:
      source: &previousCluster postgres16-v6

  externalClusters:
    - name: *previousCluster
      barmanObjectStore:
        <<: *barmanObjectStore
        serverName: *previousCluster
```

The `boostrap.recovery.source` value should be the previous cluster name, in this example `postgres16-v6`.

Update the `backup.serverName` value to iterate the version. In the below example, `postgres16-v6` was the previous version, so we make it `postgres16-v7`.

```
  backup:
    retentionPolicy: 30d
    barmanObjectStore: &barmanObjectStore
      data:
        compression: bzip2
      wal:
        compression: bzip2
        maxParallel: 8
      destinationPath: s3://cnpg/
      endpointURL: http://minio.storage.svc.cluster.local:9000
      # Note: serverName version needs to be incremented
      # when recovering from an existing cnpg cluster
      serverName: &currentCluster postgres16-v7
```

Deploy, and profit.

### Test Database connections

Update the `tests/database/postgres-cli.yaml` password env var and deploy.
```
kubectl apply -f tests/database/postgres-cli.yaml
```

shell into the pod in k9s and test
```
psql -h postgres16-rw.database.svc.cluster.local -U postgres
root@postgres-cli:/# psql -h postgres16-rw.database.svc.cluster.local -U postgres
psql (16.3 (Debian 16.3-1.pgdg120+1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
Type "help" for help.

postgres=# \l
                                                  List of databases
   Name    |  Owner   | Encoding | Locale Provider | Collate | Ctype | ICU Locale | ICU Rules |   Access privileges   
-----------+----------+----------+-----------------+---------+-------+------------+-----------+-----------------------
 app       | app      | UTF8     | libc            | C       | C     |            |           | 
 postgres  | postgres | UTF8     | libc            | C       | C     |            |           | 
 template0 | postgres | UTF8     | libc            | C       | C     |            |           | =c/postgres          +
           |          |          |                 |         |       |            |           | postgres=CTc/postgres
 template1 | postgres | UTF8     | libc            | C       | C     |            |           | =c/postgres          +
           |          |          |                 |         |       |            |           | postgres=CTc/postgres
 testdb    | postgres | UTF8     | libc            | C       | C     |            |           | 
(5 rows)

postgres=# \c testdb
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
You are now connected to database "testdb" as user "postgres".
testdb=# \dt
           List of relations
 Schema |   Name    | Type  |  Owner   
--------+-----------+-------+----------
 public | testtable | table | postgres
(1 row)

testdb=# select * from testtable;
 id |   name   
----+----------
  1 | testname
(1 row)

testdb=# \q
root@postgres-cli:/# 
```
