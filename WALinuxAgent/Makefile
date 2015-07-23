
include $(TOP)/config.mk
EXTRA_SOURCES = dist/usr/bin/pubkey2ssh
include $(TOP)/generic.mk
SOURCE_DIST = ./usr ./etc ./var
include $(TOP)/template-spec.mk
include $(TOP)/from-git.mk

dist/usr/bin/pubkey2ssh: pubkey2ssh.c
	gcc -o dist/usr/bin/pubkey2ssh pubkey2ssh.c -lcrypto

