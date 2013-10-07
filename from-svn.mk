
SVN_BRANCH = $(shell basename `cat source`)
SOURCE_ROOT = $(TOP)/$(NAME)/$(SVN_BRANCH)
ifndef SOURCE_DIST
SOURCE_DIST = .
endif

$(SOURCE_TARBALL): $(SOURCE_ROOT) version release | $(RPMTOP)/SOURCES
	cd $(SOURCE_ROOT); \
	  gtar -cvz --exclude=.svn --transform 's,^\.\([^.]\),$(NAME)-$(VERSION)\1,' --show-transformed-names -f - $(SOURCE_DIST) > $(SOURCE_TARBALL)

$(SOURCE_ROOT): source
	svn co `cat source`

