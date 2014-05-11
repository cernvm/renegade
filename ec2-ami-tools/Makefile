
include $(TOP)/config.mk

EXTRA_SOURCES=src/usr/lib/ec2/bin
src/usr/lib/ec2/bin: ec2-ami-tools-$(VERSION).zip
	unzip ec2-ami-tools-$(VERSION).zip
	cp -av ec2-ami-tools-$(VERSION)/bin ec2-ami-tools-$(VERSION)/lib ec2-ami-tools-$(VERSION)/etc src/usr/lib/ec2/
	cp -v ec2-ami-tools-$(VERSION)/license.txt src/usr/lib/ec2/license-ec2-ami-tools.txt
	rm -rf ec2-ami-tools-$(VERSION)
	touch src/usr/lib/ec2/bin
ec2-ami-tools-$(VERSION).zip:
	curl http://ecsft.cern.ch/dist/cernvm/ec2-ami-tools-$(VERSION).zip > ec2-ami-tools-$(VERSION).zip

include $(TOP)/generic.mk
include $(TOP)/template-spec.mk
include $(TOP)/from-svn.mk

