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
Created on Nov 1, 2012
This is a rule for Verifying and/or setting the state of the LoginWindow.

@operating system: Mac
@author: Roy Nielsen
@change: 02/13/2014 ekkehard Implemented self.detailedresults flow
@change: 02/13/2014 ekkehard Implemented isapplicable
@change: 2015/04/14 dkennel updated for new stype isApplicable
'''
from __future__ import absolute_import

# The period was making python complain. Adding the correct paths to PyDev
# made this the working scenario.
from ..ruleKVEditor import RuleKVEditor
from ..stonixutilityfunctions import *


class ConfigureLoginWindow(RuleKVEditor):
    """
    defaults read /Library/Preferences/com.apple.loginwindow SHOWFULLNAME
    """
    def __init__(self, config, environ, logdispatcher, statechglogger):
        '''
        Constructor
        '''
        RuleKVEditor.__init__(self, config, environ, logdispatcher,
                              statechglogger)
        self.rulenumber = 170
        self.rulename = 'ConfigureLoginWindow'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = "This rule sets the login window to display the " + \
                        "names of the accounts on the computer may make " + \
                        "breaking in easier. Force the user to enter a " +\
                        "login name and password to log in."
        self.rootrequired = True
        self.guidance = ['CCE-28310-1']
        self.applicable = {'type': 'white',
                           'os': {'Mac OS X': ['10.9', 'r', '10.10.10']}}
        self.addKVEditor("LoginNamePassword",
                         "defaults",
                         "/Library/Preferences/com.apple.loginwindow",
                         "",
                         {"SHOWFULLNAME": ["1", "-bool yes"]},
                         "present",
                         "",
                         "Forces the user to enter a username and " + \
                         "password at the login window when enabled.",
                         None,
                         False,
                         {"SHOWFULLNAME": ["0", "-bool no"]})
        self.addKVEditor("DisableConsoleAccess",
                         "defaults",
                         "/Library/Preferences/com.apple.loginwindow",
                         "",
                         {"DisableConsoleAccess": ["1", "-bool yes"]},
                         "present",
                         "",
                         'If console login is enabled, the user can type ' + \
                         '">console" for the user name to get a console ' + \
                         'login.',
                         None,
                         False,
                         {"DisableConsoleAccess": ["0", "-bool no"]})
