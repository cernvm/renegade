Summary: The Docker container package
Name: docker-cernvm
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: Apache License 2.0
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%description
The Docker self-contained binary plus configuration for CernVM

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
install -D -m 755 docker %{buildroot}/usr/bin/docker
install -D -m 755 docker.initd %{buildroot}/etc/init.d/docker
install -D -m 644 docker.conf %{buildroot}/etc/docker.conf

%clean
rm -rf %{buildroot}

%post
if ! getent group docker >/dev/null 2>&1; then
  groupadd -r docker -g 200
fi
if ! chkconfig docker --list >/dev/null 2>&1; then
  chkconfig --add docker
  chkconfig docker off
fi

%postun
# TODO: remove docker group.  Could this change the gid during upgrades?

%files
%defattr(-,root,root,-)
%{_bindir}/docker
%{_sysconfdir}/init.d/docker
%config %{_sysconfdir}/docker.conf

%changelog
* Sun Dec 21 2014 Jakob Blomer <jblomer@cern.ch> - 1.4.1-1
- Initial package
