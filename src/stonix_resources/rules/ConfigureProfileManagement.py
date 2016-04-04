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
#from __builtin__ import False
'''
Created on Feb 10, 2015

@author: dwalker
@change: 2015/04/14 dkennel updated for new isApplicable
'''
from __future__ import absolute_import
import traceback
import re
import sys
import os
from ..rule import Rule
from ..CommandHelper import CommandHelper
from ..logdispatcher import LogPriority
from ..stonixutilityfunctions import iterate
from ..KVEditorStonix import KVEditorStonix


class ConfigurePasswordProfile(Rule):
    '''
    Deploy Passcode Policy configuration profiles for OS X Mavericks 10.9
    & OS Yosemite 10.10. Profile files are installed using the following
    OS X command.
    '''
    def __init__(self, config, environ, logdispatch, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logdispatch, statechglogger)

        self.logger = logdispatch
        self.rulenumber = 106
        self.rulename = "ConfigureProfileManagement"
        self.formatDetailedResults("initialize")
        self.helptext = "ConfigurePasswordProfile rule configures the " + \
            "Mac OSX operating system's password policy according to LANL " + \
            "standards and practices."
        self.rootrequired = True
        datatype = "bool"
        key = "PASSCODECONFIG"
        instructions = "To disable this rule set the value of " + \
            "PASSCODECONFIG to False"
        default = True
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.10', 'r', '10.11.13']}}
        self.ci = self.initCi(datatype, key, instructions, default)
        self.iditerator = 0
        
    def report(self):
        '''
        @since: 3/9/2016
        @author: dwalker
        first item in dictionary - identifier (multiple can exist)
            first item in second nested dictionary - key identifier within
                opening braces in output
            first item in nested list is the expected value after the = in
                output (usually a number, in quotes "1"
            second item in nested list is accepted datatype of value after
                the = ("bool", "int")
            third item in nested list (if int) is whether the allowable value
                is allowed to be more or less and still be ok
                "more", "less"
                '''
        try:
            compliant = True
            self.detailedresults = ""
            cmd = ["/usr/sbin/system_profiler",
                   "SPConfigurationProfileDataType"]
            self.ch = CommandHelper(self.logger)
            self.neededprofiles = []
            '''form key = val;'''
            
            self.pwprofiledict = {"com.apple.mobiledevice.passwordpolicy": {"allowSimple": ["1", "bool"],
                                                                            "forcePIN": ["1", "bool"],
                                                                            "maxFailedAttempts" :["4", "int", "less"],
                                                                            "maxPINAgeInDays": ["180", "int", "more"],
                                                                            "minComplexChars": ["1", "int", "more"],
                                                                            "minLength": ["14", "int", "more"],
                                                                            "minutesUntilFailedLoginReset":["15", "int", "more"],
                                                                            "pinHistory": ["5", "int", "more"],
                                                                            "requireAlphanumeric": ["1", "bool"]}}
            self.spprofiledict =  {"com.apple.screensaver": "",
                                   "com.apple.loginwindow": "",
                                   "com.apple.systempolicy.managed": "",
                                   "com.apple.SubmitDiagInfo": "",
                                   "com.apple.preference.security": "",
                                   "com.apple.MCX": "",
                                   "com.apple.applicationaccess": "",
                                   "com.apple.systempolicy.control": ""}

            self.profpaths = {os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]))) + "/stonix_resources/files/stonix4macPasscodeProfileForOSXElCapitan10.11STIG.mobileconfig": self.pwprofiledict,
                              os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]))) + "/stonix_resources/files/stonix4macSecurity&PrivacyForOSXElCapitan10.11.mobileconfig": self.spprofiledict}
            '''Run the system_proflier command'''
            if self.ch.executeCommand(cmd):
                output = self.ch.getOutput()
                if output:
                    for profilepath, values in self.profpaths.iteritems():
                        self.editor = KVEditorStonix(self.statechglogger,
                                                     self.logger, "profiles",
                                                     "", "", values, "", "",
                                                     output)
                        if not self.editor.report():
                            self.neededprofiles.append(profilepath)
                else:
                    self.detailedresults += "There are no profiles installed\n"
                    for profile in self.profpaths:
                        self.neededprofiles.append(profile)
            else:
                self.detailedresults += "Unable to run the system_profile " + \
                    "command\n"
                compliant = False
            if self.neededprofiles:
                compliant = False
            self.compliant = compliant
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

###############################################################################

    def fix(self):
        try:
            if not self.ci.getcurrvalue():
                return
            self.detailedresults = ""

            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)
            success = True
            pathsexist = True
            if self.neededprofiles:
                for profilepath in self.profpaths:
                    if not os.path.exists(profilepath):
                        pathsexist = False
                        break
                if not pathsexist:
                    self.detailedresults += "You need profiles installed " + \
                        "but you don't have all the necessary profiles\n"
                    success = False
                else:
                    for profile in self.neededprofiles:
                        cmd = ["/usr/bin/profiles", "-I", "-F", profile]
                        if self.ch.executeCommand(cmd):
                            self.iditerator += 1
                            myid = iterate(self.iditerator, self.rulenumber)
                            undocmd = ["/usr/bin/profiles", "-R", "-F", profile]
                            event = {"eventtype": "comm",
                                     "command": undocmd}
                            self.statechglogger.recordchgevent(myid, event)
                        else:
                            success = False
            self.rulesuccess = success
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess
