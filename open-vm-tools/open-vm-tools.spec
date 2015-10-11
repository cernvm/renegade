Summary: The open source version of VMware tools
Name: open-vm-tools
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: vmware-guestd.init
Source2: network.patch
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Provides: libhgfs.so()(64bit)
Provides: libvmtools.so()(64bit)

BuildRequires: gcc 
BuildRequires: gcc-c++
BuildRequires: make
BuildRequires: fuse-devel
BuildRequires: glib2-devel
BuildRequires: pam-devel
BuildRequires: libXinerama-devel
BuildRequires: libXi-devel
BuildRequires: libXrandr-devel
BuildRequires: libXtst-devel
BuildRequires: gtk2-devel
BuildRequires: gtkmm24-devel
BuildRequires: libdnet-devel
BuildRequires: libicu-devel
BuildRequires: uriparser
BuildRequires: xerces-c-devel
BuildRequires: libmspack-devel
BuildRequires: procps-ng-devel
BuildRequires: automake
BuildRequires: autoconf
BuildRequires: libtool
BuildRequires: doxygen

%description
The open source version of VMware tools

%prep
%setup -q -n %{name}-%{name}-%{version}-3000743

%build
cd open-vm-tools
autoreconf -i
./configure --prefix=/usr \
  --with-x \
  --disable-tests \
  --without-kernel-modules \
  --without-root-privileges \
  --without-xmlsecurity \
  --libdir=/usr/lib64 \
  --sysconfdir=/etc
make %{?_smp_mflags}

%install
cd open-vm-tools
make DESTDIR=%{buildroot} install

rm -f %{buildroot}/sbin/mount.vmhgfs
ln -s /usr/sbin/mount.vmhgfs %{buildroot}/sbin/mount.vmhgfs
mkdir -p %{buildroot}/mnt/hgfs

# vmtoolsd -- syncronizes time with host, responsible for "vmware tools installed"
mkdir -p %{buildroot}/etc/init.d
cp %{_sourcedir}/vmware-guestd.init %{buildroot}/etc/init.d/vmware-guestd
chmod +x %{buildroot}/etc/init.d/vmware-guestd

# Fix suspend script: service network stop does not work in uCernVM
cd %{buildroot}/etc/vmware-tools/scripts/vmware
patch < %{_sourcedir}/network.patch

chmod u+s %{buildroot}/usr/bin/vmware-user-suid-wrapper

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc /usr/share/doc/*
/usr/share/open-vm-tools
/usr/bin/*
/etc/xdg/autostart/vmware-user.desktop
/etc/pam.d/vmtoolsd
/usr/include/*
/usr/lib64/*
/usr/sbin/*
/sbin/*
/etc/vmware-tools
%dir /mnt/hgfs
/etc/init.d/vmware-guestd

%changelog
* Sat Oct 10 2015 Jakob Blomer <jblomer@cern.ch> - 10.0.0-3
- Update to reflect new open-vm-tools version
* Mon May 15 2015 Jakob Blomer <jblomer@cern.ch> - 9.4.0-9
- Ensure suid flag of vmware-user-suid-wrapper
* Thu May 14 2013 Jakob Blomer <jblomer@cern.ch> - 9.2.3
- Initial package
