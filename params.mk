
RPMTOP = /data/rpmbuild
YUMBASE = /data/yum/cernvm/extras
UPSTREAM_VERSION = 6
HOSTARCH = x86_64

DISTTAG = el$(UPSTREAM_VERSION)
YUM_REPO = $(YUMBASE)/$(UPSTREAM_VERSION)/$(HOSTARCH)

