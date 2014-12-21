
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): $(wildcard x86_64/*) | $(RPMTOP)/SOURCES
	cd x86_64; \
          gtar -cvz --transform 's,^\.\([^.]\),$(NAME)-$(VERSION)\1,' --show-transformed-names -f - . > $(SOURCE_TARBALL)

$(SPEC_FILE): docker-cernvm.spec version release | $(RPMTOP)/SPECS
	cat docker-cernvm.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
