
include $(TOP)/config.mk
EXTRA_SOURCES = $(RPMTOP)/SOURCES/vmware-guestd.init
EXTRA_SOURCES2 = $(RPMTOP)/SOURCES/network.patch
include $(TOP)/generic.mk

$(NAME)-$(VERSION)-1280544.tar.gz:
	curl http://ecsft.cern.ch/dist/cernvm/$(NAME)-$(VERSION)-1280544.tar.gz > $(NAME)-$(VERSION)-1031360.tar.gz

$(SOURCE_TARBALL): $(NAME)-$(VERSION)-1280544.tar.gz | $(RPMTOP)/SOURCES
	cat $(NAME)-$(VERSION)-1280544.tar.gz > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): $(EXTRA_SOURCES2) | $(RPMTOP)/SOURCES
	cat vmware-guestd.init > $(EXTRA_SOURCES)

$(EXTRA_SOURCES2): | $(RPMTOP)/SOURCES
	cat network.patch > $(EXTRA_SOURCES2)

$(SPEC_FILE): open-vm-tools.spec version release | $(RPMTOP)/SPECS
	cat open-vm-tools.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
