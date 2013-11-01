
NPM_SOURCE = npm-$(NAME)-$(VERSION)
NPM_DIST = $(NAME)-$(VERSION)
NPM_TARBALL = $(NAME)-$(VERSION).tar.gz

$(NPM_DIST): $(NPM_SOURCE)
	cd $(NPM_SOURCE) && npm -g -q --production --prefix=../$(NPM_DIST)/usr install .

$(NPM_TARBALL): $(NPM_DIST)
	tar -czf $(NPM_TARBALL) $(NPM_DIST)

$(SOURCE_TARBALL): version $(NPM_TARBALL) | $(RPMTOP)/SOURCES
	cp $(NPM_TARBALL) $(SOURCE_TARBALL)

$(SPEC_FILE): version release $(NPM_TARBALL) $(TOP)/template.spec | $(RPMTOP)/SPECS
	cat $(TOP)/template.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE).$(DISTTAG)/" | \
	  sed -e "s/^Name: AUTO/Name: $(NAME)/" | \
	  sed -e "s/^Summary: AUTO/Summary: $(NAME) package/" | \
	  sed -e "s/^BuildArch: AUTO/BuildArch: $(ARCH)/" | \
	  sed -e "s/^EXTRADEPENDS/Requires: nodejs/" | \
	  sed -f $(TOP)/files.sed \
	> $(SPEC_FILE)
	
	

