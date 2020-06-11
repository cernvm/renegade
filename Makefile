
TOP = $(shell pwd)
include $(TOP)/params.mk

PACKAGES = cernvm-config

PACKAGES_ORIG = \
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
	container-selinux \
	containerd.io \
	docker-ce \
	docker-ce-cli \
	ec2-api-tools \
	ec2-ami-tools \
	elastiq \
	google-cloud-sdk \
	lxdm \
	openafs-kernel \
	open-vm-tools \
	perl-Amazon-EC2 \
	perl-Text-Aligner \
	perl-Text-Table \
	rpmrebuild \
	shoal-client \
	vaf-client \
	vboxguest \
	VBoxManage \
	vmware-tools-plugins-unity

default: all
	$(MAKE) repo

$(PACKAGES)::
	$(MAKE) TOP=$(TOP) -C $@ $(MAKECMDGOALS)

all clean : $(PACKAGES)

repo: $(YUM_REPO)/repodata/repomd.xml
$(YUM_REPO)/repodata/repomd.xml: $(wildcard $(YUM_REPO)/*.rpm)
	createrepo -d $(YUM_REPO) --workers=12

