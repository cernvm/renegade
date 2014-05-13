#################################################################################
# Author: Cristovao Cordeiro <cristovao.cordeiro@cern.ch>			#
#										#
# Cloud Config module for Condor service. 					#
# Documentation in:								#
# https://twiki.cern.ch/twiki/bin/view/LCG/CloudInit				#
#################################################################################

import subprocess
try:
  import cloudinit.CloudConfig as cc
except ImportError:
  import cloudinit.config as cc
except:
  print "There is something wrong with this module installation. Please verify and rerun."
  import sys
  sys.exit(0)
import urllib
import os
import re
import socket
import pwd
import multiprocessing

# In case this runs to early during the boot, the PATH environment can still be unset. Let's define each necessary command's path
# MACROS:
YUM_cmd = '/usr/bin/yum'
SERVICE_cmd = '/sbin/service'
CHOWN_cmd = '/bin/chown'

# Condor default template:
template = {
	
	'DAEMON_LIST' : 'MASTER, STARTD',
	'HIGHPORT' : '24500',
	'LOWPORT' : '20000',
	'START' : 'TRUE',
	'SUSPEND' : 'FALSE',
	'PREEMPT' : 'FALSE', 
	'KILL' : 'FALSE',
	'QUEUE_SUPER_USERS' : 'root, condor',
	'ALLOW_WRITE' : 'condor@*.*',
	'STARTER_ALLOW_RUNAS_OWNER' : 'False',
	'ALLOW_DAEMON' : '*',
	'RELEASE_DIR' : '/usr', 
	'LOCAL_DIR' : '/var', 
	'RANK' : '0'

}


def install_condor():
    print 'Starting Condor installation: '
    subprocess.check_call([YUM_cmd,"-y","install","libtool-ltdl","libvirt","perl-XML-Simple","openssl098e","compat-expat1","compat-openldap","perl-DateManip","perl-Time-HiRes","policycoreutils-python"])

    print 'Overwriting condor_config.local'

    CondorRepo = "http://www.cs.wisc.edu/condor/yum/repo.d/condor-stable-rhel6.repo"
    urllib.urlretrieve(CondorRepo,'/etc/yum.repos.d/condor.repo')

    subprocess.check_call([YUM_cmd,'-y','install','condor'])

    os.environ['PATH'] = os.environ['PATH']+"/usr/sbin:/sbin"
    os.environ['CONDOR_CONFIG'] = "/etc/condor/condor_config"
  
    try:
        os.makedirs('/scratch/condor')
    except OSError:
        print 'Directory /scratch alreadys exists'
        
    subprocess.call([CHOWN_cmd,'condor:condor','/scratch/condor'])
    subprocess.call(["/bin/ln -s /etc/condor/condor_config.local /etc/condor/config.d/condor_config.local"], shell=True)


def handle(_name, cfg, cloud, log, _args):
    if 'condor' not in cfg:
        return

    condor_cc_cfg = cfg['condor'] 

    subprocess.call([SERVICE_cmd,'condor','stop']) 

    # Condor configuration file
    ConfigFile = '/etc/condor/condor_config.local'

    try:
        IPAddress = socket.gethostbyname(socket.gethostname())
    except: 		# Sometimes the IP is resolved when this runs, so...
        IPAddress = '$(IP_ADDRESS)'

    slot_dynamic = True
    # Read userdata configuration
    # Allow any parameter on the userdata - user's responsability
    for parameter in condor_cc_cfg:
        # IP_ADDRESS is a key for a dynamic configuration of the IP address
        if 'IPADDRESS' in str(condor_cc_cfg[parameter]):
            template[parameter] = re.sub('IPADDRESS',IPAddress,str(condor_cc_cfg[parameter]))
        else:
            # pool-password is not a configuration
            if parameter == 'pool-password':
                try:
                    pp = open(condor_cc_cfg['SEC_PASSWORD_FILE'],'w')
                except KeyError:
                    pp = open('/root/pool_password','w')
                except:
                    raise
                pp.write(condor_cc_cfg['pool-password']) 
                pp.close()
            elif (parameter == 'install') and (condor_cc_cfg[parameter] == True):
                install_condor() 
            else:
                template[parameter] = condor_cc_cfg[parameter]        
                if re.match('SLOT[\d]_USER', parameter):
                    os.system("/usr/sbin/useradd -m -s /sbin/nologin  %s > /dev/null 2>&1\n" % (condor_cc_cfg[parameter]))
                    slot_dynamic = False
            
    # Dynamically writing SLOT users
    condor_uid = pwd.getpwnam('condor').pw_uid
    condor_gid = pwd.getpwnam('condor').pw_gid
    template['CONDOR_ID'] = "%s.%s" % (condor_uid, condor_gid)

    if slot_dynamic:
        for count in range(1, multiprocessing.cpu_count() + 1):
            parameter = "SLOT%s_USER" % (count)
            template[parameter] = "cuser%s" % (count)
            os.system("/usr/sbin/useradd -m -s /sbin/nologin  cuser%s > /dev/null 2>&1\n" % (count)) 
    
    # Write new configuration file
    f = open(ConfigFile,'w')        
    for parameter in template:
        f.write("%s = %s\n" %(parameter, template[parameter]))
    f.close()

    subprocess.check_call([SERVICE_cmd,'condor','start'])
