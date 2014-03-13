Summary: The module-init-tools package
Name: module-init-tools
Version: AUTO
Release: AUTO%{?dist}
Source0: https://www.kernel.org/pub/linux/utils/kernel/module-init-tools/module-init-tools-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Provides: config(module-init-tools) = %{version}-%{release}
Provides: modutils = %{version}

%description
/sbin/modprobe and friends

%prep
%setup -q

%build
./configure --prefix /usr
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install
mkdir %{buildroot}/sbin
mv %{buildroot}/usr/bin/* %{buildroot}/sbin/
mv %{buildroot}/usr/sbin/* %{buildroot}/sbin/
rmdir %{buildroot}/usr/sbin %{buildroot}/usr/bin

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/sbin/*
/usr/share/*

%changelog
* Wed Mar 05 2014 Jakob Blomer <jblomer@cern.ch> - 3.15 
- Initial package
