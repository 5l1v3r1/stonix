#!/usr/bin/env python3
###############################################################################
#                                                                             #
# Copyright 2019. Triad National Security, LLC. All rights reserved.          #
# This program was produced under U.S. Government contract 89233218CNA000001  #
# for Los Alamos National Laboratory (LANL), which is operated by Triad       #
# National Security, LLC for the U.S. Department of Energy/National Nuclear   #
# Security Administration.                                                    #
#                                                                             #
# All rights in the program are reserved by Triad National Security, LLC, and #
# the U.S. Department of Energy/National Nuclear Security Administration. The #
# Government is granted for itself and others acting on its behalf a          #
# nonexclusive, paid-up, irrevocable worldwide license in this material to    #
# reproduce, prepare derivative works, distribute copies to the public,       #
# perform publicly and display publicly, and to permit others to do so.       #
#                                                                             #
###############################################################################


'''
This is a Unit Test for Rule ConfigureAppleSoftwareUpdate

@author: ekkehard j. koch
@change: 02/27/2013 Original Implementation
@change: 2016/02/10 roy Added sys.path.append for being able to unit test this
                        file as well as with the test harness.
'''

import unittest
import sys

sys.path.append("../../../..")
from src.tests.lib.RuleTestTemplate import RuleTest
from src.stonix_resources.CommandHelper import CommandHelper
from src.tests.lib.logdispatcher_mock import LogPriority
from src.stonix_resources.rules.DisableMediaAutomaticActions import DisableMediaAutomaticActions


class zzzTestRuleDisableMediaAutomaticActions(RuleTest):

    def setUp(self):
        RuleTest.setUp(self)
        self.rule = DisableMediaAutomaticActions(self.config,
                                                 self.environ,
                                                 self.logdispatch,
                                                 self.statechglogger)
        self.rulename = self.rule.rulename
        self.rulenumber = self.rule.rulenumber
        self.ch = CommandHelper(self.logdispatch)
        self.dc = "/usr/bin/defaults"

    def tearDown(self):
        pass

    def runTest(self):
        self.simpleRuleTest()

    def setConditionsForRule(self):
        '''This makes sure the intial report fails by executing the following
        commands:
        defaults -currentHost delete /Library/Preferences/com.apple.digihub com.apple.digihub.blank.cd.appeared
        defaults -currentHost delete /Library/Preferences/com.apple.digihub com.apple.digihub.blank.dvd.appeared
        defaults -currentHost delete /Library/Preferences/com.apple.digihub com.apple.digihub.cd.picture.appeared
        defaults -currentHost delete /Library/Preferences/com.apple.digihub com.apple.digihub.dvd.video.appeared

        :param self: essential if you override this definition
        :returns: boolean - If successful True; If failure False
        @author: ekkehard j. koch

        '''
        success = True
        if success:
            command = [self.dc, "-currentHost", "delete",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.blank.cd.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "delete",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.blank.dvd.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "delete",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.cd.picture.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "delete",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.dvd.video.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            success = self.checkReportForRule(False, True)
        return success

    def checkReportForRule(self, pCompliance, pRuleSuccess):
        '''To see what happended run these commands:
        defaults -currentHost read /Library/Preferences/com.apple.digihub com.apple.digihub.blank.cd.appeared
        defaults -currentHost read /Library/Preferences/com.apple.digihub com.apple.digihub.blank.dvd.appeared
        defaults -currentHost read /Library/Preferences/com.apple.digihub com.apple.digihub.cd.picture.appeared
        defaults -currentHost read /Library/Preferences/com.apple.digihub com.apple.digihub.dvd.video.appeared

        :param self: essential if you override this definition
        :param pCompliance: 
        :param pRuleSuccess: 
        :returns: boolean - If successful True; If failure False
        @author: ekkehard j. koch

        '''
        self.logdispatch.log(LogPriority.DEBUG, "pCompliance = " + \
                             str(pCompliance) + ".")
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = True
        if success:
            command = [self.dc, "-currentHost", "read",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.blank.cd.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "read",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.blank.dvd.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "read",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.cd.picture.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        if success:
            command = [self.dc, "-currentHost", "read",
                       "/Library/Preferences/com.apple.digihub",
                       "com.apple.digihub.dvd.video.appeared"]
            self.logdispatch.log(LogPriority.DEBUG, str(command))
            success = self.ch.executeCommand(command)
        return success

    def checkFixForRule(self, pRuleSuccess):
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = self.checkReportForRule(True, pRuleSuccess)
        return success

    def checkUndoForRule(self, pRuleSuccess):
        self.logdispatch.log(LogPriority.DEBUG, "pRuleSuccess = " + \
                             str(pRuleSuccess) + ".")
        success = self.checkReportForRule(False, pRuleSuccess)
        return success

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
