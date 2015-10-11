Summary: LXDM graphical login manager
Name: lxdm
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: gcc 
BuildRequires: make
BuildRequires: intltool

%description
LXDM graphical login manager

%prep
%setup -q

%build
./configure --prefix=/usr \
  --sysconfdir=/etc \
  --with-x \
  --with-pam
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/etc/lxdm
/etc/pam.d/lxdm
/usr/bin/lxdm-config
/usr/lib/systemd/system/lxdm.service
/usr/libexec/lxdm-*
/usr/sbin/lxdm
/usr/sbin/lxdm-binary
/usr/share/locale/*
/usr/share/lxdm

%changelog
* Sun Oct 11 2015 Jakob Blomer <jblomer@cern.ch> - 0.5.2-1
- Initial package
