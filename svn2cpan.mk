
$(subst perl-,,$(NAME))-$(VERSION).tar.gz: source
	rm -rf $(subst perl-,,$(NAME))-$(VERSION)
	svn export `cat source` $(subst perl-,,$(NAME))-$(VERSION)
	tar cfvz $(subst perl-,,$(NAME))-$(VERSION).tar.gz $(subst perl-,,$(NAME))-$(VERSION)

