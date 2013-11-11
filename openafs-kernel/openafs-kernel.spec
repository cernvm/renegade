Summary: Helper package to fulfill OpenAFS kmod dependency
Name: openafs-kernel
Version: AUTO
Release: AUTO%{?dist}
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%description
OpenAFS kernel module is part of the CernVM kernel

%prep

%build

%install

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)

%changelog
* Mon Nov 11 2013 Jakob Blomer <jblomer@cern.ch> - 1.6.5
- Initial package
