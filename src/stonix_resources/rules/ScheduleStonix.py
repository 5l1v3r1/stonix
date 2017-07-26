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
Created on Dec 12, 2013

Schedule Stonix to run randomly throughout the week and once in a user context
per day

@author: Breen Malmberg
@change: 2014/02/16 ekkehard Implemented self.detailedresults flow
@change: 2014/02/16 ekkehard Implemented isapplicable
@change: 2014/04/30 dkennel Corrected bug where crons were created without -c
@change: 2014/04/30 dkennel Added newline to crontab entries to prevent damage
@change: 2014/04/30 dkennel Corrected overly greedy regexes
@change: 2014/09/02 ekkehard self.rootrequired = True & OS X 10.10 compliant
@change: 2015/04/17 dkennel updated for new isApplicable
@change: 2015/10/08 eball Help text cleanup
@change: 2017/01/31 Breen Malmberg removed superfluous logging entries (now contained
         within ServiceHelper and SHlaunchd)
'''

from __future__ import absolute_import

from ..rule import Rule
from ..logdispatcher import LogPriority
from ..stonixutilityfunctions import readFile
from ..ServiceHelper import ServiceHelper
from ..pkghelper import Pkghelper

import random
import os
import re
import pwd
import traceback


class ScheduleStonix(Rule):
    '''
    Schedule Stonix to run randomly throughout the week and once in a user
    context

    @author: bemalmbe
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''

        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 268
        self.rulename = 'ScheduleStonix'
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.rootrequired = True
        self.helptext = "Schedule a random time for STONIX to run in admin/" + \
            "root context once per week, and in user context once per day. NOTE: THIS RULE CANNOT BE REVERTED/UNDONE."
        self.guidance = ['']
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', '+']}}
        self.svchelper = ServiceHelper(self.environ, self.logger)

        # possible locations where the root cron tab may be located
        # (system-dependent)
        self.cronfilelocations = ['/var/spool/cron/root',
                                  '/usr/lib/cron/tabs/root',
                                  '/var/cron/tabs/root',
                                  '/var/spool/cron/crontabs/root']

        # init cronfilelocation to blank
        self.cronfilelocation = ''

        # find correct location out of possible locations
        for location in self.cronfilelocations:
            if os.path.exists(location):
                self.cronfilelocation = location

        # if all else fails: etc/crontab
        if self.cronfilelocation == '':
            self.cronfilelocation = '/etc/crontab'

        # get the stonix executable path
        self.stonixpath = self.environ.get_script_path()

        self.userlist = []

        for p in pwd.getpwall():
            if re.search('^/home/', p[5]) or re.search('^/Users/', p[5]):
                self.userlist.append(p[0].strip())

        # this causes a problem in detection of correct system configuration
        # because the numbers generated by this change each time it is run and
        # are then compared with the existing numbers in the file contents

        # generate random weekly time
        randday = random.randrange(1, 7)
        randhour = random.randrange(1, 23)
        randminute = random.randrange(1, 59)
        randhourfix = random.randrange(18, 23)

        # define the weekly report plist content
        self.stonixplistreport = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>gov.lanl.stonix.report</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/stonix4mac.app/Contents/Resources/stonix.app/Contents/MacOS/stonix</string>
        <string>-c</string>
        <string>-r</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key>
        <integer>''' + str(randday) + '''</integer>
        <key>Hour</key>
        <integer>''' + str(randhour) + '''</integer>
        <key>Minute</key>
        <integer>''' + str(randminute) + '''</integer>
    </dict>
</dict>
</plist>'''

        # define the weekly fix plist content
        self.stonixplistfix = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>gov.lanl.stonix.fix</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/stonix4mac.app/Contents/Resources/stonix.app/Contents/MacOS/stonix</string>
        <string>-c</string>
        <string>-f</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Day</key>
        <integer>''' + str(randday) + '''</integer>
        <key>Hour</key>
        <integer>''' + str(randhourfix) + '''</integer>
        <key>Minute</key>
        <integer>''' + str(randminute) + '''</integer>
    </dict>
</dict>
</plist>'''

        # define the once-daily user context plist content
        self.stonixplistuser = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>gov.lanl.stonix.user</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/stonix4mac.app/Contents/Resources/stonix.app/Contents/MacOS/stonix</string>
        <string>-c</string>
        <string>-f</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>''' + str(randhourfix) + '''</integer>
        <key>Minute</key>
        <integer>''' + str(randminute) + '''</integer>
    </dict>
</dict>
</plist>'''

        # note that if either this string or the user-stonix.py script are altered
        # #they both need to be altered so they match each other identically
        self.userstonixscript = '''#! /usr/bin/env python

#Created on Jan 13, 2014
#
#This script is used by ScheduleStonix.py
#This script will run stonix.py, in user context mode, once daily
#
#@author: bemalmbe


import os,time,getpass,pwd,re

#defaults
username = getpass.getuser()
userhome = ''
scriptsuccess = True

#get current user's home directory
for p in pwd.getpwall():
    if p[0] in username:
        if re.search('^/home/',p[5]) or re.search('^/Users/',p[5]):
            userhome = p[5]

todaysdate = time.strftime("%d%m%Y")
stonixscriptpath = '/usr/sbin/stonix.py'
stonixtempfolder = userhome + '/.stonix/'
alreadyran = False

#if the script has not already run today

if os.path.exists(stonixtempfolder + 'userstonix.log'):

    f = open(stonixtempfolder + 'userstonix.log','r')
    contentlines = f.readlines()
    f.close()

    for line in contentlines:
        line = line.split()
        #script log file entries should follow the format: usernameDDMMYYYY
        if re.search('^' + username,line[0]) and re.search(todaysdate,line[1]):
            alreadyran = True

    #if the script has not yet run today, then run it        
    if not alreadyran:

        try:

            #run stonix -f in user context
            os.system(stonixscriptpath + ' -cf')

        except IOError:
            exitcode = IOError.errno
            print IOError.message
            scriptsuccess = False
        except OSError:
            exitcode = OSError.errno
            print OSError.message
            scriptsuccess = False

        if scriptsuccess:

            i = 0

            for line in contentlines:
                if re.search('^' + username,line) and not re.search(todaysdate,line):
                    line = username + ' ' + todaysdate
                    contentlines[i] = line
                    i += 1

            #create/update log entry
            f = open(stonixtempfolder + 'userstonix.log','w')
            f.writelines(contentlines)
            f.close()

        else:

            print "user-stonix.py script failed to run properly"
            exit(exitcode)'''

###############################################################################

    def report(self):
        '''
        Check that cron file(s) exist and that they are properly configured
        with the correct config string(s)

        @return: bool
        @author: bemalmbe
        '''

        # defaults
        foundcronfile = False
        cronreportstringfound = False
        cronfixstringfound = False
        userstonix = False
        self.compliant = True
        self.detailedresults = ""

        try:

            # if on mac run reportmac
            if self.environ.getostype() == "Mac OS X":
                if not self.reportmac():
                    self.compliant = False

            else:

                self.helper = Pkghelper(self.logger, self.environ)

                if not self.cronfilelocation:
                    if self.helper.manager == 'apt-get':
                        self.cronfilelocation = '/var/spool/cron/crontabs/root'

                # check if the cron file exists on the system
                if os.path.exists(self.cronfilelocation):
                    foundcronfile = True

                # if cron file exists, get file contents
                if foundcronfile:
                    f = open(self.cronfilelocation, 'r')
                    contentlines = f.readlines()
                    f.close()

                    # if config strings exist, system is configured
                    for line in contentlines:
                        if re.search('root nice -n 19 ' + str(self.stonixpath) + '/stonix.py -cr', line):
                            self.detailedresults += "found the correct report line in cron file\n"
                            cronreportstringfound = True
                        if re.search('root nice -n 19 ' + str(self.stonixpath) + '/stonix.py -cf', line):
                            self.detailedresults += "found the correct fix line in the cron file\n"
                            cronfixstringfound = True

                # check the user stonix script for existence and correctness
                if os.path.exists('/etc/profile.d/user-stonix.py'):

                    f = open('/etc/profile.d/user-stonix.py', 'r')
                    contentlines = f.readlines()
                    f.close()

                    userstonixscriptlist = \
                    self.userstonixscript.splitlines(True)

                    if cmp(contentlines, userstonixscriptlist) == 0:
                        userstonix = True

                # if all 3 conditions are met, set configured = True
                if not cronreportstringfound:
                    self.compliant = False
                    self.detailedresults += '\nreport-mode cron job line not found'
                if not cronfixstringfound:
                    self.compliant = False
                    self.detailedresults += '\nfix-mode cron job line not found'
                if not userstonix:
                    self.compliant = False
                    self.detailedresults += '\nuser-mode cron job line not found'

        except(KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults += "\n" + traceback.format_exc()
            self.logger.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant
###############################################################################

    def reportmac(self):
        '''
        Report whether or not stonix is properly scheduled to run randomly,
        weekly in both fix and report in a system context - and once daily in
        fix mode, in a user context

        @return bool
        @author bemalmbe
        '''

        # defaults
        configured = True
        pathsneeded = ['/Library/LaunchDaemons/gov.lanl.stonix.report.plist',
                       '/Library/LaunchDaemons/gov.lanl.stonix.fix.plist',
                       '/Library/LaunchAgents/gov.lanl.stonix.user.plist']

        plistdict = {'/Library/LaunchDaemons/gov.lanl.stonix.report.plist':
                     self.stonixplistreport,
                     '/Library/LaunchDaemons/gov.lanl.stonix.fix.plist':
                     self.stonixplistfix,
                     '/Library/LaunchAgents/gov.lanl.stonix.user.plist':
                     self.stonixplistuser}

        try:

            # if a required path is missing, return False
            for path in pathsneeded:
                if not os.path.exists(path):
                    configured = False
                    self.detailedresults += "Path doesn't exist: " + path + "\n"

                # if path exists, check for required plist content
                else:
                    contents = readFile(path, self.logger)

                    # get contents of appropriate plist script in a list
                    scrptcontents = plistdict[path].splitlines(True)

                    # compare contents of plist script
                    i = 0
                    for i in range(len(contents)):
                        if not re.search('<integer>', contents[i]):
                            if contents[i].strip() != scrptcontents[i].strip():
                                configured = False
                                self.detailedresults += "line not correct: " + str(contents[i]) + " in file: " + str(path) + "\n"

                        else:
                            if not re.search('<integer>[0-9][0-9]{0,1}<\/integer>', contents[i]):
                                configured = False
                                self.detailedresults += "integer line wrong: " + str(contents[i]) + " in file: " + str(path) + "\n"

            for item in plistdict:
                itemlong = item
                itemshort = item.split('/')[3][:-6]
                if not self.svchelper.auditservice(itemlong, itemshort):
                    configured = False

        except (IOError, IndexError):
            raise
        except Exception:
            raise
        return configured
###############################################################################

    def genRandCronTime(self):
        '''
        Generate a random time within 1 week period, format it for cron
        and return it as a string

        @return: string
        @author: Breen Malmberg
        '''

        randday = random.randrange(1, 7)
        randhour = random.randrange(1, 23)
        randminute = random.randrange(1, 59)

        cronstring = str(randminute) + ' ' + str(randhour) + ' * * ' + \
        str(randday)

        return cronstring
###############################################################################

    def fix(self):
        '''
        If no cron file exists, create it (location based on os type)
        If cron file exists but stonix config entry/entries missing, append it

        @author: Breen Malmberg
        '''

        self.detailedresults = ""
        fixresult = True

        try:

            # If mac os, run fixmac
            if self.environ.getostype() == "Mac OS X":
                if not self.fixmac():
                    fixresult = False
                    self.rulesuccess = False

            # else make fixes for *nix os types
            else:

                reportstring = '\n' + str(self.genRandCronTime()) + \
                ' root nice -n 19 ' + str(self.stonixpath) + '/stonix.py' + ' -cr'
                fixstring = '\n' + str(self.genRandCronTime()) + \
                ' root nice -n 19 ' + str(self.stonixpath) + '/stonix.py' + ' -cf\n'

                if os.path.exists(self.cronfilelocation):

                    # get content of current cronfile
                    f = open(self.cronfilelocation, 'r')
                    contentlines = f.readlines()
                    f.close()

                    # if file exists, but lacks config string, then append it
                    # to the file
                    if not self.report():

                        f = open(self.cronfilelocation, 'a')
                        f.write(reportstring + fixstring)
                        f.close()

                        os.chmod(self.cronfilelocation, 0644)
                        os.chown(self.cronfilelocation, 0, 0)
                        self.rulesucces = True

                # if cron file does not exist for whatever reason, add it with
                # the correct config lines
                else:
                    contentlines = []
                    if self.cronfilelocation == '/etc/crontab':
                        contentlines.append('SHELL=/bin/bash\n')
                        contentlines.append('PATH=/sbin:/bin:/usr/sbin:/usr/bin\n')
                        contentlines.append('MAILTO=root\n')
                        contentlines.append('HOME=/\n')
                    contentlines.append(reportstring)
                    contentlines.append(fixstring)

                    if self.cronfilelocation != '/etc/crontab':
                        crondir = os.path.abspath(os.path.join(self.cronfilelocation, os.pardir))
                        if not os.path.exists(crondir):
                            os.makedirs(crondir, 0644)

                    try:

                        f = open(self.cronfilelocation, 'w')
                        f.writelines(contentlines)
                        f.close()

                        # set the correct permissions and ownership for the root
                        # cron file
                        os.chmod(self.cronfilelocation, 0644)
                        os.chown(self.cronfilelocation, 0, 0)
                    except Exception:
                        fixresult = False

                # check for existence and correct text in user context stonix
                # script
                if not os.path.exists('/etc/profile.d/user-stonix.py'):
                    try:
                        f = open('/etc/profile.d/user-stonix.py', 'w')
                        f.write(self.userstonixscript)
                        f.close()

                        os.chown('/etc/profile.d/user-stonix.py', 0, 0)
                        os.chmod('/etc/profile.d/user-stonix.py', 0550)
                    except Exception:
                        fixresult = False

                # fix the user stonix script
                else:
                    f = open('/etc/profile.d/user-stonix.py', 'r')
                    contentlines = f.readlines()
                    f.close()

                    userstonixscriptlist = \
                    self.userstonixscript.splitlines(True)

                    try:

                        if cmp(contentlines, userstonixscriptlist) != 0:
                            f = open('/etc/profile.d/user-stonix.py', 'w')
                            f.writelines(userstonixscriptlist)
                            f.close()

                            os.chown('/etc/profile.d/user-stonix.py', 0, 0)
                            os.chmod('/etc/profile.d/user-stonix.py', 0700)

                    except Exception:
                        fixresult = False

        except(KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults += traceback.format_exc()
            self.logger.log(LogPriority.ERROR, self.detailedresults)
            fixresult = False
            self.rulesuccess = False
        self.formatDetailedResults("fix", fixresult, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return fixresult
###############################################################################

    def fixmac(self):
        '''
        Mac os doesn't use cron. Instead it uses plists to schedule jobs.
        Create plist files as necessary for system runs as well as user context
        (user home director(y)(ies)) plist.

        @author Breen Malmberg
        '''

        retval = False

        # defaults
        servicedict = {'/Library/LaunchDaemons/gov.lanl.stonix.report.plist':
                       'gov.lanl.stonix.report',
                       '/Library/LaunchDaemons/gov.lanl.stonix.fix.plist':
                       'gov.lanl.stonix.fix',
                       '/Library/LaunchAgents/gov.lanl.stonix.user.plist':
                       'gov.lanl.stonix.user'}

        # create weekly report plist file
        f = open('/Library/LaunchDaemons/gov.lanl.stonix.report.plist',
                 'w')
        f.write(self.stonixplistreport)
        f.close()
        os.chown('/Library/LaunchDaemons/gov.lanl.stonix.report.plist',
                 0, 0)
        os.chmod('/Library/LaunchDaemons/gov.lanl.stonix.report.plist',
                 0o644)
        self.detailedresults += "Wrote the report plist\n"
        # create weekly fix plist file
        f = open('/Library/LaunchDaemons/gov.lanl.stonix.fix.plist', 'w')
        f.write(self.stonixplistfix)
        f.close()
        os.chown('/Library/LaunchDaemons/gov.lanl.stonix.fix.plist', 0, 0)
        os.chmod('/Library/LaunchDaemons/gov.lanl.stonix.fix.plist', 0o644)
        self.detailedresults += "Wrote the fix plist\n"
        # create once-daily user context plist file
        f = open('/Library/LaunchAgents/gov.lanl.stonix.user.plist', 'w')
        f.write(self.stonixplistuser)
        f.close()
        os.chown('/Library/LaunchAgents/gov.lanl.stonix.user.plist', 0, 0)
        os.chmod('/Library/LaunchAgents/gov.lanl.stonix.user.plist', 0o644)
        self.detailedresults += "Wrote the user plist\n"
        retval = True
        for item in servicedict:
            self.svchelper.enableservice(item, servicedict[item])
        return retval
