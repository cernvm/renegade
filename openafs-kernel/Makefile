
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL):
	echo "Not needed" > $(SOURCE_TARBALL)

$(SPEC_FILE): openafs-kernel.spec version release | $(RPMTOP)/SPECS
	cat openafs-kernel.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
