#!/bin/bash
###############################################################################
#   demo.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2004 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: demo.sh 627 2009-11-13 13:38:02Z gerbier $
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

version=1.1
###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin just show which spec part is changed by a plugin"
	msg "it can be called with from any option"
	msg "-n|--null : does nothing"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	exit 1

}
###############################################################################

# test for arguments
if [ $# -eq 1 ]
then
	case $1 in
	-n | --null )
		opt_null=y
	;;

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
	change-spec*)
		;;
	*)	msg "bad option : $LONG_OPTION (should be called from change-spec*)";
		syntaxe
	;;
esac

while read line
do
	if [ -n "$opt_null" ]
	then
		# do nothing : just repeat
		echo "$line"
	else
		# add the plugin type on each spec line
		# it will not work any more, but let see which part is modified
		echo "$LONG_OPTION $line"
	fi
done 
