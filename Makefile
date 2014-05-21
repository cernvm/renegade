
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	acroread \
	CERN-CA-certs \
	CASTOR-client \
	castor-lib \
	castor-stager-clientold \
	castor-rtcopy-client \
	castor-upv-client \
	castor-rtcopy-messages \
	castor-ns-client \
	castor-stager-client \
	castor-vdqm2-client \
	castor-rfio-client \
	castor-vmgr-client \
	castor-devel \
	castor-tape-client \
	cernvm-config \
	condor \
	ld.so \
	libc

PACKAGES-32BIT = $(wildcard *-i686)

default: all
	$(MAKE) repo

$(PACKAGES)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

$(PACKAGES-32BIT)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

all clean : $(PACKAGES) 

repo: $(YUM_REPO)/repodata/repomd.xml
$(YUM_REPO)/repodata/repomd.xml: $(wildcard $(YUM_REPO)/*.rpm)
	createrepo -d -s sha $(YUM_REPO) --workers=12

