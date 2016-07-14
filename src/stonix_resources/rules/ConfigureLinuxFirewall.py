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
Created on May 27, 2016

@author: dkennel

'''
from __future__ import absolute_import

import os
import traceback
import re
import shutil
import subprocess
import time

from ..ServiceHelper import ServiceHelper
from ..CommandHelper import CommandHelper
from ..rule import Rule
from ..logdispatcher import LogPriority


class ConfigureLinuxFirewall(Rule):
    '''
    The configureLinuxFirewall class attempts to audit and configure firewalls
    for Linux OS based systems. Note: there is tremendous variations in the
    approach taken by the various distributions on how to manage firewalls,
    this code should work effectively for debian, ubuntu, RHEL and close
    derivatives. Note: unlike many other rules this behaves as a binary state
    manager, the undo will set the system back to an as new state with no
    firewalls.
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.config = config
        self.environ = environ
        self.logger = logger
        self.statechglogger = statechglogger
        self.rulenumber = 92
        self.rulename = 'ConfigureLinuxFirewall'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = '''The ConfigureLinuxFirewall rule will configure \
the firewalld or iptables firewall for a Linux host in an appropriate manner \
for typical enterprise workstation usage. This will allow most client activity \
but prevent network access to most services other than SSH. \
Most workstations will leave this rule enabled but some server \
administrators may want to disable this rule or customize the firewall after \
STONIX has done the baseline configuration.
'''
        self.rootrequired = True
        self.applicable = {'type': 'white',
                           'family': ['linux']}
        self.servicehelper = ServiceHelper(self.environ, self.logger)
        self.cmdhelper = CommandHelper(self.logger)
        self.guidance = ['NIST 800-53 AC-4', 'DISA RHEL 7 STIG 2.5.7.1',
                         'DISA RHEL 7 STIG 2.5.7.1.1',
                         'DISA RHEL 7 STIG 2.5.8.1.1',
                         'DISA RHEL 7 STIG 2.5.8.1.2',
                         'DISA RHEL 7 STIG 2.5.8.1.3',
                         'DISA RHEL 7 STIG 2.5.8.2.1',
                         'DISA RHEL 7 STIG 2.5.8.2.2',
                         'DISA RHEL 7 STIG 2.5.8.2.3',
                         'DISA RHEL 7 STIG 2.5.8.2.4']
        datatype = 'bool'
        key = 'configurelinuxfirewall'
        instructions = '''To disable this rule set the value of \
CONFIGURELINUXFIREWALL to False.'''
        default = True
        self.clfci = self.initCi(datatype, key, instructions, default)
        self.isfirewalld = False
        self.isufw = False
        if os.path.exists('/bin/firewall-cmd'):
            self.isfirewalld = True
        if os.path.exists('/usr/sbin/ufw'):
            self.isufw = True
        self.iptables = "/usr/sbin/iptables"
        if not os.path.exists(self.iptables):
            self.iptables = '/sbin/iptables'
        self.ip6tables = "/usr/sbin/ip6tables"
        if not os.path.exists(self.ip6tables):
            self.ip6tables = '/sbin/ip6tables'

    def report(self):
        """
        Report on whether the firewall meets baseline expectations.

        @return: bool
        @author: D.Kennel
        """
        compliant = True
        iptablesrunning = False
        ip6tablesrunning = False
        catchall = False
        catchall6 = False
        self.detailedresults = ""
        try:
            if self.isfirewalld:
                if self.servicehelper.auditservice('firewalld.service'):
                    compliant = True
                else:
                    compliant = False
                    self.detailedresults = 'This system appears to have ' + \
                        'firewalld but it is not running as required'
            elif self.isufw:
                cmdufw = '/usr/sbin/ufw status'
                if not self.cmdhelper.executeCommand(cmdufw):
                    self.detailedresults += "Unable to run " + \
                        "ufw status command\n"
                    compliant = False
                else:
                    outputufw = self.cmdhelper.getOutputString()
                    if re.search('Status: inactive', outputufw):
                        compliant = False
                        self.detailedresults = 'This system appears to have ' + \
                            'ufw but it is not running as required'
            elif "iptables" not in self.servicehelper.listservices():
                # Debian systems do not provide a service for iptables
                cmd = [self.iptables, "-L"]
                if not self.cmdhelper.executeCommand(cmd):
                    self.detailedresults += "Unable to run " + \
                        "iptables -L command\n"
                    compliant = False
                else:
                    output = self.cmdhelper.getOutput()
                    for line in output:
                        if re.search('Chain INPUT \(policy REJECT\)|REJECT' +
                                     '\s+all\s+--\s+anywhere\s+anywhere', line):
                            catchall = True
                            break
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. ipv4 catchall rule: "
                                     + str(catchall)])
                cmd6 = [self.ip6tables, "-L"]
                if not self.cmdhelper.executeCommand(cmd6):
                    self.detailedresults += "Unable to run " + \
                        "ip6tables -L command\n"
                    compliant = False
                else:
                    output6 = self.cmdhelper.getOutput()
                    for line in output6:
                        if re.search('Chain INPUT \(policy REJECT\)|REJECT' +
                                     '\s+all\s+anywhere\s+anywhere', line):
                            catchall6 = True
                            break
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. ipv6 catchall rule: "
                                     + str(catchall6)])
                iptShellPath = "/etc/network/if-pre-up.d/iptables"
                if os.path.exists(iptShellPath):
                    scriptExists = True
                else:
                    scriptExists = False
                if not catchall:
                    self.detailedresults += 'This system appears to use ' + \
                        'iptables but the expected deny all is missing ' + \
                        'from the rules.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. Missing v4 deny all."])
                if not catchall6:
                    self.detailedresults += 'This system appears to use ' + \
                        'ip6tables but the expected deny all is missing ' + \
                        'from the rules.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. Missing v6 deny all."])
                if not scriptExists:
                    self.detailedresults += 'This system appears to use ' + \
                        'iptables but the startup script is not present\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. Missing startup " +
                                     "script"])
                if catchall and catchall6 and scriptExists:
                    compliant = True
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. Check passed."])
                else:
                    compliant = False
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "Debian type system. Check failed."])
            else:
                if self.servicehelper.auditservice('iptables.service') or \
                   self.servicehelper.auditservice('iptables'):
                    iptablesrunning = True
                self.logger.log(LogPriority.DEBUG,
                                ['ConfigureLinuxFirewall.report',
                                 "RHEL 6 type system. iptables service: " +
                                 str(iptablesrunning)])
                if self.servicehelper.auditservice('ip6tables.service') or \
                   self.servicehelper.auditservice('ip6tables'):
                    ip6tablesrunning = True
                self.logger.log(LogPriority.DEBUG,
                                ['ConfigureLinuxFirewall.report',
                                 "RHEL 6 type system. ip6tables service: " +
                                 str(ip6tablesrunning)])
                cmd = [self.iptables, "-L"]
                if not self.cmdhelper.executeCommand(cmd):
                    self.detailedresults += "Unable to run " + \
                        "iptables -L command\n"
                    compliant = False
                else:
                    output = self.cmdhelper.getOutput()
                    for line in output:
                        if re.search('Chain INPUT \(policy REJECT\)|REJECT' +
                                     '\s+all\s+--\s+anywhere\s+anywhere', line):
                            catchall = True
                            break
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. ipv4 catchall rule: "
                                     + str(catchall)])
                cmd6 = [self.ip6tables, "-L"]
                if not self.cmdhelper.executeCommand(cmd6):
                    self.detailedresults += "Unable to run " + \
                        "ip6tables -L command\n"
                    compliant = False
                else:
                    output6 = self.cmdhelper.getOutput()
                    for line in output6:
                        if re.search('Chain INPUT \(policy REJECT\)|REJECT' +
                                     '\s+all\s+anywhere\s+anywhere', line):
                            catchall6 = True
                            break
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. ipv6 catchall rule: "
                                     + str(catchall6)])
                if not iptablesrunning:
                    self.detailedresults += 'This system appears to use ' + \
                        'iptables but it is not running as required.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. IPtables not running."])
                if not ip6tablesrunning:
                    self.detailedresults += 'This system appears to use ' + \
                        'ip6tables but it is not running as required.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. IP6tables not running."])
                if not catchall:
                    self.detailedresults += 'This system appears to use ' + \
                        'iptables but the expected deny all is missing ' + \
                        'from the rules.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. Missing v4 deny all."])
                if not catchall6:
                    self.detailedresults += 'This system appears to use ' + \
                        'ip6tables but the expected deny all is missing ' + \
                        'from the rules.\n'
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. Missing v6 deny all."])
                if iptablesrunning and ip6tablesrunning and catchall and catchall6:
                    compliant = True
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. Check passed."])
                else:
                    compliant = False
                    self.logger.log(LogPriority.DEBUG,
                                    ['ConfigureLinuxFirewall.report',
                                     "RHEL 6 type system. Check failed."])
            if compliant:
                self.detailedresults = 'The firewall configuration appears ' + \
                    'to meet minimum expectations.'
                self.targetstate = 'configured'
                self.compliant = True
            else:
                self.targetstate = 'notconfigured'
                self.compliant = False

        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.detailedresults = 'ConfigureLinuxFirewall: '
            self.detailedresults = self.detailedresults + \
                traceback.format_exc()
            self.rulesuccess = False
            self.logger.log(LogPriority.ERROR,
                            self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fix(self):
        """
        Enable the firewall services and establish basic rules if needed.

        @author: D. Kennel
        """
        if self.clfci.getcurrvalue():
            self.rulesuccess = True
            try:
                if self.isfirewalld:
                    self.servicehelper.enableservice('firewalld.service')
                    self.detailedresults += "Firewall configured.\n "
                elif self.isufw:
                    ufwcmd = '/usr/sbin/ufw enable'
                    if not self.cmdhelper.executeCommand(ufwcmd):
                        self.detailedresults += "Unable to run " + \
                            "ufw enable command\n"
                        self.rulesuccess = False
                    else:
                        self.detailedresults += "Firewall configured.\n "
                elif os.path.exists('/usr/bin/system-config-firewall') or \
                     os.path.exists('/usr/bin/system-config-firewall-tui'):

                    systemconfigfirewall = '''# Configuration file for system-config-firewall

--enabled
--service=ssh
'''
                    sysconfigiptables = '''# Firewall configuration written by system-config-firewall
# Manual customization of this file is not recommended.
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
'''
                    sysconfigip6tables = '''# Firewall configuration written by system-config-firewall
# Manual customization of this file is not recommended.
*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p ipv6-icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state NEW -m udp -p udp --dport 546 -d fe80::/64 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp6-adm-prohibited
-A FORWARD -j REJECT --reject-with icmp6-adm-prohibited
COMMIT
'''
                    fwhandle = open('/etc/sysconfig/system-config-firewall',
                                    'w')
                    fwhandle.write(systemconfigfirewall)
                    fwhandle.close()
                    ipwhandle = open('/etc/sysconfig/iptables', 'w')
                    ipwhandle.write(sysconfigiptables)
                    ipwhandle.close()
                    ip6whandle = open('/etc/sysconfig/ip6tables', 'w')
                    ip6whandle.write(sysconfigip6tables)
                    ip6whandle.close()
                    self.servicehelper.enableservice('iptables')
                    self.servicehelper.enableservice('ip6tables')
                    # we restart iptables here because it doesn't respond
                    # to reload
                    proc = subprocess.Popen('/sbin/service iptables restart',
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            shell=True, close_fds=True)
                    proc = subprocess.Popen('/sbin/service ip6tables restart',
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            shell=True, close_fds=True)
                    # Sleep for a bit to let the restarts occur
                    time.sleep(3)
                    self.detailedresults += "Firewall configured.\n "
                elif os.path.exists('/sbin/iptables-restore') and \
                     os.path.exists('/sbin/ip6tables-restore'):
                    iptables = '''*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp-host-prohibited
-A FORWARD -j REJECT --reject-with icmp-host-prohibited
COMMIT
'''
                    ip6tables = '''*filter
:INPUT ACCEPT [0:0]
:FORWARD ACCEPT [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
-A INPUT -p ipv6-icmp -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -m state --state NEW -m udp -p udp --dport 546 -d fe80::/64 -j ACCEPT
-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT
-A INPUT -j REJECT --reject-with icmp6-adm-prohibited
-A FORWARD -j REJECT --reject-with icmp6-adm-prohibited
COMMIT
'''
                    proc = subprocess.Popen('/sbin/iptables-restore',
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    proc.communicate(input=iptables)
                    proc = subprocess.Popen('/sbin/ip6tables-restore',
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
                    proc.communicate(input=ip6tables)
                    iptShellScript = '#!/bin/bash\n/sbin/iptables-restore <<< "' + \
                        iptables + '"\n/sbin/ip6tables-restore <<< "' + \
                        ip6tables + '"'
                    iptShellPath = "/etc/network/if-pre-up.d/iptables"
                    iptShellHandle = open(iptShellPath, "w")
                    iptShellHandle.write(iptShellScript)
                    iptShellHandle.close()
                    os.chmod(iptShellPath, 0755)
                    self.detailedresults += "Firewall configured.\n "
                else:
                    self.detailedresults += "Unable to configure a " + \
                        "firewall for this system. The system " + \
                        "administrator should configure an iptables firewall.\n"
                    self.rulesuccess = False
            except (KeyboardInterrupt, SystemExit):
                # User initiated exit
                raise
            except Exception:
                self.rulesuccess = False
                self.detailedresults = 'ConfigureLinuxFirewall: '
                self.detailedresults = self.detailedresults + \
                    traceback.format_exc()
                self.rulesuccess = False
                self.logger.log(LogPriority.ERROR,
                                self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess

    def undo(self):
        """
        Disabling all firewalls

        @author: dkennel
        """
        self.targetstate = 'notconfigured'
        try:
            if self.isfirewalld:
                self.servicehelper.disableservice('firewalld.service')
                self.detailedresults += "Firewall disabled.\n "
            elif self.isufw:
                ufwcmd = '/usr/sbin/ufw disable'
                if not self.cmdhelper.executeCommand(ufwcmd):
                    self.detailedresults += "Unable to run " + \
                        "ufw disable command\n"
                    return False
                self.detailedresults += "Firewall configured.\n "
            elif os.path.exists('/usr/bin/system-config-firewall') or \
                 os.path.exists('/usr/bin/system-config-firewall-tui'):
                systemconfigfirewall = '''# Configuration file for system-config-firewall

--disabled
'''
                fwhandle = open('/etc/sysconfig/system-config-firewall', 'w')
                fwhandle.write(systemconfigfirewall)
                fwhandle.close()
                shutil.move('/etc/sysconfig/iptables',
                            '/etc/sysconfig/iptables.stonix.bak')
                shutil.move('/etc/sysconfig/ip6tables',
                            '/etc/sysconfig/ip6tables.stonix.bak')
                self.servicehelper.disableservice('iptables')
                self.servicehelper.disableservice('ip6tables')
            else:
                    self.detailedresults += "Unable to configure a " + \
                        "firewall for this system. Nothing to undo.\n "
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.detailedresults = 'ConfigureLinuxFirewalls: '
            self.detailedresults = self.detailedresults + \
                traceback.format_exc()
            self.rulesuccess = False
            self.logger.log(LogPriority.ERROR,
                            ['ConfigureLinuxFirewalls.undo',
                             self.detailedresults])
            return False
        self.report()
        if self.currstate == self.targetstate:
            self.detailedresults = 'ConfigureLinuxFirewalls: Changes ' + \
                'successfully reverted'
        return True
