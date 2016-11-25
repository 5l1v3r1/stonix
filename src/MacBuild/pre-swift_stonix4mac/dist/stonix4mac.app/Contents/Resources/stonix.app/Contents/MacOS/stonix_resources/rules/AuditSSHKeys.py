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
Created on Jul 6, 2016

This class audits for passwordless ssh keys on the system.

@author: Breen Malmberg
'''

from __future__ import absolute_import
import traceback
import os
import re

from ..rule import Rule
from ..logdispatcher import LogPriority
from glob import glob
from ..CommandHelper import CommandHelper


class AuditSSHKeys(Rule):
    '''
    This class audits for password-less ssh keys on the system.

    @author: Breen Malmberg
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.environ = environ
        self.rulenumber = 62
        self.rulename = 'AuditSSHKeys'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = 'SSH can be configured to use PKI keys for authentication, commonly referred to as SSH Keys. SSH keys are a good \
authenticator and are very useful for denying brute force password guessing attacks. There is a potential weakness in \
SSH keys in that it is possible to create the private key without a password. These passwordless, unencrypted keys can \
then be used to move laterally by any user with read access to the key. To prevent this sort of exploitation all private \
keys used for SSH should have a password and be protected by file permissions that limit read access to the owner.\
*This rule does not have fix functionality and is audit-only.*'
        self.rootrequired = True
        self.guidance = ['LANL CAP', 'OpenSSH Security Best Practices']
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}

        self.localize()

    def localize(self):
        '''
        determine which OS the system is, and set
        certain variables accordingly

        @return: void
        @author: Breen Malmberg
        '''

        self.logger.log(LogPriority.DEBUG, "Running localize() ...")

        self.mac = False
        self.linux = False

        os = self.environ.getosfamily()
        if os == 'darwin':
            self.logger.log(LogPriority.DEBUG, "System OS type detected as: darwin")
            self.mac = True
        else:
            self.logger.log(LogPriority.DEBUG, "System OS type detected as: linux")
            self.linux = True

    def report(self):
        '''
        check status of private ssh keys (whether they are encrypted with passwords or not)

        @return: self.compliant
        @rtype: bool
        @author: Breen Malmberg
        '''

        searchterm = "Proc-Type:"
        searchdirs = []
        keylist = []
        keydict = {}
        self.compliant = True
        self.detailedresults = ""
        self.ch = CommandHelper(self.logger)

        try:

            self.logger.log(LogPriority.DEBUG, "Getting list of user home directories...")
            searchdirs = self.get_search_dirs()
            self.logger.log(LogPriority.DEBUG, "Getting list of ssh keys...")
            keylist = self.get_key_list(searchdirs)

            if keylist:
                self.logger.log(LogPriority.DEBUG, "Searching list of ssh keys...")
                for key in keylist:
                    keydict[key] = False
                    f = open(key, "r")
                    contentlines = f.readlines()
                    f.close()
                    for line in contentlines:
                        if re.search(searchterm, line):
                            keydict[key] = True

                for key in keydict:
                    if not keydict[key]:
                        self.compliant = False
                        self.detailedresults += "The SSH key: " + str(key) + " was made without a password!"
                if self.compliant:
                    self.detailedresults += "All ssh keys on this system are encrypted"

            else:
                self.detailedresults += "No ssh keys were found on this system."

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        return self.compliant

    def get_key_list(self, searchdirs):
        '''
        walk the ssh directory/ies and build and return a list of private keys (file names)

        @param searchdirs: list of directories to search for private ssh keys
        @return: keylist
        @rtype: list
        @author: Breen Malmberg
        '''

        keylist = []

        if not searchdirs:
            self.logger.log(LogPriority.DEBUG, "Parameter searchdirs was empty! Returning empty keylist...")
            return keylist

        try:

            self.logger.log(LogPriority.DEBUG, "Building keylist...")
            for dir in searchdirs:
                files = glob(dir + "*")
                for f in files:
                    if os.path.isfile(f):
                        fh = open(f, "r")
                        contentlines = fh.readlines()
                        fh.close()
                        for line in contentlines:
                            if re.search("BEGIN\s+\w+\s+PRIVATE KEY", line):
                                keylist.append(f)
                                self.logger.log(LogPriority.DEBUG, "Adding ssh key file: " + str(f) + " to keylist...")

            self.logger.log(LogPriority.DEBUG, "Finished building keylist")

        except Exception:
            raise
        return keylist

    def get_search_dirs(self):
        '''
        build and return a list of search directories to look for private ssh keys

        @return: searchdirs
        @rtype: list
        @author: Breen Malmberg
        '''

        searchdirs = []

        try:

            if self.mac:
                # the system is mac-based
                getuserscmd = "/usr/bin/dscl . -list /Users NFSHomeDirectory"
                self.ch.executeCommand(getuserscmd)
                retcode = self.ch.getReturnCode()
                if retcode == "0":
                    self.logger.log(LogPriority.DEBUG, "Command to get list of users' home directories ran successfully")
                    output = self.ch.getOutput()
                    self.logger.log(LogPriority.DEBUG, "Searching command output and building searchdirs list...")
                    for line in output:
                        sline = line.split()
                        if sline[1] not in ["/var/empty", "/dev/null"]:
                            if os.path.exists(sline[1] + "/.ssh/"):
                                searchdirs.append(sline[1] + "/.ssh/")
            else:
                # the system is linux-based
                # determine the start of the user id's on this system (500 or 1000)
                self.logger.log(LogPriority.DEBUG, "Setting default uidstart to 500...")
                uidstart = 500
                if os.path.exists('/etc/login.defs'):
                    self.logger.log(LogPriority.DEBUG, "login defs file exists. Getting actual uid start value...")
                    f = open('/etc/login.defs')
                    contentlines = f.readlines()
                    f.close()
                    for line in contentlines:
                        if re.search('^UID\_MIN\s+500', line, re.IGNORECASE):
                            uidstart = 500
                            self.logger.log(LogPriority.DEBUG, "Actual uid start value is 500")
                        if re.search('^UID\_MIN\s+1000', line, re.IGNORECASE):
                            uidstart = 1000
                            self.logger.log(LogPriority.DEBUG, "Actual uid start value is 1000")

                self.logger.log(LogPriority.DEBUG, "Building list of searchdirs...")
                # get list of user home directories from /etc/passwd
                f = open("/etc/passwd", "r")
                contentlines = f.readlines()
                f.close()
                for line in contentlines:
                    sline = line.split(":")
                    if len(sline) > 2:
                        if int(sline[2]) >= uidstart:
                            # build list of search directories based on home directories
                            if os.path.exists(sline[5] + "/.ssh/"):
                                searchdirs.append(sline[5] + "/.ssh/")
                                self.logger.log(LogPriority.DEBUG, "Adding directory: " + str(sline[5]) + "/.ssh/ to list of searchdirs...")

                # add the root ssh directory if it exists
                if os.path.exists("/root/.ssh/"):
                    searchdirs.append("/root/.ssh/")
                    self.logger.log(LogPriority.DEBUG, "Adding /root/.ssh/ to list of searchdirs...")

            self.logger.log(LogPriority.DEBUG, "Finished building searchdirs list")

        except Exception:
            raise
        return searchdirs