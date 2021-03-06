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
Created on Aug 23, 2016

@author: Derek Walker
@change: 2017/03/30 Dave Kennel Marked as FISMA High
@change: 2017/07/17 ekkehard - make eligible for macOS High Sierra 10.13
@change: 2018/06/08 ekkehard - make eligible for macOS Mojave 10.14
@change: 2018/10/25 Breen Malmberg - added support for high sierra and mojave;
        refactored rule
@change: Derek Walker - 2/7/2019 - updated method to search for a
            different identifier for security profile on 10.13. Added
            testing paths in setvars method which are commented out. DO
            NOT DELETE THIS SECTION OF COMMENTED CODE.
@change: 2019/08/07 ekkehard - enable for macOS Catalina 10.15 only
@change: 2019/10/23 dwalker - updated for Catalina profile, removed other unecessary code
    for older os versions that don't have python3
'''

import traceback
import os
from rule import Rule
from logdispatcher import LogPriority
from stonixutilityfunctions import iterate
from localize import FISMACAT
from KVEditorStonix import KVEditorStonix


class ConfigurePasswordPolicy(Rule):
    '''Deploy Passcode Policy configuration profiles for OS X Mavericks 10.9
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
        self.rulename = "ConfigurePasswordPolicy"
        self.formatDetailedResults("initialize")
        self.sethelptext()
        self.rootrequired = True
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.10.0', 'r', '10.14.10']}}
        self.fismacat = FISMACAT
        datatype = "bool"
        key = "PWPOLICY"
        instructions = "To disable the installation of the password " + \
                       "profile set the value of PWPOLICY to False"
        default = True
        self.pwci = self.initCi(datatype, key, instructions, default)

        datatype = "bool"
        key = "SECPOLICY"
        instructions = "To disable the installation of the security " + \
                       "profile set the value of SECPOLICY to False"
        default = True
        self.sci = self.initCi(datatype, key, instructions, default)
        self.iditerator = 0
        self.setvars()

    def setvars(self):
        '''set class variables based on os version'''

        self.passprofile = ""
        self.secprofile = ""
        baseconfigpath = "/Applications/stonix4mac.app/Contents/Resources/stonix.app/Contents/MacOS/stonix_resources/files/"
        if self.fismacat == "high":
            self.passprofile = baseconfigpath + "stonix4macPasscodeConfigurationProfile-high.mobileconfig"
            self.secprofile = baseconfigpath + "stonix4macSecurity&PrivacyConfigurationProfile.mobileconfig"
        else:
            self.passprofile = baseconfigpath + "stonix4macPasscodeConfigurationProfile.mobileconfig"
            self.secprofile = baseconfigpath + "stonix4macSecuritySecurity&PrivacyConfigurationProfile.mobileconfig"

        # the following path and dictionaries are for testing on local vm's
        # without installing stonix package each time.  DO NOT DELETE
        # basetestpath = "/Users/username/stonix/src/stonix_resources/files/"
        # if self.fismacat == "high":
        #     self.passprofile = basetestpath + "stonix4macPasscodeConfigurationProfile-high.mobileconfig"
        #     self.secprofile = basetestpath + "stonix4macSecurity&PrivacyConfigurationProfile.mobileconfig"
        # else:
        #     self.passprofile = basetestpath + "stonix4macPasscodeConfigurationProfile.mobileconfig"
        #     self.secprofile = basetestpath + "stonix4macSecurity&PrivacyConfigurationProfile.mobileconfig"
        if not os.path.exists(self.passprofile):
            self.logger.log(LogPriority.DEBUG, "Could not locate appropriate password policy profile\n")
            self.passprofile = ""
        if not os.path.exists(self.secprofile):
            self.logger.log(LogPriority.DEBUG, "Could not locate appropriate privacy and security policy profile\n")
            self.secprofile = ""

    ################################################################################################

    def report(self):
        '''first item in dictionary - identifier (multiple can exist)
        first item in second nested dictionary - key identifier within
            opening braces in output
        first item in nested list is the expected value after the = in
            output (usually a number, in quotes "1"
        second item in nested list is accepted datatype of value after
            the = ("bool", "int")
        third item in nested list (if int) is whether the allowable value
            is allowed to be more or less and still be ok
            "more", "less"
        @author: Derek Walker
        '''
        try:
            self.compliant = True
            self.detailedresults = ""
            if not self.passprofile:
                self.detailedresults += "Could not locate the appropriate password policy profile for your system.\n"
                self.compliant = False
                self.formatDetailedResults("report", self.compliant, self.detailedresults)
                self.logdispatch.log(LogPriority.INFO, self.detailedresults)
                return self.compliant
            if not self.secprofile:
                self.detailedresults += "Could not determine the appropriate privacy and security policy profile for your system.\n"
                self.compliant = False
                self.formatDetailedResults("report", self.compliant, self.detailedresults)
                self.logdispatch.log(LogPriority.INFO, self.detailedresults)
                return self.compliant
            if self.fismacat == "high":
                self.pwprofiledict = {"com.apple.mobiledevice.passwordpolicy": {"allowSimple": {"val": "0",
                                                                                                "type": "bool",
                                                                                                "accept": "",
                                                                                                "result": False},
                                                                                "forcePIN": {"val": "1",
                                                                                             "type": "bool",
                                                                                             "accept": "",
                                                                                             "result": False},
                                                                                "maxFailedAttempts": {"val": "3",
                                                                                                      "type": "int",
                                                                                                      "accept": "less",
                                                                                                      "result": False},
                                                                                "maxGracePeriod": {"val": "0",
                                                                                                   "type": "int",
                                                                                                   "accept": "",
                                                                                                   "result": False},
                                                                                "maxPINAgeInDays": {"val": "60",
                                                                                                    "type": "int",
                                                                                                    "accept": "less",
                                                                                                    "result": False},
                                                                                "minComplexChars": {"val": "1",
                                                                                                    "type": "int",
                                                                                                    "accept": "more",
                                                                                                    "result": False},
                                                                                "minLength": {"val": "15",
                                                                                              "type": "int",
                                                                                              "accept": "more",
                                                                                              "result": False},
                                                                                "minutesUntilFailedLoginReset": {
                                                                                    "val": "15",
                                                                                    "type": "int",
                                                                                    "accept": "more",
                                                                                    "result": False},
                                                                                "pinHistory": {"val": "25",
                                                                                               "type": "int",
                                                                                               "accept": "more",
                                                                                               "result": False},
                                                                                "requireAlphanumeric": {"val": "1",
                                                                                                        "type": "bool",
                                                                                                        "accept": "",
                                                                                                        "result": False}}}
            else:
                self.pwprofiledict = {"com.apple.mobiledevice.passwordpolicy": {"allowSimple": {"val": "1",
                                                                                                "type": "bool",
                                                                                                "accept": "0",
                                                                                                "result": False},
                                                                                "forcePIN": {"val": "1",
                                                                                             "type": "bool",
                                                                                             "accept": "",
                                                                                             "result": False},
                                                                                "maxFailedAttempts": {"val": "5",
                                                                                                      "type": "int",
                                                                                                      "accept": "less",
                                                                                                      "result": False},
                                                                                "maxGracePeriod": {"val": "15",
                                                                                                   "type": "int",
                                                                                                   "accept": "less",
                                                                                                   "result": False},
                                                                                "maxPINAgeInDays": {"val": "180",
                                                                                                    "type": "int",
                                                                                                    "accept": "less",
                                                                                                    "result": False},
                                                                                "minComplexChars": {"val": "1",
                                                                                                    "type": "int",
                                                                                                    "accept": "more",
                                                                                                    "result": False},
                                                                                "minLength": {"val": "8",
                                                                                              "type": "int",
                                                                                              "accept": "more",
                                                                                              "result": False},
                                                                                "minutesUntilFailedLoginReset": {
                                                                                    "val": "15",
                                                                                    "type": "int",
                                                                                    "accept": "more",
                                                                                    "result": False},
                                                                                "pinHistory": {"val": "5",
                                                                                               "type": "int",
                                                                                               "accept": "more",
                                                                                               "result": False},
                                                                                "requireAlphanumeric": {"val": "1",
                                                                                                        "type": "bool",
                                                                                                        "accept": "",
                                                                                                        "result": False}}}
            self.secdict = {"com.apple.applicationaccess": {"allowAutoUnlock": {"val": "0",
                                                                                "type": "bool",
                                                                                "accept": "",
                                                                                "result": False}},
                            "com.apple.security.firewall": {"Applications": {"val": (),
                                                                             "type": "",
                                                                             "accept": "",
                                                                             "result": False},
                                                            "BlockAllIncoming": {"val": "0",
                                                                                 "type": "bool",
                                                                                 "accept": "",
                                                                                 "result": False},
                                                            "EnableFirewall": {"val": "0",
                                                                               "type": "bool",
                                                                               "accept": "",
                                                                               "result": False},
                                                            "EnableStealthMode": {"val": "0",
                                                                                  "type": "bool",
                                                                                  "accept": "",
                                                                                  "result": False}},
                            "com.apple.systempolicy.control": {"AllowIdentifiedDevelopers": {"val": "1",
                                                                                             "type": "bool",
                                                                                             "accept": "",
                                                                                             "result": False},
                                                               "EnableAssessment": {"val": "0",
                                                                                    "type": "bool",
                                                                                    "accept": "",
                                                                                    "result": False}},
                            "com.apple.screensaver": {"askForPassword": {"val": "1",
                                                                         "type": "bool",
                                                                         "accept": "",
                                                                         "result": False},
                                                      "askForPasswordDelay": {"val": "5",
                                                                              "type": "int",
                                                                              "accept": "less",
                                                                              "result": False}},
                            "com.apple.preference.security": {"dontAllowLockMessageUI": {"val": "1",
                                                                                         "type": "bool",
                                                                                         "accept": "",
                                                                                         "result": False}},
                            "com.apple.SubmitDiagInfo": {"AutoSubmit": {"val": "0",
                                                                        "type": "bool",
                                                                        "accept": "",
                                                                        "result": False}},
                            "com.apple.MCX": {"DestroyFVKeyOnStandby": {"val": "0",
                                                                        "type": "bool",
                                                                        "accept": "",
                                                                        "result": False},
                                              "dontAllowFDEDisable": {"val": "0",
                                                                      "type": "bool",
                                                                      "accept": "",
                                                                      "result": False}}}
            self.pweditor = KVEditorStonix(self.statechglogger, self.logger,
                                           "profiles", self.passprofile, "",
                                           self.pwprofiledict, "", "")
            '''Run the system_proflier command'''
            if not self.pweditor.report():
                if self.pweditor.badvalues:
                    self.detailedresults += self.pweditor.badvalues + "\n"
                self.detailedresults += "Password profile either not installed or values are incorrect\n"
                self.compliant = False

            self.seceditor = KVEditorStonix(self.statechglogger, self.logger,
                                            "profiles", self.secprofile, "",
                                            self.secdict, "", "", self.environ)
            '''Run the system_proflier command'''
            if not self.seceditor.report():
                if self.seceditor.badvalues:
                    self.detailedresults += self.seceditor.badvalues + "\n"
                self.compliant = False
                self.detailedresults += "Security and privacy profile not installed or values are incorrect\n"

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

    ###############################################################################

    def fix(self):
        '''
        Configure and install the password policy and security profiles for Mac OS X
        @author: Derek Walker
        @change: 04/19/2018 - Breen Malmberg - added doc string; cleaned up redundant code;
            added more logging; added in-line comments; removed dead-end logic paths which
            blocked correct code from running at all (ever); corrected the return variable;
            added detailedresults formatting if exiting method early due to CI not being set
        @change: 12/1/2019 - Derek Walker - cleaned up logic, updated rule to use updated version
            of KVAprofiles class.
        '''
        try:

            self.detailedresults = ""
            success = True
            if not self.pwci and not self.sci.getcurrvalue():
                self.detailedresults += "Neither configuration item was enabled\n"
                self.rulesuccess = False
                self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)
                self.logdispatch.log(LogPriority.INFO, self.detailedresults)
                return self.rulesuccess
            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)
            # if the primary rule CI is enabled, then run the fix actions for this rule
            if self.pwci.getcurrvalue():
                if not self.pweditor.report():
                    if self.pweditor.fix():
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        self.pweditor.setEventID(myid)
                        if not self.pweditor.commit():
                            success = False
                            self.detailedresults += "Unable to install " + self.passprofile + "profile\n"
                            self.logdispatch.log(LogPriority.DEBUG, "Kveditor commit failed")
                    else:
                        success = False
                        self.detailedresults += "Unable to install " + self.passprofile + "profile\n"
                        self.logdispatch.log(LogPriority.DEBUG, "Kveditor fix failed")
            else:
                success = False
                self.detailedresults += "Password CI was not enabled.\n"
            # if the primary rule CI is enabled, then run the fix actions for this rule
            if self.sci.getcurrvalue():
                if not self.seceditor.report():
                    if self.seceditor.fix():
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        self.seceditor.setEventID(myid)
                        if not self.seceditor.commit():
                            success = False
                            self.detailedresults += "Unable to install " + self.secprofile + "profile\n"
                            self.logdispatch.log(LogPriority.DEBUG, "Kveditor commit failed")
                    else:
                        success = False
                        self.detailedresults += "Unable to install " + self.secprofile + "profile\n"
                        self.logdispatch.log(LogPriority.DEBUG, "Kveditor fix failed")
                else:
                    self.detailedresults += "Password policy profile was already installed.\n"
            else:
                success = False
                self.detailedresults += "Password CI was not enabled.\n"
            self.rulesuccess = success
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                                   " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", success, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess