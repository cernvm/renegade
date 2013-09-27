
include $(TOP)/config.mk

XROOTD_VERSION = 3.0.5
EXTRA_SOURCES = $(RPMTOP)/SOURCES/xrootd-$(XROOTD_VERSION).tar.gz
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl http://www.cse.nd.edu/~ccl/software/files/$(NAME)-$(VERSION)-source.tar.gz > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): | $(RPMTOP)/SOURCES
	curl http://xrootd.org/download/v$(XROOTD_VERSION)/xrootd-$(XROOTD_VERSION).tar.gz > $(EXTRA_SOURCES)

$(SPEC_FILE): cctools.spec version release | $(RPMTOP)/SPECS
	cat cctools.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/AUTO_XROOTD_VERSION/$(XROOTD_VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
