
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	amiconfig-rpath \
	amiconfig-cernvm \
	amiconfig-hepix \
	azure-cli \
	bootlogd \
	cctools \
	CERN-CA-certs \
	cern-cloudinit-modules \
	cernvm-appliance-agent \
	cernvm-config \
	cernvm-gce \
	cernvm-pam \
	cernvm-patches \
	cernvm-theme \
	cernvm-release \
	cernvm-online-guest \
	cernvm-update \
	condor \
	copilot-agent \
	copilot-jobmanager-generic \
	copilot-util \
	cpan2rpm \
	cloud-scheduler \
	ec2-api-tools \
	ec2-ami-tools \
	elastiq \
	eos-client \
	eos-fuse \
	erlang \
	google-cloud-sdk \
	nimbus-cloud-client \
	openafs-kernel \
	open-vm-tools \
	perl-Amazon-EC2 \
	perl-Copilot \
	perl-Copilot-AliEn \
	perl-Copilot-Component-Agent \
	perl-Copilot-Component-ContextAgent \
	perl-Copilot-Component-JobManager-AliEn \
	perl-Copilot-Component-JobManager-Generic \
	perl-Copilot-Component-KeyManager \
	perl-Copilot-Component-StorageManager-AliEn \
	perl-Filesys-DiskFree \
	perl-Filter-Template \
	perl-JSON \
	perl-JSON-RPC \
	perl-POE-Component-Jabber \
	perl-POE-Component-Logger \
	perl-POE-Component-SSLify \
	perl-POE-Filter-XML \
	perl-Redis \
	perl-Text-Aligner \
	perl-Text-EasyTemplate \
	perl-Text-Table \
	perl-XML-Encoding \
	perl-XML-SAX-Expat \
	perl-XML-SAX-Expat-Incremental \
	shoal-client \
	slim \
	uriparser \
	vaf-client \
	vboxguest \
	VBoxManage \
	vmware-tools-plugins-unity

PACKAGES-32BIT = $(wildcard *-i686)

default: all
	$(MAKE) repo

$(PACKAGES)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

$(PACKAGES-32BIT)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

all clean : $(PACKAGES) $(PACKAGES-32BIT)

repo: $(YUM_REPO)/repodata/repomd.xml
$(YUM_REPO)/repodata/repomd.xml: $(wildcard $(YUM_REPO)/*.rpm)
	createrepo -d -s sha $(YUM_REPO) --workers=12

