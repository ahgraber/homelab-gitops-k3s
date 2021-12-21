#!/bin/bash

# get current PV names from cluster
export local_PVs=($(kubectl get pv -A | awk '{print $1}' | grep "pvc"))
printf '%s\n' "${local_PVs[@]}"

# Variables contained in an unescaped or unquoted heredoc will be expanded
# by the *local* shell *before* the local shell executes the ssh command
# The solution is to use an escaped or single-quoted heredoc, <<\EOF or <<'EOF'
# or only escape the variables in the heredoc that should *not* be expanded locally
# Thus, 'local_PVs' does NOT get escaped; all other variables DO get escaped
# NOTE: Assumes truenas user has been added to sudoers file as NOPASSWD
ssh admin@truenas.ninerealmlabs.com 'bash -s' << EOF
# transfer variable data
export PVs=(${local_PVs[*]})
echo "Current PVs:"
printf '%s\n' "\${PVs[@]}"

PREFIX=("ssdpool/csi/ixi/v/" "ssdpool/csi/nfs/v/")

for PFX in \${PREFIX[@]}; do
  echo "PREFIX: \${PFX}"

  # get list of current zvols with PFX prefix
  VOLs=(\$(sudo zfs list | grep "\${PFX}" | awk '{print \$1}' | sed "s|\${PFX}||"))
  # echo "VOLs: \${VOLs[*]}"

  # get differences (OLD are VOLs that exist but that are not in current PVs)
  # ref: https://unix.stackexchange.com/questions/104837/intersection-of-two-arrays-in-bash
  OLD=(\$(comm -13 <(printf '%s\n' "\${PVs[@]}" | LC_ALL=C sort) <(printf '%s\n' "\${VOLs[@]}" | LC_ALL=C sort)))
  # echo "OLD: \${OLD[*]}"

  for OLDVOL in \${OLD[@]}; do
    echo "Removing vol: \${PFX}\${OLDVOL}"
    sudo zfs destroy -rf "\${PFX}\${OLDVOL}"
    sleep 1
  done
done
unset PVs
unset PREFIX
unset VOLs
unset OLD
exit
EOF
