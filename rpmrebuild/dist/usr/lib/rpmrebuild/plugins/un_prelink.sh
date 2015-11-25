#!/bin/bash
###############################################################################
#   unset_tag.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2004 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: un_prelink.sh 744 2012-05-15 09:41:43Z gerbier $
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
	msg "this plugin allow to reverse prelink action on includes elf files"
	msg "it must be called with change-files option"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	exit 1

}
###############################################################################

# test for arguments
if [ $# -ne 0 ]
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
	*)	msg "should be called from LONG_OPTION=change-file";
		syntaxe
	;;
esac

elfs=$(find $RPM_BUILD_ROOT -type f -print0 | xargs -0 file | grep ELF | cut -d: -f1 )

[ "$elfs" ] && {
        for i in $elfs
        do
                readelf -S "$i" | grep '\.gnu\.prelink_undo' >/dev/null && {
                        echo "prelink --undo $i"
                        prelink --undo "$i" || exit 1
                }
        done
}
exit 0
