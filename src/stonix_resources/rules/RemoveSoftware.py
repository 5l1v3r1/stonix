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
Created on Apr 5, 2016

@author: dwalker
'''
from __future__ import absolute_import
from ..pkghelper import Pkghelper
from ..logdispatcher import LogPriority
from ..ServiceHelper import ServiceHelper
from ..rule import Rule
import traceback

class RemoveSoftware(Rule):
    '''
    This class removes any unecessary software installed on the system
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 91
        self.rulename = "RemoveSoftware"
        self.mandatory = True
        self.helptext = "The RemoveSoftware rule removes any unecessary " + \
            "software installed on the system.\n" + \
            "****WARNING*****\n" + \
            "This rule is optional for a reason.  This program removes " + \
            "programs that may or may not be running during removal.  " + \
            "This can cause adverse effects during run time for your " + \
            "operating system.  Full knowledge and risk assessment is " + \
            "assumed when running this rule.\n" + \
            "*****************"   
        self.rootrequired = True
        self.detailedresults = "RemoveSoftware has not yet been run."
        self.guidance = ["NSA 2.3.5.6"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'freebsd']}
        self.ph = Pkghelper(self.logger, self.environ)
        self.sh = ServiceHelper(self.environ, self.logger)
        # Configuration item instantiation
        datatype = "bool"
        key = "REMOVESOFTWARE"
        instructions = "To disable this rule set the value of " + \
            "REMOVESOFTWARE TO False."
        default = False
        self.ci = self.initCi(datatype, key, instructions, default)
        
        datatype = "list"
        key = "PACKAGES"
        instructions = "Enter the package(s) that you wish to remove.  By " + \
            "default we already list packages that we recommend for removal."
        default = ["squid",
                   "telnet-server",
                   "rsh-server",
                   "rsh",
                   "rsh-client",
                   "talk",
                   "talk-server",
                   "talkd",
                   "libpam-ccreds",
                   "pam_ccreds",
                   "tftp-server",
                   "tftp",
                   "tftpd",
                   "udhcpd",
                   "dhcpd",
                   "dhcp",
                   "dhcp-server",
                   "yast2-dhcp-server",
                   "vsftpd",
                   "httpd"
                   "dovecot",
                   "dovecot-imapd",
                   "dovecot-pop3d",
                   "snmpd",
                   "net-snmpd",
                   "net-snmp",
                   "ipsec-tools",
                   "irda-utils",
                   "slapd",
                   "openldap-servers"
                   "openldap2"]
#         if self.ph.manager == "apt-get":
#             default = ["squid",
#                        "rsh-server",
#                        "rsh-client",
#                        "talk",
#                        "talkd",
#                        "libpam-ccreds",
#                        "tftp",
#                        "tftpd",
#                        "udhcpd",
#                        "vsftpd",
#                        "dovecot-imapd",
#                        "dovecot-pop3d",
#                        "snmpd",
#                        "ipsec-tools",
#                        "irda-utils",
#                        "slapd"]
#         elif self.ph.manager == "yum":
#             default = ["squid",
#                        "telnet-server",
#                        "rsh",
#                        "rsh-server",
#                        "talk",
#                        "talk-server",
#                        "pam_ccreds",
#                        "tftp-server",
#                        "dhcpd",
#                        "dhcp",
#                        "vsftpd",
#                        "httpd",
#                        "dovecot",
#                        "net-snmpd",
#                        "net-snmp",
#                        "ipsec-tools",
#                        "irda-utils",
#                        "openldap-servers"]
#         elif self.ph.manager == "zypper":
#             default =["squid",
#                       "telnet-server",
#                       "rsh",
#                       "rsh-server",
#                       "talk",
#                       "talk-server",
#                       "pam_ccreds",
#                       "yast2-tftp-server",
#                       "dhcp-server",
#                       "yast2-dhcp-server",
#                       "vsftpd",
#                       "httpd",
#                       "dovecot",
#                       "net-snmp",
#                       "ipsec-tools",
#                       "irda",
#                       "openldap2"]
        self.pkgci = self.initCi(datatype, key, instructions, default)

    def report(self):
        try:
            compliant = True
            if self.pkgci.getcurrvalue():
                for pkg in self.pkgci.getcurrvalue():
                    if self.ph.check(pkg):
                        self.detailedresults += pkg + " is installed\n"
                        compliant = False
            self.compliant = compliant
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant
    
    def fix(self):
        try:
            success = True
            self.detailedresults = ""
            if not self.ci.getcurrvalue():
                return
            elif not self.pkgci.getcurrvalue():
                return
            # Clear out event history so only the latest fix is recorded
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)
            for pkg in self.pkgci.getcurrvalue():
                if self.ph.check(pkg):
                    try:
                        if not self.ph.remove(pkg):
                            success = False
                    except Exception:
                        continue
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