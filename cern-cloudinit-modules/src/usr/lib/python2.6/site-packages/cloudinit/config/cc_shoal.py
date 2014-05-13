#################################################################################
# Author: Cristovao Cordeiro <cristovao.cordeiro@cern.ch>			#
#										#
# Cloud Config module for Shoal service.					#
# Documentation in:								#
# https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit				#
#################################################################################

import subprocess
import cloudinit.util as util
try:
  import cloudinit.CloudConfig as cc
except ImportError:
  import cloudinit.config as cc
except:
  print "There is something wrong with this module installation. Please verify and rerun."
  import sys
  sys.exit(0)
import os


template = {
	'cvmfs_config': '/etc/cvmfs/default.local',
	'shoal_server_url': 'http://localhost:8080/nearest',
	'default_squid_proxy': 'http://chrysaor.westgrid.ca:3128;http://cernvm-webfs.atlas-canada.ca:3128;DIRECT'
}

def handle(_name, cfg, cloud, log, _args):
    if 'shoal' not in cfg:
        return

    shoal_cfg = cfg['shoal']
    LocalFile = '/etc/shoal/shoal_client.conf'
    CronFile = '/etc/crontab_shoal'

    for param in shoal_cfg:
        if param == 'cron_shoal':
            c = open(CronFile,'w')
            c.write(shoal_cfg[param])
            c.close()
            os.system('crontab %s' % CronFile)
        else:
            template[param] = shoal_cfg[param]

    l = open(LocalFile,'w')
    l.write('[general]\n\n')
    for item in template:
        l.write("%s = %s\n" %(item, template[item]))  
    l.close()

    os.system('/usr/bin/shoal-client')
