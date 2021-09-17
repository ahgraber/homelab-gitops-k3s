#!/bin/bash

# get current PV names from cluster
export local_PVs=($(kubectl get pv -A | awk '{print $1}' | grep "pvc"))
printf '%s\n' "${local_PVs[@]}"

# Variables contained in an unescaped or unquoted heredoc will be expanded
# by the *local* shell *before* the local shell executes the ssh command
# The solution is to use an escaped or single-quoted heredoc, <<\EOF or <<'EOF'
# or only escape the variables in the heredoc that should *not* be expanded locally
# Thus, 'local_PVs' does NOT get escaped; all other variables DO get escaped
ssh root@truenas.ninerealmlabs.com 'bash -s' << EOF
# transfer variable data
export PVs=(${local_PVs[*]})
echo "Current PVs:"
printf '%s\n' "\${PVs[@]}"

PREFIX=(
  "ssdpool/csi/ixi/v/"
  "ssdpool/csi/nfs/v/"
)

for PFX in \${PREFIX[@]}; do
  echo "PREFIX: \${PFX}"

  # get list of current zvols with PFX prefix
  VOLs=(\$(zfs list | grep "\${PFX}" | awk '{print \$1}' | sed "s|\${PFX}||"))

  # get differences (OLD are VOLs that exist but that are not in current PVs)
  # ref: https://unix.stackexchange.com/questions/104837/intersection-of-two-arrays-in-bash
  OLD=(\$(comm -13 <(printf '%s\n' "\${PVs[@]}" | LC_ALL=C sort) <(printf '%s\n' "\${VOLs[@]}" | LC_ALL=C sort)))

  if [[ \${#OLD[@]} -eq \${#VOLs[@]} ]]; then
    echo "No difference between OLD and VOLs, skipping removal"
  else
    for OLDVOL in \${OLD[@]}; do
      echo "Removing vol: \${PFX}\${OLDVOL}"
      zfs destroy -rf "\${PREFIX}\${OLDVOL}"
    done
  fi
done
unset PVs
unset PREFIX
unset VOLs
unset OLD
EOF
