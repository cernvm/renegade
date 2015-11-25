#!/bin/bash
###############################################################################
#   uniq.plug
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2002 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: uniq.sh 381 2005-03-01 09:51:12Z valery_reznic $
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
# code's file of uniq plugin for rpmrebuild

version=1.0
###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin remove duplicate spec lines"
	msg "it can be called with : rpmrebuild --change-spec-requires|--change-spec-provides|--change-spec-conflicts|--change-spec-obsoletes"
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
	change-spec-requires) ;;
	change-spec-conflicts) ;;
	change-spec-obsoletes) ;;
	change-spec-provides) ;;
	*)
		msg "error : $0 can not be called from $LONG_OPTION";
		syntaxe;
		exit 1
	;;
esac

liste=""
while read line
do
	echo $line
done | sort -u
