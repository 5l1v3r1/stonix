###############################################################################
#                                                                             #
# Copyright 2017.  Los Alamos National Security, LLC. This material was       #
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
Created on May 15, 2017

@author: Breen Malmberg
@change: 2017/07/07 ekkehard - make eligible for macOS High Sierra 10.13
'''

from __future__ import absolute_import

import os
import traceback
import re

from ..rule import Rule
from ..CommandHelper import CommandHelper
from ..logdispatcher import LogPriority


class DisableTouchID(Rule):
    '''
    classdocs
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 102
        self.rulename = 'DisableTouchID'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.rootrequired = True
        self.environ = environ
        self.sethelptext()
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.12.3', '+']}}
        datatype = 'bool'
        key = 'DisableTouchID'
        instructions = "To prevent this rule from running, set the value of DisableTouchID to False."
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)
        self.guidance = ['(None)']

        self.initobjs()

    def initobjs(self):
        '''
        init objects used by this class

        @author: Breen Malmberg
        '''

        self.ch = CommandHelper(self.logger)
        self.fixed = False

    def report(self):
        '''
        check status of touch id

        @return: self.compliant
        @rtype: bool
        @author: Breen Malmberg
        '''

        self.detailedresults = ""
        self.compliant = True
        checkstrings = {"System Touch ID configuration:": False,
                        "Operation performed successfully": False}
        bioutil = "/usr/bin/bioutil"
        reportcmd = bioutil + " -r -s"
        touchidinstalled = False

        try:

            if not os.path.exists(bioutil):
                self.logger.log(LogPriority.DEBUG, "The required bioutil utility was not found")
                self.compliant = False
                self.formatDetailedResults("report", self.compliant, self.detailedresults)
                self.logger.log(LogPriority.INFO, self.detailedresults)
                return self.compliant

            self.ch.executeCommand(reportcmd)
            outlist = self.ch.getOutput()

            if not outlist:
                self.logger.log(LogPriority.DEBUG, "bioutil command returned no output!")
                self.compliant = False
                self.formatDetailedResults("report", self.compliant, self.detailedresults)
                self.logger.log(LogPriority.INFO, self.detailedresults)
                return self.compliant

            for line in outlist:
                if re.search("Touch ID functionality", line, re.IGNORECASE):
                    touchidinstalled = True

            if touchidinstalled:
                checkstrings = {"System Touch ID configuration:": False,
                                "Touch ID functionality: 0": False,
                                "Touch ID for unlock: 0": False,
                                "Operation performed successfully": False}

            for line in outlist:
                for cs in checkstrings:
                    if re.search(cs, line, re.IGNORECASE):
                        checkstrings[cs] = True

            for cs in checkstrings:
                if not checkstrings[cs]:
                    self.compliant = False
                    self.detailedresults += "\nTouch ID is still enabled."

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            self.compliant = False
            self.detailedresults = traceback.format_exc()
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        self.logger.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fix(self):
        '''
        turn off touch id functionality

        @return: self.rulesuccess
        @rtype: bool
        @author: Breen Malmberg
        '''

        self.detailedresults = ""
        self.rulesuccess = True
        fixcmd1 = "/usr/bin/bioutil -w -s -u 0"
        fixcmd2 = "/usr/bin/bioutil -w -s -f 0"
        checkstring = "Operation performed successfully"

        try:

            if self.ci.getcurrvalue():

                self.ch.executeCommand(fixcmd1)
                outlist = self.ch.getOutput()
    
                if not outlist:
                    self.logger.log(LogPriority.DEBUG, "bioutil command returned no output!")
                    self.detailedresults += "\n"
                    self.rulesuccess = False
                    self.formatDetailedResults("fix", self.compliant, self.detailedresults)
                    self.logger.log(LogPriority.INFO, self.detailedresults)
                    return self.rulesuccess
    
                cmdsuccess = False
                for line in outlist:
                    if re.search(checkstring, line, re.IGNORECASE):
                        cmdsuccess = True
    
                if not cmdsuccess:
                    self.rulesuccess = False
                    self.detailedresults += "\nFailed to turn off Touch ID unlock"
    
                self.ch.executeCommand(fixcmd2)
                outlist = self.ch.getOutput()
    
                if not outlist:
                    self.logger.log(LogPriority.DEBUG, "bioutil command returned no output!")
                    self.rulesuccess = False
                    self.formatDetailedResults("fix", self.compliant, self.detailedresults)
                    self.logger.log(LogPriority.INFO, self.detailedresults)
                    return self.rulesuccess
    
                cmdsuccess = False
                for line in outlist:
                    if re.search(checkstring, line, re.IGNORECASE):
                        cmdsuccess = True
    
                if not cmdsuccess:
                    self.rulesuccess = False
                else:
                    self.fixed = True

            else:
                self.detailedresults += "\nCI was not enabled. Nothing was fixed."
                self.logger.log(LogPriority.DEBUG, "User ran rule without CI enabled. Nothing was fixed.")

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults = traceback.format_exc()
        self.formatDetailedResults("fix", self.compliant, self.detailedresults)
        self.logger.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess

    def undo(self):
        '''
        reverse the fix actions which were applied

        @return: success
        @rtype: bool
        @author: Breen Malmberg
        '''

        self.detailedresults = ""
        success = True
        undocmd1 = "/usr/bin/bioutil -w -s -f 1"
        undocmd2 = "/usr/bin/bioutil -w -s -u 1"

        try:

            if self.fixed:

                self.ch.executeCommand(undocmd1)
                retval = self.ch.getReturnCode()
                if retval != 0:
                    success = False
                    self.detailedresults += "\nEncountered an error while trying to undo the fix actions."
    
                self.ch.executeCommand(undocmd2)
                retval = self.ch.getReturnCode()
                if retval != 0:
                    success = False
                    self.detailedresults += "\nEncountered an error while trying to undo the fix actions."
    
                if success:
                    self.fixed = False

            else:
                self.detailedresults += "\nSystem already in original state. Nothing to undo."

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            success = False
            self.detailedresults = traceback.format_exc()
        self.formatDetailedResults("undo", success, self.detailedresults)
        self.logger.log(LogPriority.INFO, self.detailedresults)
        return success
        