'''
###############################################################################
#                                                                             #
# Copyright 2015.  Los Alamos National Security, LLC. This material was       #
# produced under U.S. Government contract DE-AC52-06NA25396 for Los Alamos    #
# National Laboratory (LANL), which is operated by Los Alamos National        #
# Security, LLC for the U.S. Department of Energy. The U.S. Government has    #
# rights to use, reproduce, and distribute this software.  NEITHER THE        #
# GOVERNMENT NOR LOS ALAMOS NATIONAL SECURITY, LLC MAKES ANY WARRANTY,        #
# EXPRESS OR IMPLIED, OR ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  #
# If software is modified to produce derivative works, such modified software #
# should be clearly marked, so as not to confuse it with the version          #
# available from LANL.                                                        #
#                                                                             #
# Additionally, this program is free software; you can redistribute it and/or #
# modify it under the terms of the GNU General Public License as published by #
# the Free Software Foundation; either version 2 of the License, or (at your  #
# option) any later version. Accordingly, this program is distributed in the  #
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the     #
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    #
# See the GNU General Public License for more details.                        #
#                                                                             #
###############################################################################
Created on Sep 19, 2012

@author: dkennel
'''
import subprocess
import re
import os
from logdispatcher import LogPriority

class SHupdaterc(object):
    '''
    SHupdaterc is the Service Helper for systems using the rcupdate command to
    configure services. (Debian, Ubuntu and variants) 
    '''


    def __init__(self, environment, logdispatcher):
        '''
        Constructor
        '''
        self.environment = environment
        self.logdispatcher = logdispatcher
        self.cmd = '/usr/sbin/update-rc.d '
        self.svc = '/usr/sbin/service '
        
    def disableservice(self, service):
        '''
        Disables the service and terminates it if it is running.
        
        @param string: Name of the service to be disabled
        @return: Bool indicating success status
        '''
        ret2 = 0
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.disableservice ' + service)
        confsuccess = True
        svcoff = True
        ret = subprocess.call(self.cmd + '-f ' + service + ' remove &> /dev/null',
                              shell=True, close_fds=True )
        if ret != 0:
            confsuccess = False
        if self.isrunning(service):
            ret2 = subprocess.call(self.svc + service + ' stop &> /dev/null',
                                   shell=True, close_fds=True )
            if ret2 != 0:
                svcoff = False
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.disableservice ' + service + ' ' + str(confsuccess) + str(svcoff))
        if confsuccess and svcoff:
            return True
        else:
            return False        
    
    def enableservice(self, service):
        '''
        Enables a service and starts it if it is not running as long as we are
        not in install mode
        
        @param string: Name of the service to be enabled
        @return: Bool indicating success status
        '''
        ret2 = 0
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.enableservice ' + service)
        if not os.path.exists('/etc/init.d/' + service):
            return False
        confsuccess = True
        svcon = True
        ret = subprocess.call(self.cmd + service + ' defaults &> /dev/null',
                              shell=True, close_fds=True )
        if ret != 0:
            confsuccess = False
        if not self.environment.getinstallmode():
            ret2 = subprocess.call(self.svc + service + ' start &> /dev/null',
                                   shell=True, close_fds=True )
            if ret2 != 0:
                svcon = False
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.enableservice ' + service + ' ' + str(confsuccess) + str(svcon))
        if confsuccess and svcon:
            return True
        else:
            return False 
    
    def auditservice(self, service):
        '''
        Checks the status of a service and returns a bool indicating whether or
        not the service is configured to run or not.
        
        @param string: Name of the service to audit
        @return: Bool, True if the service is configured to run
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.auditservice ' + service)
        running = False
        sklist = []
        for rcdir in ['/etc/rc2.d', '/etc/rc3.d', '/etc/rc4.d', '/etc/rc5.d']:
            sklist = sklist + os.listdir(rcdir)
        for entry in sklist:
            if re.search('S..' + service, entry):
                running = True
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.auditservice ' + service + ' '+ str(running))
        return running
    
    def isrunning(self, service):
        '''
        Check to see if a service is currently running.
        
        @param sting: Name of the service to check
        @return: bool, True if the service is already running
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.isrunning ' + service)
        running = False
        chk = subprocess.Popen(self.svc + service + ' status',
                               stdout = subprocess.PIPE,
                               stderr = subprocess.PIPE, shell = True,
                               close_fds = True)
        message = chk.stdout.readlines()
        # some services don't return any output (sysstat) so we call audit
        if len(message) == 0:
            running = self.auditservice(service)
        for line in message:
            if re.search('running', line):
                running = True
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.isrunning ' + service + ' '+ str(running))
        return running
    
    def reloadservice(self, service):
        '''
        Reload (HUP) a service so that it re-reads it's config files. Called
        by rules that are configuring a service to make the new configuration
        active.
        
        @param string: Name of the service to reload
        @return: bool indicating success status
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.reload ' + service)
        if not os.path.exists('/etc/init.d/' + service):
            return False
        if not self.environment.getinstallmode():
            ret = subprocess.call(self.svc + service + ' reload &> /dev/null',
                                   shell=True, close_fds=True )
            self.logdispatcher.log(LogPriority.DEBUG,
                                   'SHupdaterc.reload ' + service + str(ret))
            if ret != 0:
                return False
            else:
                return True
            
    def listservices(self):
        '''
        Return a list containing strings that are service names.
        
        @return: list
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.listservices')
        svclist = os.listdir('/etc/init.d/')
        metafiles = ['README', 'skeleton', 'rc', 'rcS']
        # This list comprehension will filter out filenames listed
        # in metafiles.
        svclist = [service for service in svclist if service not in metafiles]
        self.logdispatcher.log(LogPriority.DEBUG,
                               'SHupdaterc.listservices ' + str(svclist))
        return svclist