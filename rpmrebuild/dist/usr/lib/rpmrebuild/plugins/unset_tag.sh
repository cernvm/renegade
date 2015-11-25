#!/bin/bash
###############################################################################
#   unset_tag.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2004 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: unset_tag.sh 744 2012-05-15 09:41:43Z gerbier $
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

version=1.0
###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin allow to delete a tag"
	msg "it must be called with change-spec-preamble option"
	msg "-t|--tag yourtag : remove the tag yourtag"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	msg "you can also provide the tag id by the TAG_ID environment variable"
	exit 1

}
###############################################################################

# test for arguments
if [ $# -ne 0 ]
then
	case $1 in
	-t | --tag )
		opt_tag=$2
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
else
	# we can also provide value by environment
	if [ -n "$TAG_ID" ]
	then
		opt_tag=$TAG_ID
	else
		syntaxe
	fi
fi

# test the way to be called
case $LONG_OPTION in
	change-spec-preamble*)
		;;
	*)	msg "should be called from LONG_OPTION=change-spec-preamble";
		syntaxe
	;;
esac

# comment the tag opt_tag"
sed "s/^\($opt_tag: .*\)/# \1/"
