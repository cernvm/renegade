Summary: CernVM amiconfig plugins for HEPiX contextualization
Name: amiconfig-hepix
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: hepix.cfg
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python-devel
Requires: amiconfig-rpath

%description
HEPiX contextualization amiconfig plugins for CernVM

%prep
%setup -q

%build
make

%install
make DESTDIR=%{buildroot} install
mkdir -p %{buildroot}/etc/amiconfig
cp %{_sourcedir}/hepix.cfg %{buildroot}/etc/amiconfig/

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/lib/python2.4/site-packages/*
/etc/init.d/*
/usr/sbin/*
/etc/amiconfig/hepix.cfg

%changelog
* Thu Apr 25 2013 Jakob Blomer <jblomer@cern.ch> - 0.5.1
- Initial package
