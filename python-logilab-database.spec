# for el5, force use of python2.6
%if 0%{?el5}
%define python python26
%define __python /usr/bin/python2.6
%else
%define python python
%define __python /usr/bin/python
%endif
%{!?_python_sitelib: %define _python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           %{python}-logilab-database
Version:        1.13.4
Release:        logilab.1%{?dist}
Summary:        Unified database access library for python

Group:          Development/Libraries
License:        LGPLv2+
URL:            http://www.logilab.org/projects/logilab-database
Source0:        http://download.logilab.org/pub/database/logilab-database-%{version}.tar.gz
BuildArch:      noarch
BuildRoot:      %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildRequires:  %{python}
Requires:       %{python}, %{python}-logilab-common >= 0.63.2
Requires:       %{python}-six >= 1.4.0


%description
logilab-database provides some classes to make unified access
to different RDBMS possible:

* actually compatible db-api from different drivers
* extensions functions for common tasks such as creating database, index,
  users, dump and restore, etc...
* additional api for full text search

%prep
%setup -q -n logilab-database-%{version}


%build
%{__python} setup.py build
%if 0%{?el5}
# change the python version in shebangs
find . -name '*.py' -type f -print0 |  xargs -0 sed -i '1,3s;^#!.*python.*$;#! /usr/bin/python2.6;'
%endif


%install
rm -rf $RPM_BUILD_ROOT
NO_SETUPTOOLS=1 %{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
rm -rf $RPM_BUILD_ROOT%{_python_sitelib}/logilab/database/test
rm -rf $RPM_BUILD_ROOT%{_python_sitelib}/logilab/__init__.py*

%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README ChangeLog COPYING
%{_python_sitelib}/logilab*

