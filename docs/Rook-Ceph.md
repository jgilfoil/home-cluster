# Rook-Ceph Notes

## Maintenance

### Start Maintenance mode
```
ceph osd set noout
ceph osd set nobackfill
ceph osd set norecover
```

### End Maintenance mode
```
ceph osd unset noout
ceph osd unset nobackfill
ceph osd unset norecover
```

## Troubleshooting

### Abandoned OSDs

Sometimes we'll see older OSD's still in the osd tree:
```sh
bash-4.4$ ceph osd tree
ID  CLASS  WEIGHT   TYPE NAME           STATUS  REWEIGHT  PRI-AFF
-1         2.72910  root default                                 
-7         0.90970      host odroid-01                           
 9    ssd  0.90970          osd.9           up   1.00000  1.00000
-3         0.90970      host odroid-02                           
10    ssd  0.90970          osd.10          up   1.00000  1.00000
-5         0.90970      host odroid-03                           
11    ssd  0.90970          osd.11          up         0  1.00000
 1               0  osd.1                 down         0  1.00000
 2               0  osd.2                 down         0  1.00000
 3               0  osd.3                 down         0  1.00000
 4               0  osd.4                 down   1.00000  1.00000
 5               0  osd.5                 down   1.00000  1.00000
 6               0  osd.6                 down   1.00000  1.00000
 7               0  osd.7                 down   1.00000  1.00000
 8               0  osd.8                 down   1.00000  1.00000
```
1-8 are old osd's here that didn't get cleaned up.

If we want to remove them, make sure there's no data on them:

```sh
bash-4.4$ ceph osd df
ID  CLASS  WEIGHT   REWEIGHT  SIZE     RAW USE  DATA     OMAP     META     AVAIL    %USE  VAR   PGS  STATUS
 9    ssd  0.90970   1.00000  932 GiB   82 GiB   80 GiB  141 KiB  1.9 GiB  850 GiB  8.80  1.00   33      up
10    ssd  0.90970   1.00000  932 GiB   82 GiB   80 GiB  244 KiB  2.0 GiB  849 GiB  8.82  1.00   33      up
11    ssd  0.90970         0      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0      up
 0               0         0      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 1               0         0      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 2               0         0      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 3               0         0      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 4               0   1.00000      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 5               0   1.00000      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 6               0   1.00000      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 7               0   1.00000      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 8               0   1.00000      0 B      0 B      0 B      0 B      0 B      0 B     0     0    0    down
 ```
 If no data, then they can be deleted.
 ```sh
# if they're not already marked down
ceph osd down osd.1 
ceph osd crush remove osd.1
ceph auth del osd.1
ceph osd rm osd.1
```
Repeat those commands for each osd you want to remove or:
```sh
for i in {0..8}; do
  ceph osd down osd.$i
  ceph osd crush remove osd.$i
  ceph auth del osd.$i
  ceph osd rm osd.$i
done
```