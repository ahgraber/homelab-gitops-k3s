#!/bin/bash

# get current PV names from cluster
PVs=($(kubectl get pv -A | awk '{print $1}' | grep "pvc"))


###   ISCSI   ###
PREFIX="ssdpool/csi/ixi/v/"
# get list of current iscsi zvols
ISCSIs=($(zfs list | grep "${PREFIX}" | awk '{print $1}' | sed "s|${PREFIX}||"))

# get differences
OLD=($(echo ${ISCSIs[@]} ${PVs[@]} | tr ' ' '\n' | sort | uniq -u))

for dat in ${OLD[@]}; do
  echo "Removing ${PREFIX}${dat}"
  zfs destroy -rf "${PREFIX}${dat}"
done


###   NFS   ###
PREFIX="ssdpool/csi/nfs/v/"
# get list of current nfs zvols
NFSs=($(zfs list | grep "${PREFIX}" | awk '{print $1}' | sed "s|${PREFIX}||"))

# get differences
OLD=($(echo ${NFSs[@]} ${PVs[@]} | tr ' ' '\n' | sort | uniq -u))

for dat in ${OLD[@]}; do
  echo "Removing ${PREFIX}${dat}"
  zfs destroy -rf "${PREFIX}${dat}"
done