
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	cernvm-config 

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

