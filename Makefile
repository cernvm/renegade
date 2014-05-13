
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	amiconfig-rpath \
	amiconfig-cernvm \
	amiconfig-hepix \
	bootlogd \
	CERN-CA-certs \
	cern-cloudinit-modules \
	cernvm-config \
	cernvm-gce \
	cernvm-pam \
	cernvm-patches \
	cernvm-theme \
	cernvm-release \
	cernvm-online-guest \
	cernvm-update \
	condor \
	cpan2rpm \
	google-cloud-sdk \
	module-init-tools \
	slim \
	vboxguest

PACKAGES-32BIT = $(wildcard *-i686)

default: all
	$(MAKE) repo

$(PACKAGES)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

$(PACKAGES-32BIT)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

all clean : $(PACKAGES) $(PACKAGES-32BIT)

repo: $(YUM_REPO)/repodata/repomd.xml
$(YUM_REPO)/repodata/repomd.xml: $(wildcard $(YUM_REPO)/*.rpm)
	createrepo -d -s sha $(YUM_REPO)

