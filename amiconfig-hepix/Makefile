
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/hepix.cfg
include $(TOP)/generic.mk

SVN_SRC = $(shell basename `cat source`)

$(SVN_SRC): source
	svn co `cat source`

$(SOURCE_TARBALL): $(SVN_SRC) | $(RPMTOP)/SOURCES
	cd $(SVN_SRC); \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): hepix.cfg | $(RPMTOP)/SOURCES
	cp hepix.cfg $(RPMTOP)/SOURCES

$(SPEC_FILE): amiconfig-hepix.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-hepix.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
