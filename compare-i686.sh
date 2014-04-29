#!/bin/sh

fix=0
if [ "x$1" = "x-f" ]; then
  echo "Fixing versions"
  fix=1
fi

for compat in *-i686; do
  remote=$(echo $compat | sed s/-i686$/.i686/)  
  rversion=$(repoquery -q --qf "%{version}-%{release}\n" $remote)
  lversion="$(cat $compat/version)-$(cat $compat/release)"
  if [ "x$lversion" != "x$rversion" ]; then
    echo "$compat    $lversion    $rversion"
    if [ $fix -eq 1 ]; then 
      new_version=$(repoquery -q --qf "%{version}" $remote)
      new_release=$(repoquery -q --qf "%{release}" $remote)
      echo $new_version > $compat/version
      echo $new_release > $compat/release
      echo "   ...bumped to $(cat $compat/version)-$(cat $compat/release)"
    fi
  fi
done
