
include $(TOP)/config.mk
include $(TOP)/generic.mk

UPSTREAM_NAME = $(shell echo $(NAME) | sed 's/^compat-//')
UPSTREAM_RPM = $(UPSTREAM_NAME)-$(VERSION)-$(RELEASE).x86_64.rpm
TREE = $(NAME)-$(VERSION)

$(UPSTREAM_RPM): version release
	curl http://eos.cern.ch/rpms/eos-aquamarine/el-7-x86_64/$(UPSTREAM_RPM) > $@

$(TREE): $(UPSTREAM_RPM)
	rm -rf $(TREE) && mkdir $(TREE)
	cd $(TREE) && cat ../$(UPSTREAM_RPM) | rpm2cpio | cpio -id

$(SOURCE_TARBALL): $(TREE) version release | $(RPMTOP)/SOURCES
	gtar -cvz -f - `basename $(TREE)` > $(SOURCE_TARBALL)

include $(TOP)/template-spec.mk

