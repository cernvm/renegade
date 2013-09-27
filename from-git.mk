
GIT_REPO_NAME = $(shell basename `cat source` | sed 's/\.git$$//')
SOURCE_ROOT = $(TOP)/$(NAME)/$(GIT_REPO_NAME)
ifndef GIT_BASE_DIR
GIT_BASE_DIR =
endif
ifndef SOURCE_DIST
SOURCE_DIST = .
endif

$(SOURCE_TARBALL): $(SOURCE_ROOT) version release | $(RPMTOP)/SOURCES
	cd $(SOURCE_ROOT)/$(GIT_BASE_DIR); \
	  gtar -cvz --exclude=.git --transform 's,^\.,$(NAME)-$(VERSION),' --show-transformed-names -f - $(SOURCE_DIST) > $(SOURCE_TARBALL)

$(SOURCE_ROOT): source
	git clone `cat source`

