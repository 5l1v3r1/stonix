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
Created on Mar 12, 2013

@author: dwalker
@change: 02/16/2014 ekkehard Implemented self.detailedresults flow
@change: 02/16/2014 ekkehard Implemented isapplicable
@change: 04/18/2014 ekkehard ci updates
@change: 2015/04/17 dkennel updated for new isApplicable
@change: 2015/09/09 eball Improved feedback
@change: 2016/06/29 eball Fixed Mac path, added timeout as a CI
@change: 2017/07/17 ekkehard - make eligible for macOS High Sierra 10.13
@change: 2017/10/23 rsn - removed unused service helper
@change: 2017/11/13 ekkehard - make eligible for OS X El Capitan 10.11+
@change: 2018/06/08 ekkehard - make eligible for macOS Mojave 10.14
@change: 2019/03/12 ekkehard - make eligible for macOS Sierra 10.12+
@change: 2019/08/07 ekkehard - enable for macOS Catalina 10.15 only
'''

from stonixutilityfunctions import iterate, checkPerms, setPerms, resetsecon
from stonixutilityfunctions import createFile
from rule import Rule
from logdispatcher import LogPriority
from KVEditorStonix import KVEditorStonix
from pkghelper import Pkghelper
import traceback
import os
import re


class SSHTimeout(Rule):
    '''This rule will configure the ssh timeout period for
    ssh sessions, if ssh is installed.
    
    @author: dwalker


    '''

    def __init__(self, config, environ, logger, statechglogger):
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rootrequired = True
        self.rulenumber = 127
        self.rulename = 'SSHTimeout'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.sethelptext()
        self.boolCi = self.initCi("bool",
                                  "SSHTIMEOUTON",
                                  "To disable this rule set the value " +
                                  "of SSHTIMEOUTON to False",
                                  True)
        self.intCi = self.initCi("int", "SSHTIMEOUT",
                                 "Set your preferred timeout value here, " +
                                 "in seconds. Default is 900 (15 minutes).",
                                 900)
        self.guidance = ['NSA 3.5.2.3']
        self.iditerator = 0
        self.editor = ""
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.15', 'r', '10.15.10']}}
        self.ph = Pkghelper(self.logger, self.environ)

    def report(self):
        '''SSHTimeout.report(): produce a report on whether or not a valid
        time for timing out of ssh is set.
        @author: D.Walker


        '''

        try:
            self.detailedresults = ""
            compliant = True
            results = ""
            timeout = self.intCi.getcurrvalue()
            if self.environ.getostype() == "Mac OS X":
                self.path = '/private/etc/ssh/sshd_config'
                self.tpath = '/private/etc/ssh/sshd_config.tmp'
            else:
                self.path = '/etc/ssh/sshd_config'
                self.tpath = '/etc/ssh/sshd_config.tmp'

                if self.ph.manager == "zypper":
                    openssh = "openssh"
                else:
                    openssh = "openssh-server"

                if not self.ph.check(openssh):
                    self.compliant = True
                    self.detailedresults += "Package " + openssh + " is not installed.\nNothing to configure."
                    self.formatDetailedResults("report", self.compliant, self.detailedresults)
                    return self.compliant

            self.ssh = {"ClientAliveInterval": str(timeout),
                        "ClientAliveCountMax": "0"}
            if os.path.exists(self.path):
                compliant = True
                kvtype = "conf"
                intent = "present"
                self.editor = KVEditorStonix(self.statechglogger, self.logger,
                                             kvtype, self.path, self.tpath,
                                             self.ssh, intent, "space")
                if not self.editor.report():
                    compliant = False
                    results += "Settings in " + self.path + " are not " + \
                        "correct\n"
                if not checkPerms(self.path, [0, 0, 0o644], self.logger):
                    compliant = False
                    results += self.path + " permissions are incorrect\n"
            else:
                compliant = False
                results += self.path + " does not exist\n"

            self.detailedresults = results
            self.compliant = compliant
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fix(self):
        '''SSHTimeout.fix(): set the correct values in /etc/ssh/sshd_config
        so that ssh sessions time out appropriately.
        @author: D.Walker


        '''

        try:
            if not self.boolCi.getcurrvalue():
                return
            debug = "inside fix method\n"
            self.logger.log(LogPriority.DEBUG, debug)
            created = False
            self.iditerator = 0
            success = True
            self.detailedresults = ""
            debug = ""
            # clear out event history so only the latest fix is recorded
            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)
            if self.environ.getostype() != "Mac OS X":
                if self.ph.manager == "zypper":
                    openssh = "openssh"
                else:
                    openssh = "openssh-server"
                if not self.ph.check(openssh):
                    debug = "openssh-server is not installed in fix\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    if self.ph.checkAvailable(openssh):
                        debug = "openssh-server is not available in fix\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        if not self.ph.install(openssh):
                            debug = "Unable to install openssh-server\n"
                            self.logger.log(LogPriority.DEBUG, debug)
                            self.rulesuccess = False
                            return
                        else:
                            cmd = self.ph.getRemove() + openssh
                            event = {"eventtype": "commandstring",
                                     "command": cmd}
                            self.iditerator += 1
                            myid = iterate(self.iditerator, self.rulenumber)
                            self.statechglogger.recordchgevent(myid, event)
                            self.detailedresults += "Installed openssh-server\n"
                            self.editor = KVEditorStonix(self.statechglogger,
                                                         self.logger, "conf",
                                                         self.path, self.tpath,
                                                         self.ssh, "present",
                                                         "space")
                            self.editor.report()
                    else:
                        debug += "openssh-server not available to install\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        self.rulesuccess = False
                        return
            if not os.path.exists(self.path):
                createFile(self.path, self.logger)
                created = True
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "creation",
                         "filepath": self.path}
                self.statechglogger.recordchgevent(myid, event)
                self.editor = KVEditorStonix(self.statechglogger, self.logger,
                                             "conf", self.path, self.tpath,
                                             self.ssh, "present", "space")
                self.editor.report()

            if os.path.exists(self.path):
                print("path exists\n")
                if not checkPerms(self.path, [0, 0, 0o644], self.logger):
                    if not created:
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        if not setPerms(self.path, [0, 0, 0o644], self.logger,
                                        self.statechglogger, myid):
                            debug += "Unable to set Permissions \
    for: " + self.editor.getPath() + "\n"
                            success = False
                    else:
                        if not setPerms(self.path, [0, 0, 0o644], self.logger):
                            success = False

                if self.editor.fixables:
                    print(("editor has fixables and they are " + str(self.editor.fixables) + "\n"))
                    if not created:
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        self.editor.setEventID(myid)
                    if self.editor.fix():
                        debug += "kveditor fix ran successfully\n"
                        if self.editor.commit():
                            debug += "kveditor commit ran successfully\n"

                            os.chown(self.path, 0, 0)
                            os.chmod(self.path, 0o644)
                            if re.search("linux", self.environ.getosfamily()):
                                resetsecon(self.path)

                        else:
                            debug += "Unable to complete kveditor commit\n"
                            success = False
                    else:
                        debug += "Unable to complete kveditor fix\n"
                        success = False
                    
                self.rulesuccess = success
            if debug:
                self.logger.log(LogPriority.DEBUG, debug)
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
