#!/bin/bash
###############################################################################
#   nodoc.sh
#      it's a part of the rpmrebuild project
#
#    Copyright (C) 2002 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#      or	   : valery_reznic@users.sourceforge.net
#    $Id: nodoc.sh 410 2005-05-31 12:02:16Z gerbier $
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
# code's file of nodoc plugin for rpmrebuild

version=1.1

###############################################################################
function msg () {
	echo >&2 $*
}
###############################################################################
function syntaxe () {
	msg "this plugin remove documentation from package"
	msg "it can be called with : rpmrebuild --change-spec-files"
	msg "-m|--man : just remove man pages"
	msg "-d|--doc : just remove doc files"
	msg "-h|--help : this help"
	msg "-v|--version : print plugin version"
	exit 1

}
###############################################################################

# default is to treat all docs
opt_all=y
# test for arguments
if [ $# -eq 1 ]
then
	case $1 in
	-h | --help )
		syntaxe
	;;

	-m | --man )
		opt_man=y
		opt_all=''
	;;

	-d | --doc )
		opt_doc=y
		opt_all=''
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

if [ -n "$opt_all" ]
then
	opt_man=y
	opt_doc=y
fi

# test the way to be called
if [ "$LONG_OPTION" != "change-spec-files" ]
then
	msg "error : $0 can not be called by $LONG_OPTION"
	syntaxe
	exit 1
fi

while read line
do
	skip=''
	# first code style
#	if [ -n "$opt_doc" ]
#	then
#		out=$(echo $line | grep "^%doc")
#		if [ -n "$out" ]
#		then
#			skip=y
#		fi
#	fi
#	if [ -n "$opt_man" ]
#	then
#		out=$(echo $line | egrep "/man/man[[:alnum:]]*/|/man/[[:alpha:]]*/man[[:alnum:]]*/" )
#		if [ -n "$out" ]
#		then
#			skip=y
#		fi
#	fi
	# second code style (avoid call to external grep process)
	case "$line" in
   		%doc*)
			#echo "%doc found"
      			case "$line" in
				*/man*/man*/* | */man*/*/man*/*)
					#echo "man found"
         				# process manpages
					if [ -n "$opt_man" ]
					then
						skip=y
					fi
      					;;
      				*)
          				# process docs
					#echo "doc found"
					if [ -n "$opt_doc" ]
					then
						skip=y
					fi
      					;;        
      			esac
			;;
    		*)
        		# process nodoc
    			;;
	esac
	if [ -z "$skip" ]
	then
		echo $line
	fi
done
