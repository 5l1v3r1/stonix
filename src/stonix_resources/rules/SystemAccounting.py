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
Created on Apr 15, 2015

System accounting is an optional process which gathers baseline system data
(CPU utilization, disk I/O, etc.) every 10 minutes, by default. The data may be
accessed with the sar command, or by reviewing the nightly report files named
/var/ log/sa/sar*. Once a normal baseline for the system has been established,
with frequent monitoring - unauthorized activity (password crackers and other
CPU-intensive jobs, and activity outside of normal usage hours) may be detected
due to departures from the normal system performance curve.

@author: Breen Malmberg
@change: 2015/09/25 eball Added Deb/Ubuntu compatibility
@change: 2015/09/29 Breen Malmberg - Added initialization of variable self.iditerator in fix()
'''

from __future__ import absolute_import

import traceback
import os
import re

from ..rule import Rule
from ..pkghelper import Pkghelper
from ..CommandHelper import CommandHelper
from ..logdispatcher import LogPriority
from ..KVEditorStonix import KVEditorStonix
from ..stonixutilityfunctions import createFile, writeFile, iterate, resetsecon


class SystemAccounting(Rule):
    '''
    classdocs
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 9
        self.rulename = 'SystemAccounting'
        self.compliant = True
        self.formatDetailedResults("initialize")
        self.mandatory = False
        self.rootrequired = True
        self.helptext = '''System accounting is an optional process which \
gathers baseline system data (CPU utilization, disk I/O, etc.) every 10 \
minutes, by default. The data may be accessed with the sar command, or by \
reviewing the nightly report files named /var/log/sa/sar*. Once a normal \
baseline for the system has been established, with frequent monitoring - \
unauthorized activity (password crackers and other CPU-intensive jobs, and \
activity outside of normal usage hours) may be detected due to departures \
from the normal system performance curve.'''
        self.guidance = ['CIS 2.4', 'cce-3992-5']
        self.applicable = {'type': 'white',
                           'family': 'linux',
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}

        # set up configuration items for this rule
        datatype = 'bool'
        key = 'SYSTEMACCOUNTING'
        instructions = 'To enable this rule, set the value of ' + \
            'SYSTEMACCOUNTING to True'
        default = False
        self.ci = self.initCi(datatype, key, instructions, default)

    def islinux(self):
        '''
        is this linux or another os type?

        @author: Breen Malmberg
        '''

        # defaults
        retval = True

        ostype = self.environ.getostype()
        if ostype == 'Mac OS X':
            retval = False

        return retval

    def setlinux(self):
        '''
        @author: Breen Malmberg
        '''

        self.setCmds()
        self.setPaths()
        self.setOpts()
        self.setObjs()

    def setmac(self):
        '''
        @author: Breen Malmberg
        '''

        self.setCmds('mac')
        self.setPaths('mac')
        self.setOpts('mac')
        self.setObjs('mac')

    def setCmds(self, ostype='linux'):
        '''
        @author: Breen Malmberg
        '''

        if ostype == 'linux':
            self.accon = '/usr/sbin/accton'
        else:
            self.accon = '/usr/sbin/accton'

    def setPaths(self, ostype='linux'):
        '''
        @author: Breen Malmberg
        '''

        self.accpath = ''
        self.pkgname = ''
        self.accbasedir = ''

        if ostype == 'linux':
            self.enableacc = '/etc/rc.conf'
            self.accbasedir = '/var/account'
            self.accpath = '/var/account/acct'
            self.pkgname = 'sysstat'
        else:
            self.enableacc = '/etc/rc.conf'
            self.accbasedir = '/var/account'
            self.accpath = '/var/account/acct'

        if not os.path.exists(self.accpath):
            self.detailedresults += '\ncould not locate accounting file: ' + \
                str(self.accpath)

    def setOpts(self, ostype='linux'):
        '''
        @author: Breen Malmberg
        '''

        if ostype == 'linux':
            self.accopt = 'accounting_enable=YES'
        else:
            self.accopt = 'accounting_enable=YES'

    def setObjs(self, ostype='linux'):
        '''
        @author: Breen Malmberg
        '''

        if ostype == 'linux':
            self.pkghelper = Pkghelper(self.logger, self.environ)
            self.cmdhelper = CommandHelper(self.logger)
        else:
            self.cmdhelper = CommandHelper(self.logger)

    def report(self):
        '''
        @author: Breen Malmberg
        '''

        # defaults
        self.compliant = True
        self.detailedresults = ''

        try:
            if self.islinux():
                self.setlinux()
                self.compliant = self.reportlinux()
            else:
                self.setmac()
                self.compliant = self.reportmac()

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def reportlinux(self):
        '''
        @author: Breen Malmberg
        '''

        # defaults
        configured = True

        try:
            if not self.pkghelper.check(self.pkgname):
                self.detailedresults += 'Accounting package not installed: ' \
                    + str(self.pkgname) + '\n'
                return False
            if self.pkghelper.determineMgr() == "apt-get":
                sysstat = "/etc/default/sysstat"
                if os.path.exists(sysstat):
                    tmppath = sysstat + ".tmp"
                    data = {"ENABLED": "true"}
                    editor = KVEditorStonix(self.statechglogger, self.logger,
                                            "conf", sysstat, tmppath, data,
                                            "present", "closedeq")
                    if not editor.report():
                        self.detailedresults += "Accounting configuration " + \
                            "file has incorrect settings: " + sysstat + "\n"
                        return False
            else:
                if not os.path.exists(self.enableacc):
                    configured = False
                    self.detailedresults += 'Accounting configuration file ' + \
                        'not found: ' + str(self.enableacc) + '\n'
                else:
                    contentlines = self.getFileContents(self.enableacc)

                    if self.accopt + '\n' not in contentlines:
                        configured = False
                        self.detailedresults += 'Accounting not enabled. ' + \
                            'missing directive: ' + str(self.accopt) + '\n'

                if not os.path.exists(self.accpath):
                    configured = False
                    self.detailedresults += 'Accounting file not found: ' + \
                        str(self.accpath) + '\n'

        except Exception:
            raise
        return configured

    def reportmac(self):
        '''
        @author: Breen Malmberg
        '''

        configured = True

        try:
            if not os.path.exists(self.accpath):
                configured = False
                self.detailedresults += 'Accounting file not found: ' + \
                    str(self.accpath) + '\n'

            if not os.path.exists(self.enableacc):
                configured = False
                self.detailedresults += 'Accounting configuration file ' + \
                    'not found: ' + str(self.enableacc) + '\n'

            else:
                contentlines = self.getFileContents(self.enableacc)

                if self.accopt + '\n' not in contentlines:
                    configured = False
                    self.detailedresults += 'Accounting not enabled. missing ' + \
                        'directive: ' + str(self.accopt) + '\n'

        except Exception:
            raise
        return configured

    def fix(self):
        '''
        @author: Breen Malmberg
        '''
        # defaults
        self.detailedresults = ''
        success = True
        self.iditerator = 0
        try:
            if self.ci.getcurrvalue():
                if self.islinux():
                    success = self.fixlinux()
                else:
                    success = self.fixmac()
            else:
                self.detailedresults += 'Configuration item ' + \
                    'SYSTEMACCOUNTING was not enabled, so nothing was done\n'

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", success,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return success

    def fixlinux(self):
        '''
        @author: Breen Malmberg
        '''

        success = True
        found = False

        try:
            if not self.pkghelper.install(self.pkgname):
                success = False
                self.detailedresults += 'Unable to install package: ' + \
                    self.pkgname + '\n'
            if self.pkghelper.determineMgr() == "apt-get":
                sysstat = "/etc/default/sysstat"
                tmppath = sysstat + ".tmp"
                if os.path.exists(sysstat):
                    data = {"ENABLED": "true"}
                    editor = KVEditorStonix(self.statechglogger, self.logger,
                                            "conf", sysstat, tmppath, data,
                                            "present", "closedeq")
                    if not editor.report():
                        if editor.fixables:
                            if editor.fix():
                                if not editor.commit():
                                    success = False
                                    self.detailedresults += "KVEditor " + \
                                        "failed to commit fixes\n"
                            else:
                                success = False
                                self.detailedresults += "KVEditor fix failed\n"
                else:
                    if createFile(sysstat, self.logger):
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        event = {"eventtype": "creation", "filepath": sysstat}
                        self.statechglogger.recordchgevent(myid, event)
                    else:
                        success = False
                        self.detailedresults += "Failed to create file: " + \
                            sysstat + "\n"

                    if writeFile(tmppath, "ENABLED=true", self.logger):
                        os.rename(tmppath, sysstat)
                        resetsecon(sysstat)
                    else:
                        success = False
                        self.detailedresults += "Failed to write settings " + \
                            "to file: " + sysstat + "\n"
            else:
                if not os.path.exists(self.accbasedir):
                    os.makedirs(self.accbasedir, 0755)
                if not os.path.exists(self.accpath):
                    f = open(self.accpath, 'w')
                    f.write('')
                    f.close()
                if not os.path.exists(self.enableacc):
                    f = open(self.enableacc, 'w')
                    f.write('')
                    f.close()

                contentlines = self.getFileContents(self.enableacc)

                if contentlines:
                    for line in contentlines:
                        if re.search('^accounting_enable=', line):
                            contentlines = [c.replace(line, self.accopt + '\n')
                                            for c in contentlines]
                            found = True

                if not found:
                    contentlines.append(self.accopt + '\n')

                f = open(self.enableacc, 'w')
                f.writelines(contentlines)
                f.close()

                cmd = self.accon + ' ' + self.accpath
                self.cmdhelper.executeCommand(cmd)
                if self.cmdhelper.getErrorString():
                    success = False
                    self.detailedresults += 'Execution of "' + cmd + '' + \
                        '" failed with error: ' + \
                        self.cmdhelper.getErrorString() + '\n'

        except Exception:
            raise
        return success

    def fixmac(self):
        '''
        @author: Breen Malmberg
        '''

        success = True
        found = False

        try:
            if not os.path.exists(self.accbasedir):
                os.makedirs(self.accbasedir, 0755)
            if not os.path.exists(self.accpath):
                f = open(self.accpath, 'w')
                f.write('')
                f.close()
            if not os.path.exists(self.enableacc):
                f = open(self.enableacc, 'w')
                f.write('')
                f.close()

            contentlines = self.getFileContents(self.enableacc)

            if contentlines:
                for line in contentlines:
                    if re.search('^accounting_enable=', line):
                        contentlines = [c.replace(line, self.accopt + '\n')
                                        for c in contentlines]
                        found = True

            if not found:
                contentlines.append(self.accopt + '\n')

            f = open(self.enableacc, 'w')
            f.writelines(contentlines)
            f.close()

            cmd = self.accon + ' ' + self.accpath
            self.cmdhelper.executeCommand(cmd)
            if self.cmdhelper.getErrorString():
                success = False
                self.detailedresults += 'Execution of "' + cmd + '" failed ' + \
                    'with error:\n' + self.cmdhelper.getErrorString()

        except Exception:
            raise
        return success

    def getFileContents(self, filepath):
        '''
        @author: Breen Malmberg
        '''

        contentlines = []

        try:

            f = open(filepath, 'r')
            contentlines = f.readlines()
            f.close()

        except IOError:
            self.detailedresults += 'Could not find specified filepath: ' + \
                str(filepath) + ': Returning empty list\n'
        return contentlines
