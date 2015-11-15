
include $(TOP)/config.mk
EXTRA_SOURCES = $(RPMTOP)/SOURCES/vmware-guestd.init
EXTRA_SOURCES2 = $(RPMTOP)/SOURCES/network.patch
EXTRA_SOURCES3 = $(RPMTOP)/SOURCES/vmware-guestd.service
include $(TOP)/generic.mk

$(NAME)-$(VERSION)-3000743.tar.gz:
	curl https://ecsft.cern.ch/dist/cernvm/$(NAME)-$(VERSION)-3000743.tar.gz > $(NAME)-$(VERSION)-3000743.tar.gz

$(SOURCE_TARBALL): $(NAME)-$(VERSION)-3000743.tar.gz | $(RPMTOP)/SOURCES
	cat $(NAME)-$(VERSION)-3000743.tar.gz > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): $(EXTRA_SOURCES2) $(EXTRA_SOURCES3) | $(RPMTOP)/SOURCES
	cat vmware-guestd.init > $(EXTRA_SOURCES)

$(EXTRA_SOURCES2): | $(RPMTOP)/SOURCES
	cat network.patch > $(EXTRA_SOURCES2)

$(EXTRA_SOURCES3): | $(RPMTOP)/SOURCES
	cat vmware-guestd.service > $(EXTRA_SOURCES3)

$(SPEC_FILE): open-vm-tools.spec version release | $(RPMTOP)/SPECS
	cat open-vm-tools.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
