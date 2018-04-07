###############################################################################
#                                                                             #
# Copyright 2015-2018.  Los Alamos National Security, LLC. This material was  #
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
Created on Mar 27, 2018

The NoDirectRootLogin rule prevents users from logging into root directly
through virtual console or tty connections. Users can still access root
through non-tty connections or by escalating privileges using sudo.

@author: bgonz12
'''

from __future__ import absolute_import
import os
import re
import traceback

from ..rule import Rule
from ..KVEditorStonix import KVEditorStonix
from ..logdispatcher import LogPriority
from ..CommandHelper import CommandHelper
from ..stonixutilityfunctions import createFile

class NoDirectRootLogin(Rule):
    '''
    @author bgonz12
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''

        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 85
        self.rulename = 'NoDirectRootLogin'
        self.formatDetailedResults("initialize")
        self.compliant = False
        self.mandatory = True
        self.sethelptext()
        self.rootrequired = True
        self.guidance = ["CCE-RHEL7-CCE-TBD 2.4.1.1.7"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd']}

        # Configuration item instantiation
        datatype = "bool"
        key = "NODIRECTROOTLOGIN"
        instructions = "To disable this rule, set the value of " + \
                       "NODIRECTROOTLOGIN to false."
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)
        
        self.ch = CommandHelper(self.logger)
        self.securettypath = "/etc/securetty"

    def report(self):
        '''
        The report method examines the current configuration and determines
        whether or not it is correct. If the config is correct then the
        self.compliant, self.detailedresults and self.currstate properties are
        updated to reflect the system status. self.rulesuccess will be updated
        if the rule does not succeed.

        @return: self.compliant
        @rtype: bool
        @author bgonz12
        '''
        try:
            compliant = True
            self.detailedresults = ""
            
            if not os.path.exists(self.securettypath):
                compliant = False
                self.detailedresults += self.securettypath + " is missing\n"
            else:
                if os.stat(self.securettypath).st_size != 0:
                    compliant = False
                    self.detailedresults += self.securettypath + " should be empty\n"
            self.compliant = compliant
            
        except (OSError):
            self.detailedresults = traceback.format_exc()
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fix(self):
        '''
        The report method examines the current configuration and determines
        whether or not it is correct. If the config is correct then the
        self.compliant, self.detailedresults and self.currstate properties are
        updated to reflect the system status. self.rulesuccess will be updated
        if the rule does not succeed.

        @return: self.rulesuccess
        @rtype: bool
        @author bgonz12
        '''
        try:
            self.detailedresults = ""
            if not self.ci.getcurrvalue():
                return
            success = True

            if not os.path.exists(self.securettypath):
                if not createFile(self.securettypath, self.logger):
                    success = False
                    self.detailedresults += "Unable to create " + \
                                            self.securettypath + "\n"
            
            if os.stat(self.securettypath).st_size != 0:
                cmd = "echo -n > " + self.securettypath
                if not self.ch.executeCommand(cmd):
                    success = False
                    self.detailedresults += "Unable to write to " + \
                                            self.securettypath + "\n"

            self.rulesuccess = success
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess
