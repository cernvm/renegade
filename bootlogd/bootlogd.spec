Summary: bootlogd package
Name: bootlogd
Version: AUTO
Release: AUTO%{?dist}
Source0: %{name}-%{version}.tar.gz
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%description
The bootlogd daemon, customized for CernVM

%prep
%setup -q

%build
make %{?_smp_mflags}

%install
make DESTDIR=%{buildroot} install

%post
chkconfig --del bootlogd-stop
for i in 2 3 4 5; do
  ln -s ../init.d/bootlogd-stop /etc/rc.d/rc${i}.d/S99zbootlogd-stop
done

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc /usr/share/man/*
/sbin/*
/etc/init.d/bootlogd-stop
/etc/sysconfig/modules/bootlogd.modules

%changelog
* Thu Aug 08 2013 Jakob Blomer <jblomer@cern.ch> - 2.86.01 
- Initial package
