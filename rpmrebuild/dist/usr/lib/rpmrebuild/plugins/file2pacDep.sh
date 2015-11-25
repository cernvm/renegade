#!/bin/bash
###############################################################################
#   file2pacDep.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2002 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: file2pacDep.sh 381 2005-03-01 09:51:12Z valery_reznic $
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
# code's file of file2pacDep plugin for rpmrebuild

# for performance
# frst search all motifs, then transform all with only one call

version=1.0

function analyse () {
	# build the list of file dependencies
	# without any version dependence
	tag=$1
	shift
	name=$1
	shift
	remain=$*
	if [ -n "$remain" ]
	then
		# the line is : Require name relation version
		# write it without change
		echo "$tag $name $remain"
	elif [ -n "$opt_all" ]
	then
		# the line is : Require name
		# add the name to list
		liste="$liste $name"
	else
		is_done=''
		if [ -n "$opt_lib" ]
		then
			is_lib=$( echo $name | grep "^lib" )
			if [ -n "$is_lib" ]
			then
				liste="$liste $name"
				is_done=y
			fi

		fi
		if [ -n "$opt_file" ]
		then
			is_file=$( echo $name | grep "^\/" )
			if [ -n "$is_file" ]
			then
				liste="$liste $name"
				is_done=y
			fi

		fi
		# if not done, print as it
		if [ -z "$is_done" ]
		then
			echo "$tag $name"
		fi
	fi
}
###############################################################################

function transform () {
	# rewrite require to file into require to packages
	if [ -n "$liste" ]
	then
		#msg "liste =\"$liste\""
		if [ -n "$opt_forceversion" ]
		then
			rpm --query --qf 'Requires: %{NAME} > = %{VERSION}\n' --whatprovides $liste | sort -u
		else
			rpm --query --qf 'Requires: %{NAME}\n' --whatprovides $liste | sort -u
		fi
	fi
}
###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin transform all dependencies to files into dependencies to package"
	msg "it can be called with : rpmrebuild --change-spec-requires"
	msg "-f|--file : just replace files (with path) by package"
	msg "-l|--lib : just replace lib file by packages"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	msg "-V|--forceversion : add dependency to version"
	exit 1

}
###############################################################################

# default is to treat all dependencies
opt_all=y
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

	-V | --forceversion )
		opt_forceversion=y
	;;

	-f | --file )
		opt_file=y;
		opt_all='';
	;;

	-l | --lib )
		opt_lib=y;
		opt_all='';
	;;

	*)
		msg "bad option : $1";
		syntaxe
	;;
	esac
fi

# test the way to be called
if [ "$LONG_OPTION" != "change-spec-requires" ]
then
	msg "error : $0 can not be called by $LONG_OPTION"
	syntaxe
	exit 1
fi

liste=""
while read line
do
	analyse $line
done
transform
