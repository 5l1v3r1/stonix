###############################################################################
#                                                                             #
# Copyright 2015-2017.  Los Alamos National Security, LLC. This material was  #
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
Created on Dec 10, 2013

@author: dwalker, Breen Malmberg
@change: 02/14/2014 ekkehard Implemented self.detailedresults flow
@change: 03/26/2014 ekkehard convert to ruleKVEditor
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2015/04/14 dkennel updated for new isApplicable
@change: 2015/08/26 ekkehard [artf37771] : DisableCamera(150) - NCAF & Lack of detail in Results - OS X El Capitan 10.11
@change: 2015/11/09 ekkehard - make eligible of OS X El Capitan
@change: 2017/01/19 Breen Malmberg - minor class doc string edit; minor refactor of report and fix methods;
        got rid of unused code blocks (previously commented out) and unused imports; updated the help text to
        include more detail
@change: 2017/07/07 ekkehard - make eligible for macOS High Sierra 10.13
'''

from __future__ import absolute_import

from ..rule import Rule
from ..logdispatcher import LogPriority
from ..CommandHelper import CommandHelper

import re
import traceback


class DisableCamera(Rule):

    def __init__(self, config, environ, logger, statechglogger):
        '''
        '''

        Rule.__init__(self, config, environ, logger, statechglogger)
        self.rulenumber = 150
        self.rulename = "DisableCamera"
        self.formatDetailedResults("initialize")
        self.mandatory = False
        self.rulesuccess = True
        self.sethelptext()
        self.rootrequired = True
        self.guidance = ["CIS 1.2.6"]
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.9', 'r', '10.13.10']}}

        datatype = 'bool'
        key = 'DISABLECAMERA'
        instructions = "To disable the built-in iSight camera, set the value of DISABLECAMERA to True."
        default = False
        self.ci = self.initCi(datatype, key, instructions, default)

    def report(self):
        '''
        check for the existence of the AppleCameraInterface driver in the
        output of kexstat. Report non-compliant if found. Report compliant
        if not found.

        @return: self.compliant
        @rtype: bool
        @author: Breen Malmberg
        @change: dwalker - ??? - ???
        @change: Breen Malmberg - 1/19/2017 - minor doc string edit; minor refactor
        '''

        self.detailedresults = ""
        self.compliant = True
        self.cmdhelper = CommandHelper(self.logdispatch)
        found = False
        cameradriver = "com.apple.driver.AppleCameraInterface"
        cmd = ["/usr/sbin/kextstat"]

        try:

            self.cmdhelper.executeCommand(cmd)
            output = self.cmdhelper.getOutput()
            retcode = self.cmdhelper.getReturnCode()

            if retcode != 0:
                self.detailedresults += "Command: " + str(cmd) + " failed with return code: " + str(retcode) + "\nUnable to determine status of camera!"
                self.compliant = False

            if output:
                for line in output:
                    if re.search(cameradriver, line):
                        found = True
                        break
            else:
                self.logdispatch.log(LogPriority.DEBUG, "The kextstat command produced no output!")

            if found:
                self.detailedresults += "The rule is not compliant because: The camera is currently enabled."
                self.compliant = False

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)

        return self.compliant

    def fix(self):
        '''
        run kextunload on the AppleCameraInterface driver to
        unload it and disable the iSight camera.
        return True if the command succeeds. return False if
        the command fails.

        @return: success
        @rtype: bool
        @author: Breen Malmberg
        @change: dwalker - ??? - ???
        @change: Breen Malmberg - 1/19/2017 - minor doc string edit; minor refactor
        '''

        success = True
        self.detailedresults = ""
        cmd = ["/sbin/kextunload", "-b", "com.apple.driver.AppleCameraInterface"]

        try:

            # only run the fix actions if the CI has been enabled
            if self.ci.getcurrvalue():

                eventlist = self.statechglogger.findrulechanges(self.rulenumber)

                for event in eventlist:
                    self.statechglogger.deleteentry(event)

                self.cmdhelper.executeCommand(cmd)
                retcode = self.cmdhelper.getReturnCode()

                if retcode != 0:
                    self.detailedresults += "Command: " + str(cmd) + " failed with return code: " + str(retcode) + "\nFailed to disable camera!"
                    success = False
                else:
                    self.detailedresults += "Command succeeded: " + str(cmd)

            else:
                self.detailedresults += "\nThe configuration item for this rule was not enabled. Nothing was done."
                self.logdispatch.log(LogPriority.DEBUG, "The fix method was run without the CI being enabled. Nothing was done.")

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", success, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)

        return success
