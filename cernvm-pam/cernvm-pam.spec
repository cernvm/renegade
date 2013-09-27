Summary: CernVM contextualization PAM module
Name: cernvm-pam
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: gcc
BuildRequires: pam-devel
Requires: cernvm-online-guest

%description
PAM Module to handle cernvm-online contextualization during console login

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
/lib64/security/pam_cernvm.so
/etc/cernvm/pam_action.sh

%changelog
* Mon Apr 29 2013 Jakob Blomer <jblomer@cern.ch> - 0.1
- Initial package
