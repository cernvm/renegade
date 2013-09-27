Summary: OpenAFS user space client
Name: openafs-client
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: gcc
BuildRequires: make
BuildRequires: pam-devel
BuildRequires: krb5-devel
BuildRequires: ncurses-devel
BuildRequires: byacc
BuildRequires: flex

%description
AFS is a distributed filesystem product, pioneered at Carnegie Mellon University and supported and developed as a product by Transarc Corporation (now IBM Pittsburgh Labs). It offers a client-server architecture for federated file sharing and replicated read-only content distribution, providing location independence, scalability, security, and transparent migration capabilities.

%prep
%setup -q -n openafs-%{version}

%build
./configure --prefix=/usr \
  --libdir=/usr/lib64 \
  --enable-transarc-paths \
  --disable-kernel-module \
  --with-afs-sysname=amd64_linux26
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install

%clean
rm -rf %{buildroot}

# From SLC openafs package
%files
%defattr(-,root,root,-)
%{_bindir}/afsmonitor
%{_bindir}/bos
%{_bindir}/fs
%{_bindir}/klog
%{_bindir}/klog.krb
%{_bindir}/pagsh.openafs
%{_bindir}/pagsh.krb
%{_bindir}/pts
%{_bindir}/scout
%{_bindir}/sys
%{_bindir}/tokens
%{_bindir}/tokens.krb
%{_bindir}/translate_et
%{_bindir}/udebug
%{_bindir}/unlog
%{_bindir}/xstat_cm_test
%{_bindir}/xstat_fs_test
%attr(0555,root,root) %{_sbindir}/backup
%attr(0555,root,root) %{_sbindir}/butc
%{_sbindir}/fms
%attr(0555,root,root) %{_sbindir}/fstrace
%{_sbindir}/kas
%{_sbindir}/read_tape
%{_sbindir}/restorevol
%attr(0555,root,root) %{_sbindir}/rxdebug
%{_sbindir}/uss
%attr(0555,root,root) %{_sbindir}/vos

%{_mandir}/*
%{initdir}/afs
%dir %{_prefix}/vice
%dir %{_prefix}/vice/cache
%dir %{_prefix}/vice/etc
%{_prefix}/vice/etc/C
%{_prefix}/vice/etc/C/afszcm.cat
%defattr(0555,root,root)
%{_bindir}/cmdebug
%{_bindir}/up
%{_sbindir}/kdump
%{_prefix}/vice/etc/afsd
%{_prefix}/vice/etc/killafs

%changelog
* Wed May 15 2013 Jakob Blomer <jblomer@cern.ch> - 1.6.2.1
- Initial package
