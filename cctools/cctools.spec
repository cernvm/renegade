%define xrootd_version AUTO_XROOTD_VERSION

Summary: The CCTools package
Name: cctools
Version: AUTO
Release: AUTO%{?dist}
Source0: http://www.cse.nd.edu/~ccl/software/files/%{name}-%{version}.tar.gz
Source1: http://xrootd.org/download/v%{xrootd_version}/xrootd-%{xrootd_version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# XRootD
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libtool

BuildRequires: cvmfs-devel
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: doxygen
BuildRequires: fuse-devel
BuildRequires: groff
BuildRequires: krb5-devel
BuildRequires: m4
BuildRequires: make
BuildRequires: mysql-devel
BuildRequires: openssl-devel
BuildRequires: perl-ExtUtils-Embed
BuildRequires: python-devel
BuildRequires: readline-devel
BuildRequires: swig
BuildRequires: zlib-devel

%description
The CCTools package contains Parrot, Chirp, Makeflow, Work Queue, SAND, and other software.

%package devel
Summary: CCTools package development libs
Group: Application/System
%description devel
The CCTools package static libraries and header files

%prep
%setup -q -n %{name}-%{version}-source
%setup -q -D -T -a 1 -n %{name}-%{version}-source

%build
cd xrootd-%{xrootd_version}
./bootstrap.sh
./configure --enable-shared=no --enable-static=yes --prefix=%{_builddir}/xrootd-built
make %{?_smp_mflags}
make install
cd ..

./configure --prefix /usr \
  --with-cvmfs-path /usr \
  --with-fuse-path /usr \
  --with-krb5-path /usr \
  --with-mysql-path /usr \
  --with-readline-path /usr \
  --with-xrootd-path %{_builddir}/xrootd-built
make %{?_smp_mflags}

%install
make CCTOOLS_INSTALL_DIR=%{buildroot}/usr install
rm -rf %{buildroot}/usr/etc
%ifarch x86_64
mv %{buildroot}/usr/lib %{buildroot}/usr/lib64
%endif

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc /usr/doc/*
%{_bindir}/*
%{_libdir}/*.so
%{_libdir}/perl*
%{_libdir}/python*
%{_mandir}/man1/*

%files devel 
%defattr(-,root,root)
%{_libdir}/*.a
%{_includedir}/*

%changelog
* Sun Apr 07 2013 Jakob Blomer <jblomer@cern.ch> - 3.7.1
- Initial package
