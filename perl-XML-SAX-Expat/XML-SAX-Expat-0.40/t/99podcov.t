# 99pod.t -- Minimally check POD for code coverage.
#
# $Id$

use strict;
use warnings;
use Test::More;

eval "use Test::Pod::Coverage";
plan skip_all => "Test::Pod::Coverage required for testing pod coverage" if $@;
plan tests => 1;
pod_coverage_ok('XML::SAX::Expat');

