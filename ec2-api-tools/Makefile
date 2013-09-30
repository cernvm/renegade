
include $(TOP)/config.mk

EXTRA_SOURCES=direct/usr/lib/ec2/bin
direct/usr/lib/ec2/bin: ec2-api-tools-$(VERSION).zip
	unzip ec2-api-tools-$(VERSION).zip
	cp -av ec2-api-tools-$(VERSION)/THIRDPARTYLICENSE.TXT ec2-api-tools-$(VERSION)/bin ec2-api-tools-$(VERSION)/lib direct/usr/lib/ec2/
	cp -v ec2-api-tools-$(VERSION)/license.txt direct/usr/lib/ec2/license-ec2-api-tools.txt
	rm -rf ec2-api-tools-$(VERSION)
	touch direct/usr/lib/ec2/bin
ec2-api-tools-$(VERSION).zip:
	curl http://ecsft.cern.ch/dist/cernvm/ec2-api-tools-$(VERSION).zip > ec2-api-tools-$(VERSION).zip

include $(TOP)/generic.mk
include $(TOP)/template-spec.mk
include $(TOP)/from-svn.mk

