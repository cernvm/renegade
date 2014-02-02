
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/cloud_admin
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	wget -O tmp.tar.gz http://pypi.python.org/packages/source/c/$(NAME)/$(NAME)-$(VERSION).tar.gz --no-check-certificate
	mv tmp.tar.gz $(SOURCE_TARBALL)

$(EXTRA_SOURCES): | $(RPMTOP)/SOURCES
	curl https://raw.github.com/hep-gc/$(NAME)/$(VERSION)/cloud_admin > $(EXTRA_SOURCES)

$(SPEC_FILE): cloud-scheduler.spec version release | $(RPMTOP)/SPECS
	cat cloud-scheduler.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
