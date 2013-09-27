#!/bin/sh

SRC=cern-vm-wi/cernvm-appliance-agent
DEST=src

pushd $SRC
tar cvfz setup.tar.gz etc/init.d/cernvm-appliance-agent usr/share/doc/cernvm-appliance-agent usr/libexec/cernvm-appliance-agent etc/cernvm-appliance-agent
popd
mv $SRC/setup.tar.gz $DEST/
cd $DEST
tar xvfz setup.tar.gz
rm -f setup.tar.gz

