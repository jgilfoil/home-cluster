#!/usr/bin/env bash

DISK="/dev/sda"

sudo sgdisk --zap-all $DISK
sudo dd if=/dev/zero of="$DISK" bs=1M count=100 oflag=direct,dsync
sudo blkdiscard $DISK
sudo partprobe $DISK

sudo rm -rf /dev/ceph-*
sudo rm -rf /dev/mapper/ceph--*