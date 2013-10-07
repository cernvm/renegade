
SOURCE_ROOT = $(TOP)/$(NAME)/$(NAME)-$(VERSION)
SOURCE_DIST = ./*
UPSTREAM_NAME = $(shell echo $(NAME) | sed 's/-i686$$//')
UPSTREAM_RPM_32 = $(UPSTREAM_NAME)-$(VERSION)-$(RELEASE).i686.rpm
UPSTREAM_RPM_64 = $(UPSTREAM_NAME)-$(VERSION)-$(RELEASE).x86_64.rpm
TREE_32 = 32-$(VERSION)-$(RELEASE)
TREE_64 = 64-$(VERSION)-$(RELEASE)

$(UPSTREAM_RPM_32): version release
	yumdownloader $(UPSTREAM_NAME)-$(VERSION)-$(RELEASE) --archlist=i686
	touch $(UPSTREAM_RPM_32)

$(UPSTREAM_RPM_64): version release
	yumdownloader $(UPSTREAM_NAME)-$(VERSION)-$(RELEASE) --archlist=x86_64
	touch $(UPSTREAM_RPM_64)

$(TREE_32): $(UPSTREAM_RPM_32)
	mkdir $(TREE_32)
	cd $(TREE_32) && cat ../$(UPSTREAM_RPM_32) | rpm2cpio | cpio -id

$(TREE_64): $(UPSTREAM_RPM_64)
	mkdir $(TREE_64)
	cd $(TREE_64) && cat ../$(UPSTREAM_RPM_64) | rpm2cpio | cpio -id

$(SOURCE_TARBALL): $(SOURCE_ROOT) version release | $(RPMTOP)/SOURCES
	gtar -cvz -f - `basename $(SOURCE_ROOT)` > $(SOURCE_TARBALL)

$(SOURCE_ROOT): $(TREE_32) $(TREE_64)
	rm -rf $(SOURCE_ROOT)
	mkdir $(SOURCE_ROOT)
	cd $(TREE_32) && gtar -cv -f - `for f in $$(find . ! -type d); do if [ ! -f ../$(TREE_64)/$$f ]; then echo -n "$$f "; fi; done` | \
	  (cd ../`basename $(SOURCE_ROOT)` && gtar -xv -f -)

