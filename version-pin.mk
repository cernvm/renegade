
SOURCE_ROOT = $(TOP)/$(NAME)/$(NAME)-$(VERSION)
SOURCE_DIST = ./*
UPSTREAM_RPM = $(NAME)-$(VERSION)-$(RELEASE).$(HOSTARCH).rpm

$(UPSTREAM_RPM): version release
	yumdownloader $(NAME)-$(VERSION)-$(RELEASE) --archlist=$(HOSTARCH)
	touch $(UPSTREAM_RPM)

$(RPM): $(UPSTREAM_RPM)
	cp $(UPSTREAM_RPM) $(RPM)

