renegade
========

Build system for CernVM Extra Packages

The build system is make based.  Every sub directory corresponds to an extra
package with the same name.  The top directory contains templates for
most common ways to build packages:
  * As a drop-in directory tree of files
  * From a CPAN package
  * With its own spec files
  * ...

Extra packages are either genuine CernVM additions or 3rd party software
not in SL6/EPEL repositories or a specific version of an otherwise available
package.  As packages found in the extras repository have precedence, this
way an older version of a package can be enforced.

