
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/slim.conf
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl http://pkgs.fedoraproject.org/repo/pkgs/slim/slim-$(VERSION).tar.gz/d40d256394f9ef34cef34d2aa9cb52e6/$(NAME)-$(VERSION).tar.gz > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): slim.conf slimlock.conf | $(RPMTOP)/SOURCES
	cp slim.conf $(EXTRA_SOURCES)
	cp slimlock.conf $(RPMTOP)/SOURCES/slimlock.conf

$(SPEC_FILE): slim.spec version release | $(RPMTOP)/SPECS
	cat slim.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/AUTO_XROOTD_VERSION/$(XROOTD_VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
