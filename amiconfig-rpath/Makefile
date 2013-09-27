
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/default.cfg
include $(TOP)/generic.mk

SVN_SRC = $(shell basename `cat source`)

$(SVN_SRC): source
	svn co `cat source`

$(SOURCE_TARBALL): $(SVN_SRC) | $(RPMTOP)/SOURCES
	cd $(SVN_SRC); \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): default.cfg | $(RPMTOP)/SOURCES
	cp default.cfg $(RPMTOP)/SOURCES

$(SPEC_FILE): amiconfig-rpath.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-rpath.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
