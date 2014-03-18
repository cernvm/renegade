Summary: uriparser library
Name: uriparser
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: graphviz-devel

%description
uriparser is a strictly RFC 3986 compliant URI parsing and handling library written in C. uriparser is cross-platform, fast, supports Unicode and is licensed under the New BSD license.

%prep
%setup -q 

%build
./configure --prefix=/usr --libdir=/usr/lib64 --disable-test
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_bindir}/*
%{_libdir}/*.so*
%{_libdir}/*.a
%{_libdir}/*.la
%{_libdir}/pkgconfig/liburiparser.pc
/usr/include/uriparser
/usr/share/doc/uriparser

%changelog
* Tue Mar 18 2014 Jakob Blomer <jblomer@cern.ch> - 0.8.0
- Initial package
