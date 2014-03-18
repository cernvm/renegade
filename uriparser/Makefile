
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): version release | $(RPMTOP)/SOURCES
	rm -rf $(NAME)-$(VERSION)
	git clone git://git.code.sf.net/p/uriparser/git $(NAME)-$(VERSION)
	cd $(NAME)-$(VERSION) && git checkout $(NAME)-$(VERSION)
	rm -rf $(NAME)-$(VERSION)/.git
	cd $(NAME)-$(VERSION) && ./autogen.sh
	tar cvfz $(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION)
	mv $(NAME)-$(VERSION).tar.gz $(SOURCE_TARBALL)

$(SPEC_FILE): uriparser.spec version release | $(RPMTOP)/SPECS
	cat uriparser.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
