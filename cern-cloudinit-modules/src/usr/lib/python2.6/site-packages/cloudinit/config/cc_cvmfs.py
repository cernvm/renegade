#################################################################################
# Author: Cristovao Cordeiro <cristovao.cordeiro@cern.ch>			#
#										#
# Cloud Config module for CVMFS service.					#
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
import platform
import urllib
import sys
import os

template = {
    'CVMFS_QUOTA_LIMIT' : '8000',
    'CVMFS_CACHE_BASE' : '/cvmfs_cache',
    'CVMFS_MOUNT_RW' : 'yes'
}

# In case this runs to early during the boot, the PATH environment can still be unset. Let's define each necessary command's path
# Using subprocess calls so it raises exceptions directly from the child process to the parent
RPM_cmd = '/bin/rpm'
YUM_cmd = '/usr/bin/yum'
SERVICE_cmd = '/sbin/service'
CHK_cmd = '/sbin/chkconfig'
CHOWN_cmd = '/bin/chown'

def install_cvmfs():
    if subprocess.call(['/usr/bin/cvmfs2','-V']) == 0:
        print 'CVMFS is already installed'
        return

    # Let's retrieve the current cvmfs release
    ReleaseAux = subprocess.Popen([RPM_cmd, "-q", "--queryformat", "%{version}", "sl-release"], stdout=subprocess.PIPE)
    Release, ReleaseErr = ReleaseAux.communicate()

    ReleaseMajor = Release[0]
    arch = platform.machine()       # Platform info

    # cvmfs package url
    cvmfs_rpm_url = 'http://cvmrepo.web.cern.ch/cvmrepo/yum/cvmfs/EL/'+ReleaseMajor+'/'+arch+'/cvmfs-release-2-3.el'+ReleaseMajor+'.noarch.rpm'
    # Downloading cvmfs .rpm file to /home path
    urllib.urlretrieve(cvmfs_rpm_url, '/home/cvmfs.rpm')
    if subprocess.call([RPM_cmd, "-Uvh", "/home/cvmfs.rpm"]): # If it returns 0 then it is fine
        os.system("rpm -Uvh http://cvmrepo.web.cern.ch/cvmrepo/yum/cvmfs/EL/6/`uname -i`/cvmfs-release-2-4.el6.noarch.rpm")    # Manual installation

    # Install cvmfs packages
    try:
        subprocess.check_call([YUM_cmd,'-y','install','cvmfs-keys','cvmfs','cvmfs-init-scripts'])       # cvmfs-auto-setup can also be installed. Meant for Tier 3's
    except:
        subprocess.call([YUM_cmd,'clean','all'])
        try:
            subprocess.check_call([YUM_cmd,'-y','install','cvmfs-keys','cvmfs','cvmfs-init-scripts'])
        except:
            raise

    os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config setup")

    # Start autofs and make it starting automatically after reboot 
    # Uncomment the following in case cvmfs installation doesn't do it on its own
    '''
    with open('/etc/auto.master', 'r+') as automaster_file:
        autofs_lines = automaster_file.readlines()
        autofs_lines.append('/cvmfs /etc/auto.cvmfs\n+auto.master\n')
        automaster_file.seek(0)
        automaster_file.writelines(autofs_lines)
        automaster_file.close()
    with open('/etc/fuse.conf', 'r+') as fusefile:
        fuse_lines = fusefile.readlines()
        fuse_lines.append('user_allow_other\n')
        fusefile.seek(0)
        fusefile.writelines(fuse_lines)
        fusefile.close()    
    '''
    subprocess.check_call([SERVICE_cmd,'autofs','restart'])
    subprocess.check_call([CHK_cmd,'autofs','on'])

    os.system('sed -i s/SELINUX=enforcing/SELINUX=disabled/g /etc/selinux/config; echo 0 > /selinux/enforce')

    try:
        os.makedirs('/scratch/cvmfs2')
    except OSError:
        print 'Directory /scratch alreadys exists'
         
    subprocess.check_call([CHOWN_cmd,'-R','cvmfs:cvmfs','/scratch/cvmfs2'])


def config_cvmfs(lfile, dfile, cmsfile, params):
  
    if 'install' in params:
        if params['install'] == True:
            install_cvmfs()

    if 'local' in params:
        local_args = params['local']
        for parameter in local_args:
            if (parameter == 'CVMFS_HTTP_PROXY') and not local_args[parameter].startswith('"'):
                template[parameter] = '"%s"' % (local_args[parameter])
            else:
                template[parameter] = local_args[parameter]

    if 'CMS_LOCAL_SITE' in params:
        cmslocal = open(cmsfile, 'w')
        cmslocal.write('export CMS_LOCAL_SITE='+str(params['CMS_LOCAL_SITE'])+'\n')
        cmslocal.close()

    flocal = open(lfile, 'w')
    for parameter in template:
        flocal.write("%s=%s\n" %(parameter, template[parameter]))
    flocal.close()

    if 'domain' in params:
        domain_args = params['domain']
        fdomain = open(dfile, 'w')
        for parameter in domain_args:
            fdomain.write("%s=%s\n" % (parameter, domain_args[parameter]))
        fdomain.close()

def handle(_name, cfg, cloud, log, _args):
    
    if 'cvmfs' not in cfg:
      return
    
    cvmfs_cfg = cfg['cvmfs']

    LocalFile = '/etc/cvmfs/default.local'
    DomainFile = '/etc/cvmfs/domain.d/cern.ch.local'
    CMS_LocalFile = '/etc/cvmfs/config.d/cms.cern.ch.local'
  
    config_cvmfs(LocalFile, DomainFile, CMS_LocalFile, cvmfs_cfg)
	
    os.system("export PATH=${PATH}:/usr/bin:/sbin; cvmfs_config reload; cvmfs_config probe")
