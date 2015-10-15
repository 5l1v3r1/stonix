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
This method runs all the report methods for RuleKVEditors in defined in the
dictionary

@author: ekkehard j. koch
@change: 04/21/2014 ekkehard - Original Implementation
@change: 2014/06/17 dkennel - Fixed traceback on Debian
@change: 2014/07/14 ekkehard - Fixed report to self.fh.evaluateFiles()
@change: 2015/04/14 dkennel updated for new isApplicable
@change: 2015/08/17 eball - Updated to work with Linux
@change: 2015/10/07 eball - Help text cleanup
'''
from __future__ import absolute_import
import os
import traceback
from ..ruleKVEditor import RuleKVEditor
from ..logdispatcher import LogPriority
from ..filehelper import FileHelper
from ..CommandHelper import CommandHelper
from ..pkghelper import Pkghelper
from ..ServiceHelper import ServiceHelper
from ..localize import KERB5, KRB5


class ConfigureKerberos(RuleKVEditor):
    '''
    @author: ekkehard j. koch
    '''

###############################################################################

    def __init__(self, config, environ, logdispatcher, statechglogger):
        RuleKVEditor.__init__(self, config, environ, logdispatcher,
                              statechglogger)
        self.rulenumber = 255
        self.rulename = 'ConfigureKerberos'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = "This rule configures Kerberos on your system, " + \
            "based on the settings in the localize.py file."
        self.rootrequired = True
        self.guidance = []
        self.applicable = {'type': 'white', 'family': 'linux',
                           'os': {'Mac OS X': ['10.9', 'r', '10.10.10']}}
        # This if/else statement fixes a bug in Configure Kerberos that
        # occurs on Debian systems due to the fact that Debian has no wheel
        # group by default.
        if self.environ.getosfamily() == 'darwin':
            self.files = {"krb5.conf":
                          {"path": "/etc/krb5.conf",
                           "remove": False,
                           "content": KERB5,
                           "permissions": 0644,
                           "owner": os.getuid(),
                           "group": "wheel",
                           "eventid": None},
# FIXME: Once StateChgLogger supports file deletion
#                           "eventid": str(self.rulenumber).zfill(4) + \
#                           "kerb5"},
                          "edu.mit.Kerberos":
                          {"path": "/Library/Preferences/edu.mit.Kerberos",
                           "remove": True,
                           "content": None,
                           "permissions": None,
                           "owner": None,
                           "group": None,
                           "eventid": None},
# FIXME: Once StateChgLogger supports file deletion
#                       "eventid": str(self.rulenumber).zfill(4) + \
#                       "Kerberos"},
                          "edu.mit.Kerberos.krb5kdc.launchd":
                          {"path": "/Library/Preferences/edu.mit.Kerberos.krb5kdc.launchd",
                           "remove": True,
                           "content": None,
                           "permissions": None,
                           "owner": None,
                           "group": None,
                           "eventid": None},
                          "kerb5.conf":
                          {"path": "/etc/kerb5.conf",
                           "remove": True,
                           "content": None,
                           "permissions": None,
                           "owner": None,
                           "group": None,
                           "eventid": None},
# FIXME: Once StateChgLogger supports file deletion
#                       "eventid": str(self.rulenumber).zfill(4) + \
#                       "krb5kdc"},
                          "edu.mit.Kerberos.kadmind.launchd":
                          {"path": "/Library/Preferences/edu.mit.Kerberos.kadmind.launchd",
                           "remove": True,
                           "content": None,
                           "permissions": None,
                           "owner": None,
                           "group": None,
                           "eventid": None}
    # FIXME: Once StateChgLogger supports file deletion
    #                       "eventid": str(self.rulenumber).zfill(4) + \
    #                       "kadmind"}
                          }
        else:
            self.files = {"krb5.conf":
                          {"path": "/etc/krb5.conf",
                           "remove": False,
                           "content": KRB5,
                           "permissions": 0644,
                           "owner": "root",
                           "group": "root",
                           "eventid": str(self.rulenumber).zfill(4) + "kerb5"}}
        self.ch = CommandHelper(self.logdispatch)
        self.sh = ServiceHelper(self.environ, self.logdispatch)
        self.fh = FileHelper(self.logdispatch, self.statechglogger)
        if self.environ.getosfamily() == 'linux':
                self.ph = Pkghelper(self.logdispatch, self.environ)
        self.filepathToConfigure = []
        for filelabel, fileinfo in sorted(self.files.items()):
            self.filepathToConfigure.append(fileinfo["path"])
            self.fh.addFile(filelabel,
                            fileinfo["path"],
                            fileinfo["remove"],
                            fileinfo["content"],
                            fileinfo["permissions"],
                            fileinfo["owner"],
                            fileinfo["group"],
                            fileinfo["eventid"]
                            )
        # Configuration item instantiation
        datatype = "bool"
        key = "CONFIGUREFILES"
        instructions = "When Enabled Add/Remove/Update these files: " + \
            str(self.filepathToConfigure)
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)

    def report(self):
        try:
            compliant = True
            self.detailedresults = ""
            if self.environ.getosfamily() == 'linux':
                packagesRpm = ["pam_krb5", "krb5-libs", "krb5-workstation",
                               "sssd-krb5", "sssd-krb5-common"]
                packagesDeb = ["krb5-config", "krb5-user", "libpam-krb5"]
                packagesSuse = ["pam_krb5", "sssd-krb5", "sssd-krb5-common"]
                if self.ph.determineMgr() == "apt-get":
                    self.packages = packagesDeb
                elif self.ph.determineMgr() == "zypper":
                    self.packages = packagesSuse
                else:
                    self.packages = packagesRpm
                for package in self.packages:
                    if not self.ph.check(package):
                        compliant = False
                        self.detailedresults += package + " is not installed\n"
            if not self.fh.evaluateFiles():
                compliant = False
                self.detailedresults += self.fh.getFileMessage()
            self.compliant = compliant
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

###############################################################################

    def fix(self):
        try:
            fixsuccess = True
            self.detailedresults = ""
            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)

            if self.ci.getcurrvalue():
                if self.environ.getosfamily() == 'linux':
                    for package in self.packages:
                        if not self.ph.check(package):
                            if not self.ph.install(package):
                                fixsuccess = False
                                self.detailedresults += "Installation of " + \
                                    package + " did not succeed.\n"
                if not self.fh.fixFiles():
                    fixsuccess = False
                    self.detailedresults += self.fh.getFileMessage()
            else:
                fixsuccess = False
                self.detailedresults = str(self.ci.getcurrvalue()) + \
                    " was disabled. No action was taken!"
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.rulesuccess = False
            fixsuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", fixsuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess
