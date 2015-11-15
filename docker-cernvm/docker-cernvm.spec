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
install -D -m 644 docker.conf %{buildroot}/etc/docker.conf
install -D -m 644 docker.service %{buildroot}/usr/lib/systemd/system/docker.service
install -D -m 644 docker.socket %{buildroot}/usr/lib/systemd/system/docker.socket

%clean
rm -rf %{buildroot}

%post
if ! getent group docker >/dev/null 2>&1; then
  groupadd -r docker -g 200
fi

%postun
# TODO: remove docker group.  Could this change the gid during upgrades?

%files
%defattr(-,root,root,-)
%{_bindir}/docker
/usr/lib/systemd/system/docker.service
/usr/lib/systemd/system/docker.socket
%config %{_sysconfdir}/docker.conf

%changelog
* Sun Nov 15 2015 Jakob Blomer <jblomer@cern.ch> - 1.8.3-3
- Systemd integration
* Tue Oct 13 2015 Jakob Blomer <jblomer@cern.ch> - 1.8.3-2
- Remove chkconfig stuff
* Sun Dec 21 2014 Jakob Blomer <jblomer@cern.ch> - 1.4.1-1
- Initial package
