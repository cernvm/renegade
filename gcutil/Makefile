
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl https://google-compute-engine-tools.googlecode.com/files/$(NAME)-$(VERSION).tar.gz > $(SOURCE_TARBALL)	

$(SPEC_FILE): gcutil.spec version release | $(RPMTOP)/SPECS
	cat gcutil.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/AUTO_XROOTD_VERSION/$(XROOTD_VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
