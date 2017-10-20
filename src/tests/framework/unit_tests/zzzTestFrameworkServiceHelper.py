#!/usr/bin/env python
'''
Created on Oct 4, 2012

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

@author: dkennel
@change: 2015/10/15 eball Updated deprecated unittest methods, added
    cron.service for openSUSE and Debian 8 compatibility
@change: roy - adding sys.path.append for both test framework and individual
               test runs.'''
import os
import pwd
import sys
import time
import unittest
from pwd import getpwnam

sys.path.append("../../../..")
from src.stonix_resources.environment import Environment
from src.tests.lib.logdispatcher_lite import LogDispatcher
from src.stonix_resources.ServiceHelper import ServiceHelper
from src.stonix_resources.stonixutilityfunctions import findUserLoggedIn, reportStack

class zzzTestFrameworkServiceHelper(unittest.TestCase):

    def setUp(self):
        self.enviro = Environment()
        self.enviro.setdebugmode(False)
        self.logger = LogDispatcher(self.enviro)
        self.mysh = ServiceHelper(environment=self.enviro, logdispatcher=self.logger)
        self.myservice = 'crond'
        self.myservicename = ""
        if self.enviro.getosfamily() == 'darwin':
            self.myservice = "/Library/LaunchDaemons/gov.lanl.stonix.report.plist"
            self.myservicename = "system/gov.lanl.stonix.report"
        elif self.enviro.getosfamily() == 'solaris':
            self.myservice = 'svc:/system/cron:default'
        elif self.enviro.getosfamily() == 'freebsd':
            self.myservice = 'cron'
        elif os.path.exists('/usr/lib/systemd/system/cron.service'):
            self.myservice = 'cron.service'
        elif os.path.exists('/usr/lib/systemd/system/crond.service'):
            self.myservice = 'crond.service'
        elif os.path.exists('/etc/init.d/vixie-cron'):
            self.myservice = 'vixie-cron'
        elif os.path.exists('/etc/init.d/cron'):
            self.myservice = 'cron'
        try:
            pwuserinfo = ""
            self.userLoggedIn = ""
            self.userLoggedIn = str(findUserLoggedIn(self.logger)).strip()
            pwuserinfo = getpwnam(self.userLoggedIn)
            self.userLoggedInUid = str(pwuserinfo.pw_uid)
        except KeyError, err:
            raise KeyError("username: " + str(self.userLoggedIn) + \
                           " pwuserinfo: " + str(pwuserinfo) + " " + str(err))
        self.startStatus = 'on'
        #####
        # Check if the service is running or not.
        if not self.mysh.isRunning(self.myservice, serviceName=self.myservicename):
            #####
            # If the service is not running, start it.
            self.startStatus = 'off'
            serviceEnabled = self.mysh.enableService(self.myservice, serviceName=self.myservicename)
            self.assertTrue(serviceEnabled, reportStack() + "Cannot enable service: " + str(self.myservice))
            

    def tearDown(self):
        #####
        # if it was off in the first place, and it's running, turn it off.
        if self.startStatus == 'off' and \
           self.mysh.isRunning(self.myservice, serviceName=self.myservicename):
            didDisable = self.mysh.disableService(self.myservice, serviceName=self.myservicename)
            self.assertTrue(didDisable, reportStack() + "Did not disable service: " + str(self.myservice) + " status: " + str(didDisable))

    def testListServices(self):
        svcslist = self.mysh.listServices()
        self.assertTrue(len(svcslist) > 0)

    def testDisableEnable(self):
        didDisable = self.mysh.disableService(self.myservice, serviceName=self.myservicename)
        self.assertTrue(didDisable, reportStack() + "Did not disable service: " + str(self.myservice) + " status: " + str(didDisable))

        auditresult = self.mysh.auditService(self.myservice, serviceName=self.myservicename)
        self.assertFalse(auditresult,
                         reportStack() + "Service not disabled or return from audit not valid: " + str(auditresult))
        time.sleep(3)
        self.assertFalse(self.mysh.isRunning(self.myservice, serviceName=self.myservicename),
                         reportStack() + "Service is still running or return from isrunning not valid")
        serviceEnabled = self.mysh.enableService(self.myservice, serviceName=self.myservicename)
        self.assertTrue(serviceEnabled, reportStack() + "Cannot enable service: " + str(self.myservice))
        self.assertTrue(self.mysh.auditService(self.myservice, serviceName=self.myservicename),
                        reportStack() + "Service not enabled or return from audit not valid")
        time.sleep(3)
        self.assertTrue(self.mysh.isRunning(self.myservice, serviceName=self.myservicename),
                        reportStack() + "Service is not running or return from isrunning not valid")

    def testReloadService(self):
        serviceReloaded = self.mysh.reloadService(self.myservice, serviceName=self.myservicename)
        self.assertTrue(serviceReloaded, reportStack() + 'Service reload returned false')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
