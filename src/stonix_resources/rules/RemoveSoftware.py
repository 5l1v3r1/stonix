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

"""
Created on Apr 5, 2016

@author: Derek Walker
@change: 2016/07/06 eball Added undo events to fix
@change: 2017/10/23 rsn removed unused service helper
@change: 2018/07/31 Breen Malmberg - added doc strings for report and fix
        methods; added redhat insights software to default list of software
        to remove
"""

import traceback

from pkghelper import Pkghelper
from logdispatcher import LogPriority
from stonixutilityfunctions import iterate
from rule import Rule


class RemoveSoftware(Rule):
    """This class removes any unnecessary software installed on the system"""

    def __init__(self, config, environ, logger, statechglogger):
        """
        Constructor
        """

        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 91
        self.rulename = "RemoveSoftware"
        self.mandatory = True
        self.formatDetailedResults("initialize")
        self.sethelptext()
        self.rootrequired = True
        self.guidance = ["NSA 2.3.5.6"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'freebsd']}

        # Configuration item instantiation
        datatype1 = "bool"
        key1 = "REMOVESOFTWARE"
        instructions1 = "To disable this rule set the value of REMOVESOFTWARE TO False."
        default1 = False
        self.ci = self.initCi(datatype1, key1, instructions1, default1)

        datatype2 = "list"
        key2 = "PACKAGES"
        instructions2 = "Enter the package(s) that you wish to remove.  By " + \
            "default we already list packages that we recommend for removal."
        default2 = ["squid",
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
                   "httpd",
                   "dovecot",
                   "dovecot-imapd",
                   "dovecot-pop3d",
                   "snmpd",
                   "net-snmpd",
                   "net-snmp",
                   "ipsec-tools",
                   "irda-utils",
                   "slapd",
                   "openldap-servers",
                   "openldap2",
                   "bind9",
                   "bind9.i386",
                   "bind",
                   "dnsutils",
                   "bind-utils",
                   "redhat-access-insights",
                   "insights-client"]

        self.pkgci = self.initCi(datatype2, key2, instructions2, default2)

    def report(self):
        """
        report whether any of the packages listed in the self.pkgci ci are installed
        return False if any are installed
        return True if none of them are installed

        :returns: self.compliant
        :rtype: bool
        """

        self.detailedresults = ""
        self.compliant = True
        self.ph = Pkghelper(self.logger, self.environ)
        packages = self.pkgci.getcurrvalue()
        self.remove_packages = []

        try:

            if packages:
                for pkg in packages:
                    if self.ph.check(pkg):
                        self.remove_packages.append(pkg)
                        self.detailedresults += pkg + " is installed\n"
                        self.compliant = False

        except Exception:
            self.compliant = False
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)

        return self.compliant

    def fix(self):
        """
        remove all software packages listed in the self.pkgci list

        :returns: self.rulesuccess
        :rtype: bool
        """

        self.rulesuccess = True
        self.detailedresults = ""
        self.iditerator = 0
        enabled = self.ci.getcurrvalue()

        try:

            if not enabled:
                self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)
                return self.rulesuccess
            elif not self.remove_packages:
                self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)
                return self.rulesuccess

            # Clear out event history so only the latest fix is recorded
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)

            for pkg in self.remove_packages:
                try:
                    if self.ph.remove(pkg):
                        self.iditerator += 1
                        self.detailedresults += "\nRemoved package: " + str(pkg)
                        myid = iterate(self.iditerator, self.rulenumber)
                        event = {"eventtype": "pkghelper",
                                 "pkgname": pkg,
                                 "startstate": "installed",
                                 "endstate": "removed"}
                        self.statechglogger.recordchgevent(myid, event)
                    else:
                        self.rulesuccess = False
                        self.detailedresults += "\nFailed to remove package: " + str(pkg)
                except Exception:
                    continue

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)

        return self.rulesuccess
