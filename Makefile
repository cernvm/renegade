
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = \
	amiconfig-cernvm \
	amiconfig-hepix \
	amiconfig-rpath \
	azure-cli \
	cctools \
	CERN-CA-certs \
	cern-cloudinit-modules \
	cernvm-config \
	cernvm-online-guest \
	cernvm-pam \
	cernvm-patches \
	cernvm-release \
	cernvm-theme \
	cernvm-update \
	cernvm-waagent \
	compat-xrootd-libs \
	compat-xrootd-client-libs \
	docker-cernvm \
	ec2-api-tools \
	ec2-ami-tools \
	eos-client \
	eos-fuse \
	elastiq \
	google-cloud-sdk \
	lxdm \
	openafs-kernel \
	open-vm-tools \
	perl-Amazon-EC2 \
	perl-Text-Aligner \
	perl-Text-Table \
	rpmrebuild \
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
	createrepo -d $(YUM_REPO) --workers=12

