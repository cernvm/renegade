
include $(TOP)/config.mk

EXTRA_SOURCES = $(RPMTOP)/SOURCES/default.cfg
include $(TOP)/generic.mk

GIT_SRC = $(shell basename `cat source` | sed 's/.git$$//')

$(GIT_SRC): source
	git clone `cat source`

$(SOURCE_TARBALL): $(GIT_SRC) | $(RPMTOP)/SOURCES
	cd $(GIT_SRC)/rpath; \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(EXTRA_SOURCES): default.cfg | $(RPMTOP)/SOURCES
	cp default.cfg $(RPMTOP)/SOURCES

$(SPEC_FILE): amiconfig-rpath.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-rpath.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
