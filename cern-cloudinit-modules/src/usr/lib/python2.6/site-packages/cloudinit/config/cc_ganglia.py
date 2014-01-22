#################################################################################
# Author: Cristovao Cordeiro <cristovao.cordeiro@cern.ch>			#
#										#
# Cloud Config module for Ganglia service. 					#
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
import os
import re


# In case this runs to early during the boot, the PATH environment can still be unset. Let's define each necessary command's path
# Using subprocess calls so it raises exceptions directly from the child process to the parent
YUM_cmd = '/usr/bin/yum'
SERVICE_cmd = '/sbin/service'

globals_template = [
	'daemonize',
	'setuid',
	'user',
	'debug_level',
	'max_udp_msg_len',
	'mute',
	'deaf',
	'allow_extra_data',
	'host_dmax',	# in seconds
	'cleanup_threshold',	# in seconds
	'gexec',
	'send_metadata_interval'	# in seconds
]

cluster_template = [
	'name',
	'owner',
	'latlong',
	'url'
]

udpsend_template = [
	'host',
	'port',
	'ttl'
]

udprecv_template = [
	'port',
	'bind'
]


def conf_node(node_f, params, lines):
    if 'globals' in params:
        globals_cfg = params['globals']
        for param, value in globals_cfg.iteritems():
            if param in globals_template:
                for i in range(0,len(lines)):
                    if param in lines[i]:
                        lines[i] = "  %s = %s\n" % (param,str(value))
                        break
    
    aux_send_channel = 0	# Help finding the right block. 
    # Find index offset in lines for faster search
    for i in range(0,len(lines)):
        if 'cluster {' in lines[i]:
            cluster_offset = i
        if 'udp_recv_channel {' in lines[i]:
            offset_recv = i
        if ('mcast_join' in lines[i]) and (aux_send_channel == 0):	# First mcast_joint belongs to udp_send_channel
            offset_send = i
            aux_send_channel = 1
        if 'tcp_accept_channel {' in lines[i]:
            offset_tcp = i
            break	# Final configurable block
 
    if 'cluster' in params:
        cluster_cfg = params['cluster']
        for param, value in cluster_cfg.iteritems():
            if param in cluster_template:
                for l in range(cluster_offset,len(lines)):
                    if param in lines[l]:
                        lines[l] = "  %s = %s\n" % (param,str(value))
                        break

    lines = [word.replace('mcast_join','host') for word in lines]               # Change to 'host' instead of 'mcast_join'. If it isn't passed in cloud-config, it will be changed anyway.

    for u in range(offset_recv, offset_recv+10):    # Erase the 'host' parameter in udp_recv_channel, because it causes parsing errors
        if 'host' in lines[u]:
            lines[u] = ''
            break

    if 'udp_send_channel' in params:
        udp_send_cfg = params['udp_send_channel']
        for param, value in udp_send_cfg.iteritems():
            if param in udpsend_template:
                for a in range(offset_send, len(lines)):
                    if param in lines[a]:
                        lines[a] = "  %s = %s\n" % (param,str(value))
                        break

    if 'udp_recv_channel' in params:
        udp_recv_cfg = params['udp_recv_channel']
        for param, value in udp_recv_cfg.iteritems():
            if param in udprecv_template:
                for u in range(offset_recv, len(lines)):
                    if param in lines[u]:
                        lines[u] = "  %s = %s\n" % (param,str(value))
                        break
  
    if 'tcp_accept_channel' in params:
        tcp_cfg = params['tcp_accept_channel']
        for param, value in tcp_cfg.iteritems():
            if param == 'port':
                for t in range(offset_tcp, len(lines)):    # tcp_accept_channel is generally small. Five iterations just in case.
                    if param in lines[t]:
                        lines[t] = "  %s = %s\n" % (param,str(value))
                        break

    flocal_new = open(node_f, 'w')
    flocal_new.writelines(lines)
    flocal_new.close()

def handle(_name, cfg, cloud, log, _args):
  
    if 'ganglia' not in cfg:
        return
        
    ganglia_cfg = cfg['ganglia']

    if 'install' in ganglia_cfg:
        if ganglia_cfg['install'] == True:
            subprocess.check_call([YUM_cmd,'-y','install','ganglia','ganglia-gmond'])
        
    gmond_conf_file = '/etc/ganglia/gmond.conf'
 
    flocal = open(gmond_conf_file, 'r')     # Open to read all the file and then close it
    node_lines = flocal.readlines()
    flocal.close()
        
    conf_node(gmond_conf_file, ganglia_cfg, node_lines)
        
    os.system('/etc/init.d/gmond restart ; /sbin/chkconfig gmond on')
