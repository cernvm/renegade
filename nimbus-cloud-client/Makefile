
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	wget -O tmp.tar.gz http://www.nimbusproject.org/downloads/$(NAME)-$(VERSION).tar.gz
	mv tmp.tar.gz $(SOURCE_TARBALL)

$(SPEC_FILE): nimbus-cloud-client.spec version release | $(RPMTOP)/SPECS
	cat nimbus-cloud-client.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
