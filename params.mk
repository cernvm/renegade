
RPMTOP = /data/rpmbuild
YUMBASE = /var/www/yum/cernvm/extras
UPSTREAM_VERSION = 4
HOSTARCH = i386

DISTTAG = el$(UPSTREAM_VERSION)
YUM_REPO = $(YUMBASE)/$(UPSTREAM_VERSION)/$(HOSTARCH)

