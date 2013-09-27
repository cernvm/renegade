Summary: rPath amiconfig agent
Name: amiconfig-rpath
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Source1: default.cfg
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: python-devel

%description
The amiconfig agent parses and processes EC2 contextualization information

%prep
%setup -q 

%build
make

%install
make DESTDIR=%{buildroot} install
rm -rf %{buildroot}/etc/init.d
mkdir -p %{buildroot}/usr/lib/python2.6/site-packages
ln -s /usr/lib/python/site-packages/amiconfig %{buildroot}/usr/lib/python2.6/site-packages/amiconfig
mkdir -p %{buildroot}/etc/amiconfig
cp %{_sourcedir}/default.cfg %{buildroot}/etc/amiconfig/

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/lib/python/site-packages/*
/usr/lib/python2.6/site-packages/amiconfig
%{_sbindir}/amiconfig
%{_sysconfdir}/amiconfig/default.cfg

%changelog
* Tue Apr 23 2013 Jakob Blomer <jblomer@cern.ch> - 0.5.1
- Initial package
