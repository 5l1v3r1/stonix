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

'''
Created on May 17, 2013

Ensure that the user account databases (passwd, shadow, group, gshadow, etc)
have the correct (secure) permissions.

@author: bemalmbe
@change: 02/13/2014 ekkehard Implemented self.detailedresults flow
@change: 02/13/2014 ekkehard Implemented isapplicable
@change: 04/18/2014 ekkehard ci updates and ci fix method implementation
@change: 2015/04/17 dkennel updated for new isApplicable
@change: 2017/07/17 ekkehard - make eligible for macOS High Sierra 10.13
@change: 2017/11/13 ekkehard - make eligible for OS X El Capitan 10.11+
@change: 2018/06/08 ekkehard - make eligible for macOS Mojave 10.14
@change: 2019/03/12 ekkehard - make eligible for macOS Sierra 10.12+
@change: 2019/08/07 ekkehard - enable for macOS Catalina 10.15 only
'''


import os
import traceback

from rule import Rule
from stonixutilityfunctions import getOctalPerms
from logdispatcher import LogPriority


class VerifyAccPerms(Rule):
    '''Ensure that the user account databases (passwd, shadow, group, gshadow,
    etc) have the correct (secure) permissions.


    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.config = config
        self.environ = environ
        self.statechglogger = statechglogger
        self.logger = logger
        self.rulenumber = 24
        self.rulename = 'VerifyAccPerms'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.sethelptext()
        self.rootrequired = True
        self.compliant = False
        self.ci = self.initCi("bool",
                              "VERIFYACCPERMS",
                              "To prevent the setting of user account db " + \
                              "permissions, set the value of " + \
                              "VerifyAccPerms to False.",
                              True)
        self.guidance = ['CIS', 'NSA 2.2.3.1', 'CCE 3988-3', 'CCE 3883-6',
                         'CCE 3276-3', 'CCE 3932-1', 'CCE 4064-2',
                         'CCE 4210-1', 'CCE 3918-0', 'CCE 3566-7',
                         'CCE 3958-6']
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.15', 'r', '10.15.10']}}
        self.file644 = ['/etc/passwd', '/etc/group']
        self.file400 = ['/etc/shadow', '/etc/gshadow']
        self.fileall = ['/etc/passwd', '/etc/group', '/etc/shadow',
                        '/etc/gshadow']

###############################################################################

    def report(self):
        '''check to see if user account databases have the correct (secure)
        permissions and ownership set. self.compliant, self.detailed results
        and self.currstate properties are updated to reflect the system status.
        self.rulesuccess will be updated if the rule does not succeed.


        :returns: bool
        @author bemalmbe

        '''

        #defaults
        retval = True
        try:
            self.detailedresults = ""
            try:
                for item in self.file644:
                    if os.path.exists(item):
                        if getOctalPerms(item) != 644:
                            retval = False
                            self.detailedresults += item + " does not have " + \
                                "the correct permissions\n"
                for item in self.file400:
                    if os.path.exists(item):
                        if getOctalPerms(item) != 400:
                            retval = False
                            self.detailedresults += item + " does not have " + \
                                "the correct permissions\n"

                for item in self.fileall:
                    if os.path.exists(item):
                        owner = os.stat(item).st_uid
                        group = os.stat(item).st_gid

                        if owner != 0:
                            retval = False
                            self.detailedresults += item + " is not owned " + \
                                "by user \"root\"\n"
                        if group != 0:
                            retval = False
                            self.detailedresults += item + " is not owned " + \
                                "by group \"root\"\n"
            except(OSError):
                self.detailedresults = traceback.format_exc()
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
            if retval:
                self.compliant = True
            else:
                self.compliant = False
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
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

    def fix(self):
        '''The fix method will apply the required settings to the system.
        self.rulesuccess will be updated if the rule does not succeed.
        
        @author bemalmbe


        '''

        try:
            if self.ci.getcurrvalue():
                self.detailedresults = ""
                try:

                    for item in self.file644:
                        if os.path.exists(item):
                            os.chmod(item, 0o644)

                    for item in self.file400:
                        if os.path.exists(item):
                            os.chmod(item, 0o400)

                    for item in self.fileall:
                        if os.path.exists(item):
                            os.chown(item, 0, 0)

                except(OSError):
                    self.detailedresults = self.detailedresults + \
                    traceback.format_exc()
                    self.logger.log(LogPriority.ERROR, self.detailedresults)
            else:
                self.detailedresults = str(self.ci.getkey()) + \
                " was disabled. No action was taken."
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
            " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess
