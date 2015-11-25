#!/bin/sh 
###############################################################################
#    Copyright (C) 2002 by Eric Gerbier
#    Bug reports to: gerbier@users.sourceforge.net
#    $Id: rpmrebuild_extract_tags.sh 720 2012-02-14 09:30:42Z gerbier $
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
# this script is used to extract all rpm tags used in rpmrebuild_rpmqf.src
# and to display a sorted list
###############################################################################
# we have to find regex such 
# %{BUILDHOST} => BUILDHOST
# %{BUILDTIME:date} => BUILDTIME

awk ' 
{
	line = $0
	long = length (line)
	# find begin
	pos_begin = index(line, "%{")
	while (pos_begin > 0) {
		new_line = substr(line, pos_begin +2, long)
		# find end
		pos_end = index(new_line, "}") 
		res = substr(new_line, 1, pos_end - 1)

		# suppress :
		pos = index(res, ":")
		if (pos > 0) {
			split(res, array, ":" )
			print array[1]
		} else {
			print res
		}
		line = new_line
		pos_begin = index(line, "%{")
	}
}' < $1 | sort -u
