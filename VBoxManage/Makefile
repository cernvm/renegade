
include $(TOP)/config.mk
include $(TOP)/generic.mk

$(SOURCE_TARBALL): | $(RPMTOP)/SOURCES
	curl http://dlc.sun.com.edgesuite.net/virtualbox/$(VERSION)/VirtualBox-$(VERSION).tar.bz2 > VirtualBox-$(VERSION).tar.bz2
	tar xvfj VirtualBox-$(VERSION).tar.bz2
	tar cfvz VirtualBox-$(VERSION).tar.gz VirtualBox-$(VERSION)
	mv VirtualBox-$(VERSION).tar.gz $(SOURCE_TARBALL)
	rm -rf VirtualBox-$(VERSION).tar.bz2 VirtualBox-$(VERSION)

$(SPEC_FILE): VBoxManage.spec version release | $(RPMTOP)/SPECS
	cat VBoxManage.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE)/" \
	  > $(SPEC_FILE)
