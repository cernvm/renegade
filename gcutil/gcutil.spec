Summary: Google Compute Engine Tools
Name: gcutil
Version: AUTO
Release: AUTO%{?dist}
Source0: https://google-compute-engine-tools.googlecode.com/files/%{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: python

%description
gcutil is a command-line tool that is used to manage your Google Compute Engine resources.

%prep
%setup -q 

%build

%install
mkdir -p %{buildroot}/usr/bin
cp gcutil %{buildroot}/usr/bin
cp -r lib %{buildroot}/usr/bin/gcutil-lib
sed -i -e s/\'lib\',/\'gcutil-lib\',/ %{buildroot}/usr/bin/gcutil

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_bindir}/*

%changelog
* Tue Jun 04 2013 Jakob Blomer <jblomer@cern.ch> - 1.8.1
- Initial package
