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
This is a Unit Test for Rule MinimizeAcceptedDHCPOptions

@author: Breen Malmberg - 6/13/2016
'''

from __future__ import absolute_import
import os
import unittest
import sys
from shutil import copyfile

sys.path.append("../../../..")
from src.tests.lib.RuleTestTemplate import RuleTest
from src.stonix_resources.CommandHelper import CommandHelper
from src.tests.lib.logdispatcher_mock import LogPriority
from src.stonix_resources.rules.MinimizeAcceptedDHCPOptions import MinimizeAcceptedDHCPOptions


class zzzTestRuleMinimizeAcceptedDHCPOptions(RuleTest):

    def setUp(self):
        RuleTest.setUp(self)
        self.rule = MinimizeAcceptedDHCPOptions(self.config,
                              self.environ,
                              self.logdispatch,
                              self.statechglogger)
        self.rulename = self.rule.rulename
        self.rulenumber = self.rule.rulenumber
        self.ch = CommandHelper(self.logdispatch)

        self.fileexisted = False
        if os.path.exists(self.rule.filepath):
            self.fileexisted = True
            copyfile(self.rule.filepath, self.rule.filepath + '.stonixtestbak')

    def tearDown(self):
        if os.path.exists(self.rule.filepath + '.stonixtestbak'):
            copyfile(self.rule.filepath + '.stonixtestbak', self.rule.filepath)
            os.remove(self.rule.filepath + '.stonixtestbak')
        if os.path.exists(self.rule.filepath):
            if not self.fileexisted:
                os.remove(self.rule.filepath)

    def setConditionsForRule(self):
        '''
        Configure system for the unit test
        @param self: essential if you override this definition
        @return: boolean - If successful True; If failure False
        @author: Breen Malmberg
        '''
        success = True
        return success

    def test_static(self):
        '''
        test with whatever the current system configuration
        is

        @author: Breen Malmberg
        '''

        self.simpleRuleTest()

    def test_nofile(self):
        '''
        run test with no dhclient.conf file present

        @author: Breen Malmberg
        '''

        if os.path.exists(self.rule.filepath):
            os.remove(self.rule.filepath)
        self.simpleRuleTest()

    def test_blankfile(self):
        '''
        run test with a blank dhclient.conf file present

        @author: Breen Malmberg
        '''

        dirname = os.path.dirname(self.rule.filepath)
        if not os.path.exists(self.rule.filepath):
            os.makedirs(dirname, 0755)
        f = open(self.rule.filepath, 'w')
        f.write('')
        f.close()
        self.simpleRuleTest()

    def test_garbage(self):
        '''
        test with a file that has garbage contents

        @author: Breen Malmberg
        '''

        dirname = os.path.dirname(self.rule.filepath)
        if not os.path.exists(self.rule.filepath):
            os.makedirs(dirname, 0755)
        f = open(self.rule.filepath, 'w')
        f.write(' (*#%HJSDnvlw jk34nrl24km \n\nrl23978Y*@$&G i4w\n')
        f.close()
        self.simpleRuleTest()

    def test_partialconfig(self):
        '''
        test with a partially configured file

        @author: Breen Malmberg
        '''

        dirname = os.path.dirname(self.rule.filepath)
        if not os.path.exists(self.rule.filepath):
            os.makedirs(dirname, 0755)
        f = open(self.rule.filepath, 'w')
        f.write('supersede subnet-mask "example.com";\nsupersede domain-name "example.com";\nrequest broadcast-address;\nrequire broadcast-address;\n')
        f.close()
        self.simpleRuleTest()

    def checkReportForRule(self, pCompliance, pRuleSuccess):
        '''
        check on whether report was correct
        @param self: essential if you override this definition
        @param pCompliance: the self.iscompliant value of rule
        @param pRuleSuccess: did report run successfully
        @return: boolean - If successful True; If failure False
        @author: ekkehard j. koch
        '''
        self.logdispatch.log(LogPriority.DEBUG, "pCompliance = " +
                             str(pCompliance) + ".")
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " +
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
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " +
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
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " +
                             str(pRuleSuccess) + ".")
        success = True
        return success

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
