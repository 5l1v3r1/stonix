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
Created on Jul 11, 2013

@author: dwalker
@change: 2014-03-26 ekkehard changed rule to ruleKVEditor rule add mac support
@change: 2014-04-08 ekkehard fix OS X issue with with configuration item
@change: 2014-04-21 dkennel Updated to use new CI invocation
@change: 2014-07-21 ekkehard fix OS X Mavericks reporting issues
@change: 2014-07-29 ekkehard refix OS X Mavericks issues
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2015/04/14 dkennel update for new isApplicable
@change: 2015/07/28 eball Fixed path validation problems in fixKde
@change: 2015/07/28 eball Fixed return value and statechglogging in correctFile
@change: 2015/08/26 ekkehard - Artifact artf37282 : ConfigureScreenLocking(74) 
                             - askForPasswordDelay not set to 0
'''
from __future__ import absolute_import
from ..stonixutilityfunctions import iterate, checkPerms, setPerms
from ..stonixutilityfunctions import readFile, resetsecon
from ..ruleKVEditor import RuleKVEditor
from ..logdispatcher import LogPriority
from ..pkghelper import Pkghelper
from subprocess import PIPE, Popen
from ..KVEditorStonix import KVEditorStonix
from ..CommandHelper import CommandHelper
import os
import traceback
import re
from pwd import getpwnam


class ConfigureScreenLocking(RuleKVEditor):

    def __init__(self, config, environ, logdispatcher, statechglogger):
        RuleKVEditor.__init__(self, config, environ, logdispatcher,
                              statechglogger)
        self.logger = logdispatcher
        self.rulenumber = 74
        self.rulename = "ConfigureScreenLocking"
        self.mandatory = True
        self.rootrequired = False
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.10.10']}}
        self.effectiveUserID = self.environ.geteuid()
        if self.environ.getosfamily() == "darwin":
            self.helptext = "This rule will configure screen saver " + \
                            "settings."
        else:
            self.helptext = "This rule will configure Screen locking " + \
            "after 15 minutes of continuous inactivity.  This rule will " + \
            "only configure screen locking for gnome and kde.  Other " + \
            "Desktop Managers may be supported in the future. This rule " + \
            "should work the same for all operating systems due to the " + \
            "consistency of kde and gnome. If either or both kde and " + \
            "gnome are not installed this will count as a pass. ***Please " + \
            "be advised: there is no undo method for this rule***"
        self.formatDetailedResults("initialize")
        self.guidance = ["NSA 2.3.5.6.1"]
        if self.environ.getosfamily() == "darwin":
            if self.effectiveUserID == 0:
                self.addKVEditor("SystemAskForPasswordSystem",
                                 "defaults",
                                 "/Library/Preferences/com.apple.screensaver",
                                 "",
                                 {"askForPassword": ["1", "-int 1"]},
                                 "present",
                                 "",
                                 "Ask for password when system wide " +
                                 "screen saver is on.",
                                 None,
                                 False,
                                 {"askForPassword": ["0", "-int 0"]})
                self.addKVEditor("SystemSetScreenSaverIdleTime",
                                 "defaults",
                                 "/Library/Preferences/com.apple.screensaver",
                                 "",
                                 {"idleTime": ["840", "-int 840"]},
                                 "present",
                                 "",
                                 "Sets system the screen saver to " +
                                 "activate after 14 minutes of idleTime.",
                                 None,
                                 False,
                                 {"idleTime":
                                  ["The domain/default pair of ( .+" +
                                   "com\.apple\.screensaver, " +
                                   "idleTime) does not " +
                                   "exist",
                                   None]})
                self.addKVEditor("SystemLoginWindowIdleTime",
                                 "defaults",
                                 "/Library/Preferences/com.apple.screensaver",
                                 "",
                                 {"loginWindowIdleTime": ["840", "-int 840"]},
                                 "present",
                                 "",
                                 "Sets system LoginWindowIdleTime to " +
                                 "14 minutes.",
                                 None,
                                 False,
                                 {"loginWindowIdleTime":
                                  ["The domain/default pair of ( .+" +
                                   "com\.apple\.screensaver, " +
                                   "loginWindowIdleTime) does not " +
                                   "exist",
                                   None]})
            else:
                self.addKVEditor("AskForPassword",
                                 "defaults",
                                 "~/Library/Preferences/com.apple.screensaver",
                                 "",
                                 {"askForPassword": ["1", "-int 1"]},
                                 "present",
                                 "",
                                 "Ask for password when screen saver is on.",
                                 None,
                                 False,
                                 {"askForPassword": ["0", "-int 0"]})
                self.addKVEditor("AskForPasswordDelay",
                                 "defaults",
                                 "~/Library/Preferences/com.apple.screensaver",
                                 "",
                                 {"askForPasswordDelay": ["0", "-int 0"]},
                                 "present",
                                 "",
                                 "Delay asking for password by 0 seconds.",
                                 None,
                                 False,
                                 {"askForPasswordDelay":
                                  ["The domain/default pair of ( .+" +
                                   "com\.apple\.screensaver, " +
                                   "askForPassword) does not " +
                                   "exist",
                                   None]})
        else:

            datatype = 'bool'
            key = 'CONFIGURESCREENLOCKING'
            instructions = "To disable this rule set the value of " + \
                           "CONFIGURESCREENLOCKING to False."
            default = True
            self.ci = self.initCi(datatype, key, instructions, default)

            self.kdeprops = {"ScreenSaver": {"Enabled": "true",
                                             "Lock": "true",
                                             "LockGrace": "60000",
                                             "Timeout": "840"}}
            self.gnomeInst = True
            self.iditerator = 0

    def report(self):
        '''
        ConfigureScreenLocking.report() method to report whether system
        is configured to screen locking NSA standards.  If the system is linux,
        although many desktops are available, this rule will only check the
        two most popular desktops, KDE, and Gnome.
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if system is compliant, False if it isn't
        '''
        try:
            compliant = True
            self.detailedresults = ""
            if self.environ.getosfamily() == "darwin":
                self.compliant = self.reportMac()
            else:
                self.ph = Pkghelper(self.logger, self.environ)
                if not self.reportGnome():
                    compliant = False
                if not self.reportKde():
                    compliant = False
                self.compliant = compliant
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

    def reportMac(self):
        '''
        Mac osx specific report submethod
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if system is compliant, False if it isn't
        '''
        success = RuleKVEditor.report(self, True)
        return success

###############################################################################

    def reportGnome(self):
        '''determines if gnome is installed, if so, checks to see if the
        return value strings from running the gconftool-2 command are
        correct.  Gconftool-2 command only works in root mode so if not root
        do not audit gnome and just return true
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool
        '''

        compliant = True
        self.cmdhelper = CommandHelper(self.logger)
        gconf = "/usr/bin/gconftool-2"
        if not os.path.exists(gconf):
            self.detailedresults += "gnome is not installed\n"
            self.gnomeInst = False
            return compliant
        getcmds = {" --get /apps/gnome-screensaver/idle_activation_enabled":
                   "true",
                   " --get /apps/gnome-screensaver/lock_enabled": "true",
                   " --get /apps/gnome-screensaver/mode": "blank-only",
                   " --get /apps/gnome-screensaver/idle_delay": "15"}
        for cmd in getcmds:
            cmd2 = gconf + cmd
            self.cmdhelper.executeCommand(cmd2)
            output = self.cmdhelper.getOutput()
            error = self.cmdhelper.getError()
            if output:
                if cmd == " --get /apps/gnome-screensaver/idle_delay":
                    if int(output[0].strip()) > 15:
                        compliant = False
                elif output[0].strip() != getcmds[cmd]:
                    self.detailedresults += cmd2 + " didn't produce the \
desired value after being run which is " + getcmds[cmd] + "\n"
                    compliant = False
            elif error:
                self.detailedresults += "There is no value set for:" + \
                                        cmd2 + "\n"
                compliant = False
        return compliant

###############################################################################

    def reportKde(self):
        '''determines if kde is installed, if so, ensures kde is configured
        by enabling screenlocking, automatically going black after 14 minutes
        and if inactivity ensues after 14 minutes, screen fully locks after 1
        additional minute of inactivity for a total of 15 minutes activity
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool
        '''
        finalcompliant = True
        self.kdefix = []
        debug = ""
        if self.environ.geteuid() == 0:
            contents = readFile("/etc/passwd", self.logger)
            if not contents:
                debug = "You have some serious issues, /etc/passwd is blank\n"
                self.logger.log(LogPriority.INFO, debug)
                self.rulesuccess = False
                return False
            for line in contents:
                compliant = True
                temp = line.split(":")
                try:
                    if int(temp[2]) >= 500:
                        if temp[5] and re.search('/', temp[5]):
                            homebase = temp[5]
                            if not re.search("^/home/", homebase):
                                continue
                            homebase += '/.kde'
                            if not os.path.exists(homebase):
                                compliant = False
                            else:
                                homebase += '/share'
                                if not os.path.exists(homebase):
                                    compliant = False
                                else:
                                    homebase += '/config'
                                    if not os.path.exists(homebase):
                                        compliant = False
                                    else:
                                        kfile = homebase + '/kdesktoprc'
                                        if not os.path.exists(kfile):
                                            kfile = homebase + '/kscreensaverrc'
                                            if not os.path.exists(kfile):
                                                compliant = False
                                            else:
                                                uid = getpwnam(temp[0])[2]
                                                gid = getpwnam(temp[0])[3]
                                                if not checkPerms(kfile,
                                                                  [uid, gid, 384],
                                                                  self.logger):
                                                    compliant = False
                                                if not self.searchFile(kfile):
                                                    compliant = False
                            if not compliant:
                                finalcompliant = False
                                self.kdefix.append(temp[0])
                        else:
                            debug += "placeholder 6 in /etc/passwd is not a \
directory, invalid form of /etc/passwd"
                            self.logger.log(LogPriority.DEBUG, debug)
                            return False
                except IndexError:
                    compliant = False
                    debug += traceback.format_exc() + "\n"
                    debug += "Index out of range\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    break
                except Exception:
                    break
            if self.kdefix:
                self.detailedresults += "The following users don't " + \
                                        "have kde configured:\n"
                for user in self.kdefix:
                    self.detailedresults += user + "\n"
        else:
            if self.environ.getosfamily() == "solaris":
                who = "/usr/bin/who"
            else:
                who = "/usr/bin/whoami"
            message = Popen(who, stdout=PIPE, shell=False)
            if self.environ.getosfamily() == "solaris":
                info = message.stdout.read().split()
                info = info[0]
            else:
                info = message.stdout.read().strip()
            contents = readFile('/etc/passwd', self.logger)
            if not contents:
                debug += "You have some serious issues, /etc/passwd is blank\n"
                self.logger.log(LogPriority.INFO, debug)
                self.rulesuccess = False
                return False
            compliant = True
            for line in contents:
                temp = line.split(':')
                try:
                    if temp[0] == info:
                        if temp[5] and re.search('/', temp[5]):
                            homebase = temp[5]
                            if not re.search("^/home/", homebase):
                                continue
                            homebase += '/.kde'
                            if not os.path.exists(homebase):
                                compliant = False
                            else:
                                homebase += '/share'
                                if not os.path.exists(homebase):
                                    compliant = False
                                else:
                                    homebase += '/config'
                                    if not os.path.exists(homebase):
                                        compliant = False
                                    else:
                                        kfile = homebase + '/kdesktoprc'
                                        if not os.path.exists(kfile):
                                            kfile = homebase + '/kscreensaverrc'
                                            if not os.path.exists(kfile):
                                                compliant = False
                                            else:
                                                uid = getpwnam(temp[0])[2]
                                                gid = getpwnam(temp[0])[3]
                                                if not checkPerms(kfile,
                                                                  [uid, gid, 384],
                                                                  self.logger):
                                                    compliant = False
                                                if not self.searchFile(kfile):
                                                    compliant = False
                            if not self.searchFile(kfile):
                                self.kdefix.append(temp[0])
                                compliant = False
                            if not compliant:
                                finalcompliant = False
                            break
                        else:
                            debug += "placeholder 6 in /etc/passwd is not a \
directory, invalid form of /etc/passwd"
                            self.logger.log(LogPriority.DEBUG, debug)
                            return False
                        break
                except IndexError:
                    compliant = False
                    debug += traceback.format_exc() + "\n"
                    debug += "Index out of range\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    break
                except Exception:
                    break
        return finalcompliant

###############################################################################

    def fix(self):
        '''
        ConfigureScreenLocking.fix() method to correct screen locking
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if fix is successful, False if it isn't
        '''
        try:
            self.detailedresults = ""
            if self.environ.getosfamily() == "darwin":
                self.rulesuccess = self.fixMac()
            elif self.ci.getcurrvalue():
                # clear out event history so only the latest fix is recorded
                if self.environ.geteuid() == 0:
                    self.iditerator = 0
                    eventlist = self.statechglogger.findrulechanges(self.rulenumber)
                    for event in eventlist:
                        self.statechglogger.deleteentry(event)
                if self.fixGnome() and self.fixKde():
                    self.rulesuccess = True
                else:
                    self.rulesuccess = False
        except(KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults += "\n" + traceback.format_exc()
            self.logger.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess

###############################################################################

    def fixMac(self):
        '''
        Mac osx specific fix submethod
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if system is successfully fix, False if it isn't
        '''
        success = RuleKVEditor.fix(self, True)
        return success

###############################################################################

    def fixGnome(self):
        '''ensures gnome is configured to automatically screen lock after
        15 minutes of inactivity, if gnome is installed
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if gnome is successfully configured, False if it
                isn't
        '''
        if not self.gnomeInst:
            self.detailedresults += "Gnome is not installed, no fix necessary \
for this portion of the rule\n"
            return True
        info = ""
        gconf = "/usr/bin/gconftool-2"
        gcmd1 = " --get /apps/gnome-screensaver/idle_activation_enabled"
        gcmd2 = " --get /apps/gnome-screensaver/lock_enabled"
        gcmd3 = " --get /apps/gnome-screensaver/mode"
        gcmd4 = " --get /apps/gnome-screensaver/idle_delay"
        scmd1 = " --type bool --set /apps/gnome-screensaver/idle_activation_enabled true"
        scmd2 = " --type bool --set /apps/gnome-screensaver/lock_enabled true"
        scmd3 = ' --type string --set /apps/gnome-screensaver/mode "blank-only"'
        scmd4 = " --type int --set /apps/gnome-screensaver/idle_delay 15"
        success = True
        cmd = gconf + gcmd1
        if self.cmdhelper.executeCommand(cmd):
            output = self.cmdhelper.getOutput()
            error = self.cmdhelper.getError()
            if output:
                if output[0].strip() != "true":
                    cmd = gconf + scmd1
                    if self.cmdhelper.executeCommand(cmd):
                        output = self.cmdhelper.getOutput()
                        error = self.cmdhelper.getError()
                        if self.cmdhelper.getReturnCode() != 0:
                            info += "Unable to set value for " + scmd1 + "\n"
                            success = False
            elif error:
                cmd = gconf + scmd1
                if self.cmdhelper.executeCommand(cmd):
                    if self.cmdhelper.getReturnCode() != 0:
                        info += "Unable to set value for " + scmd1 + "\n"
                        success = False
        cmd = gconf + gcmd2
        if self.cmdhelper.executeCommand(cmd):
            output = self.cmdhelper.getOutput()
            error = self.cmdhelper.getError()
            if output:
                if output[0].strip() != "true":
                    cmd = gconf + scmd2
                    if self.cmdhelper.executeCommand(cmd):
                        output = self.cmdhelper.getOutput()
                        error = self.cmdhelper.getError()
                        if self.cmdhelper.getReturnCode() != 0:
                            info += "Unable to set value for " + scmd2 + "\n"
                            success = False
            elif error:
                cmd = gconf + scmd2
                if self.cmdhelper.executeCommand(cmd):
                    if self.cmdhelper.getReturnCode() != 0:
                        info += "Unable to set value for " + scmd2 + "\n"
                        success = False
        cmd = gconf + gcmd3
        if self.cmdhelper.executeCommand(cmd):
            output = self.cmdhelper.getOutput()
            error = self.cmdhelper.getError()
            if output:
                if output[0].strip() != "blank only":
                    cmd = gconf + scmd3
                    if self.cmdhelper.executeCommand(cmd):
                        output = self.cmdhelper.getOutput()
                        error = self.cmdhelper.getError()
                        if self.cmdhelper.getReturnCode() != 0:
                            info += "Unable to set value for " + scmd3 + "\n"
                            success = False
            elif error:
                cmd = gconf + scmd3
                if self.cmdhelper.executeCommand(cmd):
                    if self.cmdhelper.getReturnCode() != 0:
                        info += "Unable to set value for " + scmd3 + "\n"
                        success = False
        cmd = gconf + gcmd4
        if self.cmdhelper.executeCommand(cmd):
            output = self.cmdhelper.getOutput()
            error = self.cmdhelper.getError()
            if output:
                if int(output[0].strip()) > 15:
                    cmd = gconf + scmd4
                    if self.cmdhelper.executeCommand(cmd):
                        output = self.cmdhelper.getOutput()
                        error = self.cmdhelper.getError()
                        if self.cmdhelper.getReturnCode() != 0:
                            info += "Unable to set value for " + scmd4 + "\n"
                            success = False
            elif error:
                cmd = gconf + scmd4
                if self.cmdhelper.executeCommand(cmd):
                    if self.cmdhelper.getReturnCode() != 0:
                        info += "Unable to set value for " + scmd4 + "\n"
                        success = False
        return success

###############################################################################

    def fixKde(self):
        '''This method checks if the kde screenlock file is configured
        properly.  Please note, this rule may fail if the owner and group of
        configuration file are not that of the user in question but doesn't
        necessarily mean your system is out of compliance.  If the fix fails
        Please check the logs to determing the real reason of non rule success.
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if KDE is successfully configured, False if it
                isn't
        '''

        debug = ""
        success = True

        for user in self.kdefix:
            if self.environ.getosfamily() == "solaris":
                homebase = "/export/home/"
            else:
                homebase = "/home/"
            homebase += user
            homebase += "/.kde/share/config"
            if not os.path.exists(homebase):
                os.makedirs(homebase)
            kfile = homebase + "/kdesktoprc"
            if not os.path.exists(kfile):
                kfile = homebase + "/kscreensaverrc"
                if not os.path.exists(kfile):
                    if not self.correctFile(kfile, user, homebase):
                        return False
        if debug:
            self.logger.log(LogPriority.DEBUG, debug)
        return success

###############################################################################

    def searchFile(self, filehandle):
        '''temporary method to separate the code to find directives from the
        rest of the code.  Will put back all in one method eventually
        @author: dwalker
        @return: bool
        @param filehandle: string
        '''
        self.editor = ""
        kvt = "tagconf"
        intent = "present"
        tpath = filehandle + ".tmp"
        conftype = "closedeq"
        self.editor = KVEditorStonix(self.statechglogger, self.logger, kvt,
                                     filehandle, tpath, self.kdeprops, intent,
                                     conftype)
        if not self.editor.report():
            return False
        else:
            return True
###############################################################################

    def correctFile(self, kfile, user, homebase):
        '''separate method to find the correct contents of each file passed in
        as a parameter.
        @author: dwalker
        @return: bool
        @param filehandle: string
         '''
        created = False
        success = True
        if not os.path.exists(kfile):
            f = open(kfile, "w")
            f.close()
            created = True
            if self.environ.geteuid() == 0:
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "creation", "filepath": kfile}
                self.statechglogger.recordchgevent(myid, event)

        uid = getpwnam(user)[2]
        gid = getpwnam(user)[3]
        if not created:
            if not checkPerms(kfile, [uid, gid, 0600], self.logger):
                if self.environ.geteuid() == 0:
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(kfile, [uid, gid, 0600], self.logger,
                                    self.statechglogger, myid):
                        success = False
        if not self.searchFile(kfile):
            if self.editor.fixables:
                if self.environ.geteuid() == 0:
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    self.editor.setEventID(myid)
                if not self.editor.fix():
                    return False
                elif not self.editor.commit():
                    return False
        os.chmod(kfile, 0600)
        os.chown(kfile, uid, gid)
        resetsecon(homebase)
        return success
