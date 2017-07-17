###############################################################################
#                                                                             #
# Copyright 2015-2017.  Los Alamos National Security, LLC. This material was  #
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
This method runs all the report methods for RuleKVEditors defined in the
dictionary

@author: ekkehard j. koch
@change: 03/25/2014 Original Implementation
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2014/12/02 ekkehard OS X Yosemite 10.10 Update
@change: 2015/04/14 dkennel updated for new isApplicable
@change: 2015/10/07 eball Help text/PEP8 cleanup
@change: 2017/07/07 ekkehard - make eligible for macOS High Sierra 10.13
'''
from __future__ import absolute_import
from ..ruleKVEditor import RuleKVEditor
from ..CommandHelper import CommandHelper
from ..ServiceHelper import ServiceHelper
from ..pkghelper import Pkghelper
from ..stonixutilityfunctions import iterate
from ..logdispatcher import LogPriority

import re
import traceback


class DisableCloudServices(RuleKVEditor):
    '''
    This method runs all the report methods for RuleKVEditors defined in the
dictionary

    @author: ekkehard j. koch
    @change: 07/23/2014 added ubuntu methods and applicability; fixed typos in
            doc strings; added class doc string; implemented pkghelper and
            iterate methods - bemalmbe
    '''

###############################################################################

    def __init__(self, config, environ, logdispatcher, statechglogger):
        RuleKVEditor.__init__(self, config, environ, logdispatcher,
                              statechglogger)

        self.rulenumber = 159
        self.rulename = 'DisableCloudServices'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = "This rule disables iCloud services on OS X or " + \
            "Unity Webapps and Lens Shopping on Ubuntu."
        self.rootrequired = True
        self.logger = self.logdispatch
        self.guidance = []
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.9', 'r', '10.13.10'],
                                  'Ubuntu': ['12.04', '+']}}
        self.ch = CommandHelper(self.logdispatch)
        self.sh = ServiceHelper(self.environ, self.logdispatch)

        # init CIs
        datatype = 'bool'
        key = 'DisableCloudServices'
        instructions = "To prevent cloud services from being disabled, " + \
            "set the value of DisableCloudServices to False."
        default = True
        self.DisableCloudServices = self.initCi(datatype, key, instructions,
                                                default)
        if self.environ.getosfamily() == 'darwin':
            self.addKVEditor("iCloudSaveNewDocumentsToDisk",
                             "defaults",
                             "NSGlobalDomain",
                             "",
                             {"NSDocumentSaveNewDocumentsToCloud":
                              ["0", "-bool no"]},
                             "present",
                             "",
                             "Save new documents to disk not to iCloud.",
                             None,
                             False,
                             {"NSDocumentSaveNewDocumentsToCloud":
                              ["1", "-bool yes"]})
        else:
            self.debianpkglist = ['unity-webapps-common',
                                  'unity-lens-shopping']

    def report(self):
        '''
        choose which report method to run based on OS archetype
        '''
        self.detailedresults = ""
        if self.environ.getosfamily() == 'darwin':
            RuleKVEditor.report(self, False)
        elif re.search('Ubuntu', self.environ.getostype()):
            retval = self.reportUbuntu()
            return retval
###############################################################################

    def reportUbuntu(self):
        '''
        if debian, check for unity-lens-shopping and unity-webapps-common
        cloud service packages
        '''

        # defaults
        self.compliant = True
        self.detailedresults = ""

        try:

            self.ph = Pkghelper(self.logdispatch, self.environ)

            for package in self.debianpkglist:
                if self.ph.check(package):
                    self.compliant = False

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
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
        '''
        choose which fix method to run, based on OS archetype
        '''
        self.detailedresults = ""
        if self.DisableCloudServices.getcurrvalue():
            if self.environ.getosfamily() == 'darwin':
                RuleKVEditor.fix(self, False)
            elif re.search('Ubuntu', self.environ.getostype()):
                self.fixUbuntu()
###############################################################################

    def fixUbuntu(self):
        '''
        if debian, disable unity-lens-shopping and unity-webapps-common
        cloud service packages, if they are installed
        '''

        # defaults
        self.iditerator = 0

        try:

            for package in self.debianpkglist:
                if self.ph.check(package):
                    self.ph.remove(package)

                    cmd = self.ph.getInstall() + package

                    event = {'eventtype': 'commandstring',
                             'command': cmd}
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)

                    self.statechglogger.recordchgevent(myid, event)

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults += "\n" + str(err) + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess
