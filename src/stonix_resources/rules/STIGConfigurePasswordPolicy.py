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
Created on Aug 23, 2016

@author: dwalker
'''
from __future__ import absolute_import
import traceback
import os
from re import search
from ..rule import Rule
from ..logdispatcher import LogPriority
from ..stonixutilityfunctions import iterate
from ..CommandHelper import CommandHelper


class STIGConfigurePasswordPolicy(Rule):
    '''
    Deploy Passcode Policy configuration profiles for OS X Yosemite 10.10
    '''
    def __init__(self, config, environ, logdispatch, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logdispatch, statechglogger)

        self.logger = logdispatch
        self.rulenumber = 361
        self.rulename = "STIGConfigurePasswordPolicy"
        self.formatDetailedResults("initialize")
        self.helptext = "STIGConfigurePasswordPolicy rule configures the " + \
            "Mac OSX operating system's password policy according to LANL " + \
            "standards and practices."
        self.rootrequired = True
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.10', 'r', '10.11']}}
        datatype = "bool"
        key = "STIGPWPOLICY"
        instructions = "To disable the installation of the password " + \
            "profile set the value of STIGPWPOLICY to False"
        default = True
        self.pwci = self.initCi(datatype, key, instructions, default)
        
        datatype = "bool"
        key = "STIGSECPOLICY"
        instructions = "To disable the installation of the security " + \
            "profile set the value of STIGSECPOLICY to False"
        default = True
        self.sci = self.initCi(datatype, key, instructions, default)
        self.iditerator = 0
        if search("10\.10.*", self.environ.getosver()):
#             self.pwprofile = "/Users/username/src/" + \
#                 "stonix_resources/files/" + \
#                 "U_Apple_OS_X_10-10_Workstation_V1R2_STIG_Passcode_Policy.mobileconfig"
#             self.secprofile = "/Users/username/src/" + \
#                 "stonix_resources/files/" + \
#                 "U_Apple_OS_X_10-10_Workstation_V1R2_STIG_Security_privacy_Policy.mobileconfig"
            self.pwprofile = "/Applications/stonix4mac.app/Contents/" + \
                             "Resources/stonix.app/Contents/MacOS/" + \
                             "stonix_resources/files/" + \
                             "U_Apple_OS_X_10-10_Workstation_V1R2_STIG_Passcode_Policy.mobileconfig"
            self.secprofile = "/Applications/stonix4mac.app/Contents/" + \
                              "Resources/stonix.app/Contents/MacOS/" + \
                              "stonix_resources/files/" + \
                              "U_Apple_OS_X_10-10_Workstation_V1R2_STIG_Security_Privacy_Policy.mobileconfig"
        elif search("10\.11\.*", self.environ.getosver()):
#             self.pwprofile = "/Users/username/src/" + \
#                 "stonix_resources/files/" + \
#                 "U_Apple_OS_X_10-11_V1R1_STIG_Passcode_Policy.mobileconfig"
#             self.secprofile = "/Users/username/src/" + \
#                 "stonix_resources/files/" + \
#                 "U_Apple_OS_X_10-11_V1R1_STIG_Security_and_Privacy_Policy.mobileconfig"
            self.pwprofile = "/Applications/stonix4mac.app/Contents/" + \
                         "Resources/stonix.app/Contents/MacOS/" + \
                         "stonix_resources/files/" + \
                         "U_Apple_OS_X_10-11_V1R1_STIG_Passcode_Policy.mobileconfig"
            self.secprofile = "/Applications/stonix4mac.app/Contents/" + \
                          "Resources/stonix.app/Contents/MacOS/" + \
                          "stonix_resources/files/" + \
                          "U_Apple_OS_X_10-11_V1R1_STIG_Security_and_Privacy_Policy.mobileconfig"

################################################################################################

    def report(self):
        '''
        @since: 3/9/2016
        @author: dwalker'''
        try:
            compliant1, compliant2, compliant = False, False, True
            self.pwreport = True
            self.secreport = True
            self.detailedresults = ""
            self.ch = CommandHelper(self.logger)
            cmd = ["/usr/bin/profiles", "-P"]
            if not self.ch.executeCommand(cmd):
                compliant = False
                self.detailedresults += "Unable to run profiles command\n"
            else:
                output = self.ch.getOutput()
                if output:
                    for line in output:
                        if search("^There are no configuration profiles installed", line.strip()):
                            compliant = False
                            self.detailedresults += "There are no configuration profiles installed\n"
                            break
                        elif search("mil\.disa\.STIG\.passwordpolicy\.alacarte$", line.strip()):
                            compliant1 = True
                        elif search("mil\.disa\.STIG\.Security_Privacy\.alacarte$", line.strip()):
                            compliant2 = True
            if not compliant1:
                self.pwreport = False
            if not compliant2:
                self.secreport = False
            if not self.pwreport or not self.secreport:
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
            if not self.pwci.getcurrvalue() and not self.sci.getcurrvalue():
                return
            if self.pwci.getcurrvalue() or self.sci.getcurrvalue():
                success = True
                self.detailedresults = ""
                self.iditerator = 0
                eventlist = self.statechglogger.findrulechanges(self.rulenumber)
                for event in eventlist:
                    self.statechglogger.deleteentry(event)
            if self.pwci.getcurrvalue():
                if not self.pwreport:
                    if os.path.exists(self.pwprofile):
                        cmd = ["/usr/bin/profiles", "-I", "-F", self.pwprofile]
                        if not self.ch.executeCommand(cmd):
                            success = False
                        else:
                            self.iditerator += 1
                            myid = iterate(self.iditerator, self.rulenumber)
                            cmd = ["/usr/bin/profiles", "-I", "-F", self.pwprofile]
                            event = {"eventtype": "comm",
                                     "command": cmd}
                            self.statechglogger.recordchgevent(myid, event)
                    else:
                        self.detailedresults += "You do not have the password " + \
                            "profile needed to install\n"
            if self.sci.getcurrvalue():
                if not self.secreport:
                    if os.path.exists(self.secprofile):
                        cmd = ["/usr/bin/profiles", "-I", "-F", self.secprofile]
                        if not self.ch.executeCommand(cmd):
                            success = False
                        else:
                            self.iditerator += 1
                            myid = iterate(self.iditerator, self.rulenumber)
                            cmd = ["/usr/bin/profiles", "-I", "-F", self.secprofile]
                            event = {"eventtype": "comm",
                                     "command": cmd}
                            self.statechglogger.recordchgevent(myid, event)
                    else:
                        self.detailedresults += "You do not have the password " + \
                            "profile needed to install\n"
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