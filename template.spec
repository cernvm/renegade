AUTODEPS
%define debug_package %{nil}

Summary: AUTO
Name: AUTO
Version: AUTO
Release: AUTO
License: Unknown
Group: CernVM/Extra
BuildArch: AUTO

Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

EXTRADEPENDS

%description
AUTODESC

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}
tar -cf - . | sh -c "cd %{buildroot}; tar -xf -"

%post
/sbin/ldconfig

%postun
/sbin/ldconfig

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
AUTOFILES

%changelog
