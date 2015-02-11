Summary: The VBoxManage utility
Name: VBoxManage
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: openssl-devel
BuildRequires: xz-devel
BuildRequires: mkisofs
BuildRequires: libxml2-devel
BuildRequires: iasl
BuildRequires: libxslt-devel
BuildRequires: libIDL-devel
BuildRequires: curl-devel
BuildRequires: libcap-devel
BuildRequires: libstdc++-static

%description
The VBoxManage utility from VirtualBox.  Useful to convert VM image files.

%prep
%setup -q -n VirtualBox-%{version}

%build
./configure \
  --disable-python \
  --disable-java \
  --disable-vmmraw \
  --disable-sdl-ttf \
  --disable-alsa \
  --disable-pulse \
  --disable-dbus \
  --disable-kmods \
  --disable-opengl \
  --disable-docs \
  --disable-libvpx \
  --disable-udptunnel \
  --disable-devmapper \
  --disable-hardening \
  --build-headless 
source ./env.sh
kmk

%install
mkdir -p %{buildroot}/usr/bin
cp -rv out/linux.amd64/release/bin/VBoxManage \
  out/linux.amd64/release/bin/VBoxSVC \
  out/linux.amd64/release/bin/VBoxXPCOMIPCD \
  out/linux.amd64/release/bin/VBoxDDU.so \
  out/linux.amd64/release/bin/VBoxRT.so \
  out/linux.amd64/release/bin/VBoxXPCOM.so \
  out/linux.amd64/release/bin/components \
  %{buildroot}/usr/bin/ 

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_bindir}/*

%changelog
* Sat Feb 22 2014 Jakob Blomer <jblomer@cern.ch> - 4.3.6
- Initial package
