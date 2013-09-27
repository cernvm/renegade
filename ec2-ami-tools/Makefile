
include $(TOP)/config.mk

EXTRA_SOURCES=direct/usr/lib/ec2/bin
direct/usr/lib/ec2/bin: ec2-ami-tools-$(VERSION).zip
	unzip ec2-ami-tools-$(VERSION).zip
	cp -av ec2-ami-tools-$(VERSION)/license.txt ec2-ami-tools-$(VERSION)/bin ec2-ami-tools-$(VERSION)/lib ec2-ami-tools-$(VERSION)/etc direct/usr/lib/ec2/
	rm -rf ec2-ami-tools-$(VERSION)
	touch direct/usr/lib/ec2/bin
ec2-ami-tools-$(VERSION).zip:
	curl http://ecsft.cern.ch/dist/cernvm/ec2-ami-tools-$(VERSION).zip > ec2-ami-tools-$(VERSION).zip

include $(TOP)/generic.mk
include $(TOP)/template-spec.mk
include $(TOP)/from-svn.mk

