Summary: CernVM amiconfig plugins
Name: amiconfig-cernvm
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python-devel
Requires: amiconfig-rpath

%description
Extra amiconfig plugins for CernVM

%prep
%setup -q 

%build
make

%install
make DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/lib/python/site-packages/*
/usr/bin/amiconfig-mime
/usr/sbin/amiconfig-helper

%changelog
* Sun Nov 15 2015 Jakob Blomer <jblomer@cern.ch> - 0.5.3
- move amiconfig-cernvm to cernvm-online package
* Thu Apr 25 2013 Jakob Blomer <jblomer@cern.ch> - 0.5.1
- Initial package
