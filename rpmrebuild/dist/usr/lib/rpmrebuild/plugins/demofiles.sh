#!/bin/sh
###############################################################################
#   demofiles.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2004 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or          : valery_reznic@users.sourceforge.net
#    $Id: demofiles.sh 565 2008-04-02 12:53:31Z gerbier $
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
###############################################################################
# code's file of demo plugin for rpmrebuild

# just a demo script to show what can be done
# with a file plugin
version=1.0
###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin just show how to modifiy files"
	msg "it must be called with --change-files option"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	exit 1

}
###############################################################################

# test for arguments
if [ $# -eq 1 ]
then
	case $1 in
	-h | --help )
		syntaxe
	;;

        -v | --version )
                msg "$0 version $version";
                exit 1;
        ;;

	*)
		msg "bad option : $1";
		syntaxe
	;;
	esac
fi

# test the way to be called
case $LONG_OPTION in
	change-files)
		;;
		*)	msg "bad option : $LONG_OPTION (should be called from change-files)";
		syntaxe
	;;
esac

# go to the directory which contains all package's files
# in the same tree as the installed files :
# if the package contains /etc/cron.daily files, you will find etc/cron.daily directory here
cd $RPM_BUILD_ROOT
pwd

# you can now do what you want on the files : 
# add, remove, move, rename files (be carefull, you have to change the %files section too)
# modify files, change perms ...

# for this demo, we do not change anything, just display what we can see
find . -ls

# we can also change some files
# find . -type f | xargs touch
