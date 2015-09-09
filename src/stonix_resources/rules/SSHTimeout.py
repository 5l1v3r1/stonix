'''
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

Created on Mar 12, 2013

@author: dwalker
@change: 02/16/2014 ekkehard Implemented self.detailedresults flow
@change: 02/16/2014 ekkehard Implemented isapplicable
@change: 04/18/2014 ekkehard ci updates
@change: 2015/04/17 dkennel updated for new isApplicable
@change: 2015/09/09 eball Improved feedback
'''
from __future__ import absolute_import
from ..stonixutilityfunctions import iterate, checkPerms, setPerms, resetsecon
from ..stonixutilityfunctions import createFile
from ..rule import Rule
from ..logdispatcher import LogPriority
from ..KVEditorStonix import KVEditorStonix
from ..pkghelper import Pkghelper
import traceback
import os


class SSHTimeout(Rule):

###############################################################################
    def __init__(self, config, environ, logger, statechglogger):
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rootrequired = True
        self.rulenumber = 127
        self.rulename = 'SSHTimeout'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = '''SSH allows administrators to set an idle timeout \
interval. After this interval has passed, the idle user will be \
automatically logged out. '''
        self.ci = self.initCi("bool",
                              "SSHTIMEOUT",
                              "To disable this rule set the value " + \
                              "of SSHTIMEOUT to False",
                              True)
        self.guidance = ['NSA 3.5.2.3']
        self.iditerator = 0
        self.editor = ""
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}

###############################################################################

    def report(self):
        '''SSHTimeout.report(): produce a report on whether or not a valid
        time for timing out of ssh is set.
        @author: D.Walker
        '''

        try:
            compliant = True
            results = ""
            if self.environ.getostype() == "Mac OS X":
                self.path = '/private/etc/sshd_config'
                self.tpath = '/private/etc/sshd_config.tmp'
            else:
                self.path = '/etc/ssh/sshd_config'
                self.tpath = '/etc/ssh/sshd_config.tmp'

                self.ph = Pkghelper(self.logger, self.environ)
                if self.ph.manager == "zypper":
                    openssh = "openssh"
                else:
                    openssh = "openssh-server"
                if not self.ph.check(openssh):
                    compliant = False
                    results += "Package " + openssh + " is not installed\n"
            self.ssh = {"ClientAliveInterval": "900",
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
                if not checkPerms(self.path, [0, 0, 0644], self.logger):
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
###############################################################################

    def fix(self):
        '''SSHTimeout.fix(): set the correct values in /etc/ssh/sshd_config
        so that ssh sessions time out appropriately.
        @author: D.Walker
        '''

        try:
            if not self.ci.getcurrvalue():
                return
            created = False
            self.iditerator = 0
            success = True
            self.detailedresults = ""
            debug = ""

            #clear out event history so only the latest fix is recorded
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
                    if self.ph.checkAvailable(openssh):
                        if not self.ph.install(openssh):
                            debug = "Unable to install openssh-server\n"
                            self.logger.log(LogPriority.DEBUG, debug)
                            self.rulesuccess = False
                            return
                        else:
                            cmd = self.ph.getRemove() + openssh
                            event = {"eventtype": "commandstring",
                                     "command":cmd}
                            self.iditerator += 1
                            myid = iterate(self.iditerator, self.rulenumber)
                            self.statechglogger.recordchgevent(myid, event)
                            self.detailedresults += "Installed openssh-server\n"
                            self.editor = KVEditorStonix(self.statechglogger, 
                                self.logger,"conf", self.path, self.tpath, 
                                                      self.ssh, "present", "space")
                            self.editor.report()
                    else:
                        debug += "openssh-server not available to install\n"
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
                self.editor = KVEditorStonix(self.statechglogger, 
                    self.logger, "conf", self.path, self.tpath, self.ssh, 
                                                            "present", "space")
                self.editor.report()

            if os.path.exists(self.path):
                if not checkPerms(self.path, [0, 0, 420], self.logger):
                    if not created:
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        if not setPerms(self.path, [0, 0, 420], self.logger,
                                        self.statechglogger, myid):
                            debug += "Unable to set Permissions \
    for: " + self.editor.getPath() + "\n"
                            success = False
                    else:
                        if not setPerms(self.path, [0, 0, 420], self.logger):
                            success = False
                if self.editor.fixables or self.editor.removeables:
                    if not created:
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        self.editor.setEventID(myid)
                    if self.editor.fix():
                        debug += "kveditor fix ran successfully\n"
                        if self.editor.commit():
                            debug += "kveditor commit ran successfully\n"
                        else:
                            debug += "Unable to complete kveditor commit\n"
                            success = False
                    else:
                        debug += "Unable to complete kveditor fix\n"
                        success = False
                        success = False
                    os.chown(self.path, 0, 0)
                    os.chmod(self.path, 420)
                    resetsecon(self.path)
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
    