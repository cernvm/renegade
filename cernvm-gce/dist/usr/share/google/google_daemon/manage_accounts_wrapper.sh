#!/bin/sh

DAEMON=/usr/share/google/google_daemon/manage_accounts.py

logger -- "GCE: starting account manager with options $@"
exec $DAEMON $@
