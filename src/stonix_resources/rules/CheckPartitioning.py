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
Created on Oct 10, 2012
This class checks the system partitions to see if best partitioning practices
have been followed. The class is audit only.
@author: dkennel
@change: 02/12/2014 ekkehard Implemented self.detailedresults flow
@change: 02/12/2014 ekkehard Implemented isapplicable
@change: 2015/04/14 dkennel updated to use new isApplicable
@change: 2015/10/07 eball Help text cleanup
'''

from __future__ import absolute_import
import re
import traceback

from ..rule import Rule
from ..logdispatcher import LogPriority


class CheckPartitioning(Rule):
    '''
    This class checks the system partitions to see if best partitioning
    practices have been followed. The class is audit only.This class inherits
    the base Rule class, which in turn inherits observable.
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
        self.rulenumber = 1
        self.rulename = 'CheckPartitioning'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = '''The check for partitioning is an audit only rule \
that will not change system settings. Best *NIX partitioning practices \
recommend that the following areas of the filesystem, if present, be placed \
on their own partitions: /home, /tmp, ,/var, /var/tmp, /var/log, \
/var/log/audit.'''
        self.rootrequired = False
        self.guidance = ['CCE 14161-4', 'CCE 14777-7', 'CCE 14011-1',
                         'CCE 14171-3', 'CCE 14559-9']
        self.applicable = {'type': 'black',
                           'family': ['darwin']}
        self.hasrunalready = False

    def report(self):
        '''CheckPartitioning.report(): produce a report on whether or not the
        systems partitioning appears to follow best practices.

        @author: D. Kennel
        '''
        if self.hasrunalready:
            return True
        tempcompliant = False
        varcompliant = False
        varlogcompliant = False
        varlogauditcomp = False
        vartmpcomp = False
        homecomp = False
        results = 'The following filesystems should be on their own partitions:'
        fstabfile = '/etc/fstab'
        fsnodeindex = 1
        if self.environ.getosfamily() == 'solaris':
            fstabfile = '/etc/vfstab'
            fsnodeindex = 2
        try:
            fstab = open(fstabfile, 'r')
            fstabdata = fstab.readlines()
            for line in fstabdata:
                line = line.split()
                self.logger.log(LogPriority.DEBUG,
                                'Processing: ' + str(line))
                if len(line) > 0 and not re.search('^#', line[0]):
                    try:
                        # dev = line[0]
                        fsnode = line[fsnodeindex]
                        # fstype = line[2]
                        # opts = line[4]
                        # dump1 = line[5]
                        # dump2 = line[6]
                    except (IndexError):
                        continue
                    if re.search('^/tmp', fsnode):
                        tempcompliant = True
                    if re.search('^/var$', fsnode):
                        varcompliant = True
                    if re.search('^/var/log$', fsnode):
                        varlogcompliant = True
                    if re.search('^/var/log/audit$', fsnode):
                        varlogauditcomp = True
                    if re.search('^/var/tmp$', fsnode):
                        vartmpcomp = True
                    if re.search('^/home$|^/export/home$', fsnode):
                        homecomp = True
            if not tempcompliant:
                results = results + ' /tmp'
            if not varcompliant:
                results = results + ' /var'
            if not varlogcompliant:
                results = results + ' /var/log'
            if not varlogauditcomp:
                results = results + ' /var/log/audit'
            if not vartmpcomp:
                results = results + ' /var/tmp'
            if not homecomp:
                results = results + ' /home or /export/home'
            if tempcompliant and varcompliant and varlogcompliant and \
            varlogauditcomp and vartmpcomp and homecomp:
                self.compliant = True
                self.detailedresults = 'Filesystem partitioning is good'
                return True
            else:
                self.detailedresults = results
            self.hasrunalready = True
            self.rulesuccess = True
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.detailedresults = self.detailedresults + \
            traceback.format_exc()
            self.rulesuccess = False
            self.logger.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant
