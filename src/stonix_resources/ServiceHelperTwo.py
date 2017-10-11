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
Created on Aug 9, 2012

@author: dkennel
@change: 2015/10/15 eball Added method names to debug output
@change: 2015/10/15 eball disableservice now checks audit and isrunning
@change: 2016/06/10 dkennel wrapped audit in try catch in case service is not
installed.
@change: 2016/11/03 rsn upgrading the interface to allow for more flexibility.
'''
import os
import types
import inspect

import . SHchkconfig
import . SHrcupdate
import . SHupdaterc
import . SHsystemctl
import . SHsvcadm
import . SHrcconf
import . SHlaunchd
from . logdispatcher import LogPriority


class ServiceHelper(object):
    '''
    The ServiceHelper class serves as an abstraction layer between rules that
    need to manipulate services and the actual implementation of changing
    service status on various operating systems.

    @Note: Interface methods abstracted to allow for different parameter
           lists for different helpers.  This moves the requirement for 
           input validation the the concrete helpers.

    @author: dkennel
    '''

    def __init__(self, environment, logdispatcher):
        '''
        The ServiceHelper needs to receive the STONIX environment and
        logdispatcher objects as parameters to init.

        @param environment: STONIX environment object
        '''
        self.environ = environment
        self.logdispatcher = logdispatcher
        self.isHybrid = False
        self.isdualparameterservice = False
        self.svchelper = None
        self.secondary = None
        self.service = ""
        self.servicename = ""
        # Red Hat, CentOS, SUSE
        if os.path.exists('/sbin/chkconfig'):
            ischkconfig = True
        else:
            ischkconfig = False
        # Gentoo
        if os.path.exists('/sbin/rc-update'):
            isrcupdate = True
        else:
            isrcupdate = False
        # Ubuntu, Debian
        if os.path.exists('/usr/sbin/update-rc.d'):
            isupdaterc = True
        else:
            isupdaterc = False
        # Fedora, RHEL 7
        if os.path.exists('/bin/systemctl'):
            issystemctl = True
        else:
            issystemctl = False
        # Solaris
        if os.path.exists('/usr/sbin/svcadm'):
            issvcadm = True
        else:
            issvcadm = False
        # FreeBSD
        if os.path.exists('/etc/rc.conf') and \
        os.path.exists('/etc/rc.d/LOGIN'):
            isrcconf = True
        else:
            isrcconf = False
        # OS X
        if os.path.exists('/sbin/launchd'):
            islaunchd = True
            self.isdualparameterservice = True
        else:
            islaunchd = False

        truecount = 0
        for svctype in [ischkconfig, isrcupdate, isupdaterc,
                        issystemctl, issvcadm, isrcconf, islaunchd]:
            if svctype:
                truecount = truecount + 1
        if truecount == 0:
            raise RuntimeError("Could not identify service management " + \
                               "programs")
        elif truecount == 1:
            if ischkconfig:
                self.svchelper = SHchkconfig.SHchkconfig(self.environ,
                                                         self.logdispatcher)
            elif isrcupdate:
                self.svchelper = SHrcupdate.SHrcupdate(self.environ,
                                                       self.logdispatcher)
            elif isupdaterc:
                self.svchelper = SHupdaterc.SHupdaterc(self.environ,
                                                       self.logdispatcher)
            elif issystemctl:
                self.svchelper = SHsystemctl.SHsystemctl(self.environ,
                                                         self.logdispatcher)
            elif issvcadm:
                self.svchelper = SHsvcadm.SHsvcadm(self.environ,
                                                   self.logdispatcher)
            elif isrcconf:
                self.svchelper = SHrcconf.SHrcconf(self.environ,
                                                   self.logdispatcher)
            elif islaunchd:
                self.svchelper = SHlaunchdTwo.SHlaunchd(self.environ,
                                                     self.logdispatcher)
            else:
                raise RuntimeError("Could not identify service management " +
                                   "programs")
        elif truecount > 1:
            self.ishybrid = True
            count = 0
            if issystemctl:
                self.svchelper = SHsystemctl.SHsystemctl(self.environ,
                                                         self.logdispatcher)
                count = 1
            if ischkconfig:
                if count == 0:
                    self.svchelper = SHchkconfig.SHchkconfig(self.environ,
                                                             self.logdispatcher)
                    count = 1
                elif count == 1:
                    self.secondary = SHchkconfig.SHchkconfig(self.environ,
                                                             self.logdispatcher)
            if isrcupdate:
                if count == 0:
                    self.svchelper = SHrcupdate.SHrcupdate(self.environ,
                                                           self.logdispatcher)
                    count = 1
                elif count == 1:
                    self.secondary = SHrcupdate.SHrcupdate(self.environ,
                                                           self.logdispatcher)
            if isupdaterc:
                if count == 0:
                    self.svchelper = SHupdaterc.SHupdaterc(self.environ,
                                                           self.logdispatcher)
                    count = 1
                elif count == 1:
                    self.secondary = SHupdaterc.SHupdaterc(self.environ,
                                                           self.logdispatcher)
            if issvcadm:
                if count == 0:
                    self.svchelper = SHsvcadm.SHsvcadm(self.environ,
                                                       self.logdispatcher)
                    count = 1
                elif count == 1:
                    self.secondary = SHsvcadm.SHsvcadm(self.environ,
                                                       self.logdispatcher)
            if isrcconf:
                if count == 0:
                    self.svchelper = SHrcconf.SHrcconf(self.environ,
                                                       self.logdispatcher)
                    count = 1
                elif count == 1:
                    self.secondary = SHrcconf.SHrcconf(self.environ,
                                                       self.logdispatcher)
            if islaunchd:
                self.svchelper = SHlaunchdTwo.SHlaunchd(self.environ,
                                                     self.logdispatcher)
                count = 1

        self.logdispatcher.log(LogPriority.DEBUG,
                               'ischkconfig:' + str(ischkconfig))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'isrcupdate:' + str(isrcupdate))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'isupdaterc:' + str(isupdaterc))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'issystemctl:' + str(issystemctl))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'issvcadm:' + str(issvcadm))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'isrcconf:' + str(isrcconf))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'ishybrid:' + str(self.ishybrid))
        self.logdispatcher.log(LogPriority.DEBUG,
                               'isdualparameterservice:' +
                               str(self.isdualparameterservice))

    #----------------------------------------------------------------------
    # helper Methods
    #----------------------------------------------------------------------

    def getService(self):
        return self.service

    #----------------------------------------------------------------------

    def getServiceName(self):
        return self.servicename

    #----------------------------------------------------------------------

    def __calledBy(self):
        """
        Log the caller of the method that calls this method
        
        @author: Roy Nielsen
        """
        try:
            filename = inspect.stack()[2][1]
            functionName = str(inspect.stack()[2][3])
            lineNumber = str(inspect.stack()[2][2])
        except Exception, err:
            raise err
        else:
            self.logger.log(LogPriority.DEBUG, "called by: " + \
                                      filename + ": " + \
                                      functionName + " (" + \
                                      lineNumber + ")")

    #----------------------------------------------------------------------

    def isServiceVarValid(self, service):
        """
        Input validator for the service variable
        
        @author: Roy Nielsen
        """
        serviceValid = False
        try:
            #####
            # Generic factory input validation, only for "service", the
            # rest of the parameters need to be validated by the concrete
            # service helper instance.
            if not isinstance(service, basestring):
                raise TypeError("Service: " + str(service) + \
                                " is not a string as expected.")
                serviceValid = False
            elif not service:  # if service is an empty string
                raise ValueError('service specified is blank. ' +\
                                'No action will be taken!')
                serviceValid = False
            elif service : # service is a string of one or more characters
                self.logdispatcher.log(LogPriority.DEBUG,
                                   '-- self.service set to: ' + service)
                serviceValid = True

        except Exception, err:
            self.__calledBy()
            raise err

        return serviceValid

    #----------------------------------------------------------------------

    def setService(self, service, servicename, partition="", userid="", *args, **kwargs):
        '''
        Update the name of the service being worked with.

        @return: Bool indicating success status
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START SET(' + service + ', ' + servicename +
                               ')')

        setServiceSuccess = False

        if self.isServiceVarValid(service):
            setServiceSuccess = self.svchelper.setService(service, **kwargs)
        
        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END SET(' + service + ', ' + servicename +
                               ') = ' + str(setServiceSuccess))

        return setServiceSuccess
        
    #----------------------------------------------------------------------
    # Standard interface to the service helper.
    #----------------------------------------------------------------------

    def disableService(self, service, **kwargs):
        '''
        Disables the service and terminates it if it is running.

        @return: Bool indicating success status
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START DISABLE(' + service + ')')

        disabled = False
        
        if self.setService(service):
            chkSingle = False
            chkSecond = False

            chkSingle = self.svchelper.disableService(self.getService(), **kwargs)
            if self.isHybrid:
                chkSecond = self.secondary.disableService(self.getService, **kwargs)

            if chkSingle or chkSecond:
                disabled = True
            else:
                disabled=False

        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END DISABLE(' + service + \
                               ') = ' + str(disabled))

        return disabled

    #----------------------------------------------------------------------

    def enableService(self, service, **kwargs):
        '''
        Enables a service and starts it if it is not running as long as we are
        not in install mode

        @return: Bool indicating success status
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START ENABLE(' + service + ')')

        enabledSuccess = False
        
        if self.setService(service):
            enabledSingle = False
            enabledSecondary = False

            if not self.auditService(self.getService(), **kwargs):
                if self.svchelper.enableService(self.getService(), **kwargs):
                    enabledSingle = True
                    
                if self.isHybrid:
                    if self.secondary.enableService(self.getService, **kwargs):
                        enabledSecondary = True
                    

            enabledSuccess = enabledSingle or enabledSecondary

        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END ENABLE(' + service + \
                               ') = ' + str(enabledSuccess))
        return enabledSuccess

    #----------------------------------------------------------------------

    def auditService(self, service, **kwargs):
        '''
        Checks the status of a service and returns a bool indicating whether or
        not the service is configured to run or not.

        @return: Bool, True if the service is configured to run
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START AUDIT(' + service + ')')

        auditSuccess = False
        if self.setService(service):
            singleSuccess = False
            secondarySuccess = False
            
            try:
                singleSuccess = self.svchelper.auditService(self.getService(), 
                                                            **kwargs)
            except OSError:
                singleSuccess = False

            if self.isHybrid:
                try:
                    secondarySuccess = self.secondary.auditService(self.getService(),
                                                            **kwargs)
                except OSError:
                    secondarySuccess = False

            if singleSuccess or secondarySuccess:
                auditSuccess = True

        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END AUDIT(' + service + \
                               ') = ' + str(auditSuccess))
        return auditSuccess

    #----------------------------------------------------------------------

    def isRunning(self, service, **kwargs):
        '''
        Check to see if a service is currently running. The enable service uses
        this so that we're not trying to start a service that is already
        running.

        @return: bool, True if the service is already running
        '''
        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START ISRUNNING(' + service + ')')
        isRunning = False
        if self.setService(service):
            singleSuccess = False
            secondarySuccess = False

            try:
                singleSuccess = self.svchelper.isrunning(self.getService(), **kwargs)
                if self.isHybrid:
                    secondarySuccess = self.secondary.isrunning(self.getService(), **kwargs)
            except:
                self.__calledBy()
                raise

            isRunning = singleSuccess or secondarySuccess

        if isRunning:
            self.logdispatcher.log(LogPriority.DEBUG, "Service: " + str(service) + " is running")
        else:
            self.logdispatcher.log(LogPriority.DEBUG, "Service: " + str(service) + " is NOT running")

        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END ISRUNNING(' + service + \
                               ') = ' + str(isRunning))
        return isRunning

    #----------------------------------------------------------------------

    def reloadService(self, service, **kwargs):
        '''
        Reload (HUP) a service so that it re-reads it's config files. Called
        by rules that are configuring a service to make the new configuration
        active. This method ignores services that do not return true when
        self.isrunning() is called. The assumption being that this method is
        being called due to a change in a conf file, and a service that isn't
        currently running will pick up the change when (if) it is started.

        @return: bool indicating success status
        '''

        self.logdispatcher.log(LogPriority.DEBUG,
                               '--START RELOAD(' + service + ')')

        reloadSuccess = False
        if self.setService(service):
            singleSuccess = False
            secondarySuccess = False
            
            try:
                if self.isrunning(self.getService()):
                    singleSuccess = self.svchelper.reloadservice(self.getService(), **kwargs)
                    if self.isHybrid:
                        secondarySuccess = self.secondary.reloadservice(self.getService(), **kwargs)
            except:
                self.__calledBy()
                raise

            reloadSuccess = singleSuccess and secondarySuccess

        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END RELOAD(' + service + \
                               ') = ' + str(reloadSuccess))
        return reloadSuccess

    #----------------------------------------------------------------------

    def listServices(self, **kwargs):
        '''
        List the services installed on the system.

        @return: list of strings
        '''
        self.logdispatcher.log(LogPriority.DEBUG, '--START')

        serviceList = []
        secondaryList = []
        try:
            serviceList = self.svchelper.listServices(**kwargs)
            
            if self.isHybrid:
                secondaryList = self.secondary.listservices()
                if secondaryList:
                    serviceList += secondaryList

        except:
            self.__calledBy()
            raise
            
        self.logdispatcher.log(LogPriority.DEBUG,
                               '-- END = ' + str(serviceList))
        return serviceList
