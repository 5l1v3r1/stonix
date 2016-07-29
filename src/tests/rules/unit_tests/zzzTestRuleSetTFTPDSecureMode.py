#!/usr/bin/env python
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
'''
This is a Unit Test for Rule SetTFTPD
Created on Jun 8, 2016

@author: dwalker
'''

from __future__ import absolute_import
import unittest
import sys

sys.path.append("../../../..")
from src.tests.lib.RuleTestTemplate import RuleTest
from src.stonix_resources.CommandHelper import CommandHelper
from src.tests.lib.logdispatcher_mock import LogPriority
from src.stonix_resources.pkghelper import Pkghelper
from src.stonix_resources.stonixutilityfunctions import readFile, setPerms
from src.stonix_resources.stonixutilityfunctions import checkPerms
from src.stonix_resources.rules.SetTFTPDSecureMode import SetTFTPDSecureMode
import os, re

class zzzTestRuleSetTFTPDSecureMode(RuleTest):

    def setUp(self):
        RuleTest.setUp(self)
        self.rule = SetTFTPDSecureMode(self.config,
                                        self.environ,
                                        self.logdispatch,
                                        self.statechglogger)
        self.rulename = self.rule.rulename
        self.rulenumber = self.rule.rulenumber
        self.ch = CommandHelper(self.logdispatch)

    def tearDown(self):
        pass

    def runTest(self):
        self.simpleRuleTest()

    def setConditionsForRule(self):
        '''
        Configure system for the unit test
        @param self: essential if you override this definition
        @return: boolean - If successful True; If failure False
        @author: dwalker
        '''
        success = True
        if not self.environ.getostype() == "Mac OS X":
            self.ph = Pkghelper(self.logger, self.environ)
            if self.ph.manager == "apt-get":
                self.tftpfile = "/etc/default/tftpd-hpa"
                if os.path.exists(self.tftpfile):
                    contents = readFile(self.tftpfile, self.logger)
                    tempstring = ""
                    for line in contents:
                        '''Take TFTP_OPTIONS line out of file'''
                        if re.search("TFTP_OPTIONS", line.strip):
                            continue
                        elif re.search("TFTP_DIRECTORY", line.strip()):
                            tempstring += 'TFTP_DIRECTORY="/var/lib/tftpbad"'
                            continue
                        else:
                            tempstring += line
            else:
                #if server_args line found, remove to make non-compliant
                self.tftpfile = "/etc/xinetd.d/tftp"
                tftpoptions, contents2 = [], []
                if os.path.exists(self.tftpfile):
                    i = 0
                    contents = readFile(self.tftpfile, self.logger)
                    if checkPerms(self.tftpFile, [0, 0, 420], self.logger):
                        setPerms(self.tftpfile, [0, 0, 400], self.logger)  
                    try:
                        for line in contents:
                            if re.search("service tftp", line.strip()):
                                contents2 = contents[i+1:]
                            else:
                                i += 1
                    except IndexError:
                        pass
                    if contents2:
                        if contents2[0].strip() == "{":
                            del(contents2[0])
                        if contents2:
                            i = 0
                            while i <= len(contents2) and contents2[i].strip() != "}" and contents2[i].strip() != "{":
                                tftpoptions.append(contents2[i])
                                i += 1
                            if tftpoptions:
                                for line in tftpoptions:
                                    if re.search("server_args", line):
                                        contents.remove(line)
        return success

    def checkReportForRule(self, pCompliance, pRuleSuccess):
        '''
        check on whether report was correct
        @param self: essential if you override this definition
        @param pCompliance: the self.iscompliant value of rule
        @param pRuleSuccess: did report run successfully
        @return: boolean - If successful True; If failure False
        @author: ekkehard j. koch
        '''
        self.logdispatch.log(LogPriority.DEBUG, "pCompliance = " + \
                             str(pCompliance) + ".")
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = True
        return success

    def checkFixForRule(self, pRuleSuccess):
        '''
        check on whether fix was correct
        @param self: essential if you override this definition
        @param pRuleSuccess: did report run successfully
        @return: boolean - If successful True; If failure False
        @author: ekkehard j. koch
        '''
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = True
        return success

    def checkUndoForRule(self, pRuleSuccess):
        '''
        check on whether undo was correct
        @param self: essential if you override this definition
        @param pRuleSuccess: did report run successfully
        @return: boolean - If successful True; If failure False
        @author: ekkehard j. koch
        '''
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = True
        return success

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

