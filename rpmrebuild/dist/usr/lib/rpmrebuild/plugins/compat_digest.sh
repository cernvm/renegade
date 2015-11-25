#!/bin/bash
###############################################################################
#   compat_digest.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2004 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: compat_digest.sh 624 2009-11-11 20:33:41Z gerbier $
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
	msg "this plugin will force rpm digest to be compatible with rpm 4.4 release"
	msg "it must be called with change-spec-preamble option"
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
	change-spec-preamble*)
		;;
	*)	msg "should be called from LONG_OPTION=change-spec-preamble";
		syntaxe
	;;
esac

# Fedora 11 default setup uses SHA256 file hashes, which
# rpm 4.4.x (suse, ...) doesn't understand 
# The used hash is build-time configurable macro, so to
# turn it back to compatible-everywhere MD5 hashes you can set
# %_source_filedigest_algorithm %_binary_filedigest_algorithm macros 
# to value of 1
#  for example add in spec
# %global _binary_filedigest_algorithm 1
# %global _source_filedigest_algorithm 1

# just repeat old spec
while read line
do
	# todo : test if previous spec already contains filedigest macro
	echo "$line"
done

# add new lines
echo "# compat_digest plugin"
echo "%global _binary_filedigest_algorithm 1"
echo "%global _source_filedigest_algorithm 1"
echo "# end of compat_digest plugin"
echo ""
