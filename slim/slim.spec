Summary: SLiM Display Manager
Name: slim
Version: AUTO
Release: AUTO%{?dist}
Source0: http://prdownload.berlios.de/slim/%{name}-%{version}.tar.gz 
Source1: slim.conf
Source2: slimlock.conf
Group: Applications/System
License: GPL
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires: cmake
BuildRequires: gcc
BuildRequires: gcc-c++
BuildRequires: make
BuildRequires: xorg-x11-server-devel
BuildRequires: fontconfig-devel
BuildRequires: libXft-devel
BuildRequires: libXrender-devel
BuildRequires: libX11-devel
BuildRequires: libXmu-devel
BuildRequires: libpng-devel
BuildRequires: libjpeg-devel
BuildRequires: freetype-devel
BuildRequires: zlib-devel
BuildRequires: pam-devel

%description
The SLiM graphical login manager

%prep
%setup -q 

%build
sed -i -e 's/X11_Xmu_LIB}$/X11_Xmu_LIB} -lXmu/' CMakeLists.txt
rm -rf build
mkdir build
cd build
cmake -DBUILD_SLIMLOCK=1 -DUSE_PAM=1 -DCMAKE_INSTALL_PREFIX=/usr ../
make %{?_smp_mflags}

%install
cd build
make DESTDIR=%{buildroot}/ install
cp %{_sourcedir}/slim.conf %{buildroot}/etc/slim.conf
cp %{_sourcedir}/slimlock.conf %{buildroot}/etc/slimlock.conf

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/bin/slim
/usr/bin/slimlock
/usr/lib/libslim.*
/usr/share/man/*
/etc/slim.conf
/etc/slimlock.conf
/usr/share/slim/*
/lib/systemd/system/slim.service

%changelog
* Tue Feb 10 2015 Jakob Blomer <jblomer@cern.ch> - 1.3.6
- Updated package, systemd, slimlock
* Sun Apr 28 2013 Jakob Blomer <jblomer@cern.ch> - 1.3.5
- Initial package
