
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl http://ecsft.cern.ch/dist/cernvm/openafs-1.6.2.1-src.tar.gz > $(SOURCE_TARBALL)	

$(SPEC_FILE): $(NAME).spec version release | $(RPMTOP)/SPECS
	cat $(NAME).spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
