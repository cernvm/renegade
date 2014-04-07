
include $(TOP)/params.mk

NAME = $(shell basename $(CURDIR))
ARCH = $(shell test -f arch && cat arch || echo $(HOSTARCH))
VERSION = $(shell cat version)
RELEASE = $(shell cat release)
CERNVM_EPOCH = 0

SOURCE_TARBALL = $(RPMTOP)/SOURCES/$(NAME)-$(VERSION).tar.gz
SPEC_FILE = $(RPMTOP)/SPECS/$(NAME).spec
RPM_NAME = $(NAME)-$(VERSION)-$(RELEASE).$(DISTTAG).$(ARCH).rpm
RPM = $(RPMTOP)/RPMS/$(ARCH)/$(RPM_NAME)
RPM_REPO = $(YUM_REPO)/$(RPM_NAME)

all: $(RPM_REPO)
$(RPM_REPO): $(RPM)
	cp $(RPM) $(RPM_REPO)

$(RPMTOP)/SOURCES:
	mkdir -p $(RPMTOP)/SOURCES

$(RPMTOP)/SPECS:
	mkdir -p $(RPMTOP)/SPECS

