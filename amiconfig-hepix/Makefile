
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/hepix.cfg
include $(TOP)/generic.mk

GIT_SRC = $(shell basename `cat source` | sed 's/.git$$//')

$(GIT_SRC): source
	git clone `cat source`

$(SOURCE_TARBALL): $(GIT_SRC) | $(RPMTOP)/SOURCES
	cd $(GIT_SRC)/hepix; \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): hepix.cfg | $(RPMTOP)/SOURCES
	cp hepix.cfg $(RPMTOP)/SOURCES

$(SPEC_FILE): amiconfig-hepix.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-hepix.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
