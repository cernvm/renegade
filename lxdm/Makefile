
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(NAME)-$(VERSION).tar.xz:
	curl http://netcologne.dl.sourceforge.net/project/$(NAME)/$(NAME)%20$(VERSION)/$(NAME)-$(VERSION).tar.xz > $(NAME)-$(VERSION).tar.xz

$(NAME)-$(VERSION).tar.gz: $(NAME)-$(VERSION).tar.xz
	tar xvf $(NAME)-$(VERSION).tar.xz
	tar cfz $(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION)
	rm -rf $(NAME)-$(VERSION)

$(SOURCE_TARBALL): $(NAME)-$(VERSION).tar.gz | $(RPMTOP)/SOURCES
	cat $(NAME)-$(VERSION).tar.gz > $(SOURCE_TARBALL)	

$(SPEC_FILE): $(NAME).spec version release | $(RPMTOP)/SPECS
	cat $(NAME).spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
