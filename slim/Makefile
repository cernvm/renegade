
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/slim.conf
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl http://pkgs.fedoraproject.org/repo/pkgs/slim/slim-1.3.5.tar.gz/1153e6993f9c9333e4cf745411d03472/$(NAME)-$(VERSION).tar.gz > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): slim.conf | $(RPMTOP)/SOURCES
	cp slim.conf $(EXTRA_SOURCES)

$(SPEC_FILE): slim.spec version release | $(RPMTOP)/SPECS
	cat slim.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/AUTO_XROOTD_VERSION/$(XROOTD_VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
