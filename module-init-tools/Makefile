
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl https://www.kernel.org/pub/linux/utils/kernel/module-init-tools/$(NAME)-$(VERSION).tar.gz > $(SOURCE_TARBALL)	

$(SPEC_FILE): module-init-tools.spec version release | $(RPMTOP)/SPECS
	cat module-init-tools.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/AUTO_XROOTD_VERSION/$(XROOTD_VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
