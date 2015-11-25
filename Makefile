
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	amiconfig-cernvm \
	amiconfig-hepix \
	amiconfig-rpath \
	azure-cli \
	cctools \
	CERN-CA-certs \
	cernvm-config \
	cernvm-online-guest \
	cernvm-pam \
	cernvm-release \
	cernvm-theme \
	cernvm-update \
	docker-cernvm \
	ec2-api-tools \
	ec2-ami-tools \
	lxdm \
	openafs-kernel \
	open-vm-tools \
	perl-Amazon-EC2 \
	perl-Text-Aligner \
	perl-Text-Table \
	vboxguest \
	VBoxManage \
	WALinuxAgent

#PACKAGES = \
#	azure-cli \
#	cctools \
#	CERN-CA-certs \
#	cern-cloudinit-modules \
#	cernvm-appliance-agent \
#	cernvm-config \
#	cernvm-gce \
#	cernvm-pam \
#	cernvm-patches \
#	cernvm-theme \
#	cernvm-release \
#	cernvm-online-guest \
#	cernvm-update \
#	condor \
#	cloud-scheduler \
#	ec2-api-tools \
#	ec2-ami-tools \
#	elastiq \
#	eos-client \
#	eos-fuse \
#	erlang \
#	google-cloud-sdk \
#	openafs-kernel \
#	open-vm-tools \
#	shoal-client \
#	slim \
#	uriparser \
#	vaf-client \
#	vboxguest \
#	VBoxManage \
#	vmware-tools-plugins-unity

default: all
	$(MAKE) repo

$(PACKAGES)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

all clean : $(PACKAGES)

repo: $(YUM_REPO)/repodata/repomd.xml
$(YUM_REPO)/repodata/repomd.xml: $(wildcard $(YUM_REPO)/*.rpm)
	createrepo -d -s sha $(YUM_REPO) --workers=12

