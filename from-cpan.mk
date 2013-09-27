
CPAN_TARBALL=$(subst perl-,,$(NAME))-$(VERSION).tar.gz

$(SPEC_FILE): version release $(CPAN_TARBALL) | $(RPMTOP)/SPECS
	cpan2rpm --name=$(NAME) --no-prfx --version=$(VERSION) --release=$(RELEASE).$(DISTTAG) --buildarch=$(ARCH) --spec-only --spec=$(SPEC_FILE) $(CPAN2RPM_EXTRA_OPTIONS) $(CPAN_TARBALL)
	sed -i -e "s/source:\s*$(CPAN_TARBALL)/source: perl-$(CPAN_TARBALL)/" $(SPEC_FILE)

$(SOURCE_TARBALL): version $(CPAN_TARBALL) | $(RPMTOP)/SOURCES
	cp $(CPAN_TARBALL) $(SOURCE_TARBALL)

