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

BuildRequires: libXScrnSaver-devel
BuildRequires: uriparser-devel
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

%description
The open source version of VMware tools

%prep
%setup -q -n %{name}-%{version}-179896

%build
./configure --prefix=/usr \
  --with-x \
  --without-kernel-modules \
  --without-root-privileges \
  --libdir=/usr/lib64 
make %{?_smp_mflags}

%install
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
rm -f network.orig

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc /usr/share/doc/*
/usr/share/open-vm-tools
/usr/bin/*
/usr/etc/*
/usr/include/*
/usr/lib64/*
/usr/sbin/*
/sbin/*
/etc/vmware-tools
%dir /mnt/hgfs
/etc/init.d/vmware-guestd

%changelog
* Thu May 14 2013 Jakob Blomer <jblomer@cern.ch> - 9.2.3
- Initial package
