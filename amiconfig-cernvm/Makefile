
include $(TOP)/config.mk
include $(TOP)/generic.mk

SVN_SRC = $(shell basename `cat source`)

$(SVN_SRC): source
	svn co `cat source`

$(SOURCE_TARBALL): $(SVN_SRC) | $(RPMTOP)/SOURCES
	cd $(SVN_SRC); \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(SPEC_FILE): amiconfig-cernvm.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-cernvm.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
