
include $(TOP)/config.mk
include $(TOP)/generic.mk

GIT_SRC = $(shell basename `cat source` | sed 's/\.git$$//')

$(GIT_SRC): source
	git clone `cat source`

$(SOURCE_TARBALL): $(GIT_SRC) | $(RPMTOP)/SOURCES
	cd $(GIT_SRC)/cernvm; \
	  tar -cvz --exclude=.svn --transform=s,^.,$(NAME)-$(VERSION), --show-transformed-names -f - . > $(SOURCE_TARBALL)	

$(SPEC_FILE): amiconfig-cernvm.spec version release | $(RPMTOP)/SPECS
	cat amiconfig-cernvm.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
