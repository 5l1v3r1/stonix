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
Created on Feb 11, 2015

By requiring a password to unlock System Preferences, a casual user is less
likely to compromise the security of the Mac.

@author: bemalmbe
@change: 2015/04/17 dkennel updated for new isApplicable
@change: 2015/09/16 eball Refactored rule to update active authorization
                          settings rather than the typically-unused plist
'''

from __future__ import absolute_import

from ..rule import Rule
from ..stonixutilityfunctions import iterate
from ..logdispatcher import LogPriority
from ..CommandHelper import CommandHelper
from subprocess import Popen, PIPE, STDOUT
import re
import traceback


class ReqPassSysPref(Rule):
    '''
    By requiring a password to unlock System Preferences, a casual user is less
    likely to compromise the security of the Mac.
    '''

    def __init__(self, config, environ, logger, statechglogger):
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 200
        self.rulename = 'ReqPassSysPref'
        self.compliant = True
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = 'By requiring a password to unlock System ' + \
            'Preferences, a casual user is less likely to compromise the ' + \
            'security of the Mac.'
        self.rootrequired = True
        self.guidance = ['CIS 1.4.13.3']

        datatype = 'bool'
        key = 'ReqPassSysPref'
        instructions = 'To disable this rule, set the value of ' + \
            'ReqPassSysPref to False.'
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)

        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}

        self.prefslist = ["system.preferences",
                          "system.preferences.accessibility",
                          "system.preferences.accounts",
                          "system.preferences.datetime",
                          "system.preferences.energysaver",
                          "system.preferences.network",
                          "system.preferences.parental-controls",
                          "system.preferences.printing",
                          "system.preferences.security",
                          "system.preferences.security.remotepair",
                          "system.preferences.sharing",
                          "system.preferences.softwareupdate",
                          "system.preferences.startupdisk",
                          "system.preferences.timemachine"]
        self.ch = CommandHelper(self.logger)
        self.plists = {}
        self.undovals = {}

    def report(self):
        results = ""
        self.compliant = True
        plists = {}

        try:
            for pref in self.prefslist:
                if not self.ch.executeCommand(["security", "authorizationdb",
                                               "read", pref]):
                    self.compliant = False
                    error = "Report could not execute security command"
                    self.logger.log(LogPriority.ERROR, error)
                plist = self.ch.getOutput()
                # First line of output is a success/failure code from the
                # security command, which must be deleted to get a valid plist
                del plist[0]
                plist = "".join(plist)
                debug = "Checking for <key>shared</key>, <false/>"
                self.logger.log(LogPriority.DEBUG, debug)
                if not re.search(r"<key>shared</key>\s+<false/>", plist):
                    self.compliant = False
                    results += pref + " is not set to require a password\n"
                    plists[pref] = plist
                    debug = "Correct value not found in " + pref + ". " + \
                        "Adding to plists dictionary."
                    self.logger.log(LogPriority.DEBUG, debug)
            self.plists = plists
            self.detailedresults = results
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults = traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fix(self):
        if not self.ci.getcurrvalue():
            info = "ReqPassSysPref CI not enabled. Fix not run."
            self.logger.log(LogPriority.INFO, info)
            return

        results = ""
        success = True
        self.iditerator = 0

        # Delete past state change records from previous fix
        eventlist = self.statechglogger.findrulechanges(self.rulenumber)
        for event in eventlist:
            self.statechglogger.deleteentry(event)

        # The output from the "security" command needs to be written to a
        # plist. "defaults" can then be used for read and write operations to
        # particular keys, though the output is a binary file. The bin files
        # are then read back into a string and piped back into "security".
        try:
            for pref in self.plists:
                tmppath = "/tmp/" + pref + ".plist"
                debug = "Writing plist info to " + pref
                self.logger.log(LogPriority.DEBUG, debug)
                open(tmppath, "w").write(self.plists[pref])

                cmd = ["defaults", "write", tmppath, "shared", "-bool",
                       "false"]
                if not self.ch.executeCommand(cmd):
                    success = False
                    results += "Fix failed to write new value to " + tmppath \
                        + "\n"
                cmd = ["defaults", "read", tmppath]
                if not self.ch.executeCommand(cmd):
                    success = False
                    results += "Fix could not read " + tmppath + "\n"
                else:
                    plistContents = self.ch.getOutputString()
                    p = Popen(["security", "authorizationdb", "write", pref],
                              stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                    secOut = p.communicate(plistContents)[0]
                    debug = "Popen result for " + pref + ": " + secOut
                    self.logger.log(LogPriority.DEBUG, debug)
                if not re.search("YES", secOut):
                    success = False
                    results += "'security authorizationdb write' command " + \
                        "was not successful\n"
                else:
                    # Write was successful; make state change event
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    event = {"eventtype": "applesec", "pref": pref}
                    self.statechglogger.recordchgevent(myid, event)
            self.rulesuccess = success
            self.detailedresults = results
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults = traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", success,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return success

    def undo(self):
        '''
        Due to the complicated (yet single-purpose) nature of this rule, a
        custom undo function has been implemented.
        @author: Eric Ball
        '''
        try:
            self.detailedresults = ""
            results = ""
            success = True
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            if not eventlist:
                self.formatDetailedResults("undo", None, self.detailedresults)
                self.logdispatch.log(LogPriority.INFO, self.detailedresults)
                return success
            for entry in eventlist:
                try:
                    event = self.statechglogger.getchgevent(entry)
                    # The entire process must be done in reverse. Get the info
                    # from "security", write to a plist, manipulate with
                    # "defaults", re-write to a string, then pipe back into
                    # "security".
                    if event["eventtype"] == "applesec":
                        pref = event["pref"]
                        if not self.ch.executeCommand(["security",
                                                       "authorizationdb",
                                                       "read", pref]):
                            success = False
                            error = "Undo could not execute security command"
                            self.logger.log(LogPriority.ERROR, error)
                        plist = self.ch.getOutput()
                        del plist[0]
                        plist = "".join(plist)
                        tmppath = "/tmp/" + pref + ".undo.plist"
                        open(tmppath, "w").write(plist)
                        cmd = ["defaults", "write", tmppath, "shared", "-bool",
                               "true"]
                        if not self.ch.executeCommand(cmd):
                            success = False
                            results += "Undo failed to write new value to " + \
                                tmppath + "\n"
                        cmd = ["defaults", "read", tmppath]
                        if not self.ch.executeCommand(cmd):
                            success = False
                            results += "Undo could not read " + tmppath + "\n"
                        else:
                            plistContents = self.ch.getOutputString()
                            p = Popen(["security", "authorizationdb",
                                       "write", pref],
                                      stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                            secOut = p.communicate(plistContents)[0]
                            debug = "Popen result for " + pref + ": " + secOut
                            self.logger.log(LogPriority.DEBUG, debug)
                        if not re.search("YES", secOut):
                            success = False
                            results += "'security authorizationdb write' " + \
                                "command was not successful\n"
                except(IndexError, KeyError):
                    self.detailedresults = "EventID " + entry + " not found"
                    self.logdispatch.log(LogPriority.DEBUG,
                                         self.detailedresults)
            self.detailedresults = results
        except(KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            success = False
            self.detailedresults = traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, [self.rulename + ".undo",
                                 self.detailedresults])
        self.formatDetailedResults("undo", success, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return success
