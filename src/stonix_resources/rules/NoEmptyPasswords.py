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
Created on Oct 29, 2012

@author: dwalker
@change: 04/18/2014 dkennel Replaced old-style CI invocation.
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2015/04/16 dkennel updated for new isApplicable
@change: 2015/10/07 eball Help text/PEP8 cleanup
'''


from stonixutilityfunctions import setPerms, checkPerms, readFile, writeFile
from stonixutilityfunctions import getUserGroupName
from rule import Rule
from logdispatcher import LogPriority
from pkghelper import Pkghelper
from subprocess import call
import os
import traceback
import re
import stat
import pwd
import grp  # grp is a valid package


class NoEmptyPasswords(Rule):

    def __init__(self, config, environ, logger, statechglogger):
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 41
        self.rulename = "NoEmptyPasswords"
        self.mandatory = True
        self.sethelptext()
        self.rootrequired = True
        self.detailedresults = "NoEmptyPasswords rule has not yet been run"
        self.guidance = ["NSA 2.3.1.5"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd']}

        # configuration item instantiation
        datatype = 'bool'
        key = 'NOEMPTYPASSWORDS'
        instructions = "This rule should not be disabled under any " + \
            "circumstances."
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)
        self.users = []
        self.empty = []

###############################################################################

    def report(self):
        '''Opens the /etc/shadow file and checks the second field of each entry
        for empty passwords. If they exist, call the fix method
        @author: dwalker


        '''
        try:
            self.detailedresults = ""
            compliant = True
            self.ph = ""
            osfamily = self.environ.getosfamily()
            if osfamily == "linux" or osfamily == "solaris":
                self.ph = Pkghelper(self.logger, self.environ)
                self.shadow = "/etc/shadow"
                self.passwd = "/etc/passwd"
            elif osfamily() == "freebsd" or osfamily() == "darwin":
                self.shadow = "/etc/master.passwd"
                self.passwd = "/etc/passwd"
            compliant = True
            if not os.path.exists(self.passwd):
                self.detailedresults += "This system doesn't contain an \
/etc/passwd file\n"
                compliant = False
            else:
                contents = readFile(self.passwd, self.logger)
                if not contents:
                    self.detailedresults += "This system contains an \
/etc/passwd file but it's blank\n"
                    compliant = False
                else:
                    try:
                        for line in contents:
                            if re.search(":", line):
                                line = line.split(":")
                                if int(line[2]) >= 500:
                                    self.users.append(line[0])
                    except IndexError:
                        self.detailedresults += traceback.format_exc() + "\n"
                        self.detailedresults += "Index out of range\n"
                        compliant = False
            if not os.path.exists(self.shadow):
                self.detailedresults += "This system doesn't contain an \
/etc/shadow file or /etc/master.passwd file\n"
                compliant = False
            if not self.users:
                self.detailedresults += "There are no local accounts on this \
system that need to be checked for empty passwords\n"
            contents = readFile(self.shadow, self.logger)
            if not contents:
                self.detailedresults += "Your system contains an \
/etc/shadow file or /etc/master.passwd file but it's blank\n"
                compliant = False
            else:
                try:
                    for user in self.users:
                        for line in contents:
                            if re.search(":", line):
                                line = line.split(":")
                                if line[0] == user:
                                    # if line[1].isdigit():
                                    #    compliant = False
                                    # elif line[1].strip() == "":
                                    if line[1].strip() == "":
                                        if line[0] not in self.empty:
                                            self.empty.append(line[0])
                                            compliant = False
                                            break
                except IndexError:
                    self.detailedresults += traceback.format_exc() + "\n"
                    self.detailedresults += "Index out of range\n"
                    compliant = False
            if self.ph:
                if self.ph.manager == "apt-get":
                    retval = getUserGroupName("/etc/shadow")
                    if retval[0] != "root" or retval[1] != "shadow":
                        compliant = False
                else:
                    if not checkPerms(self.shadow, [0, 0, 256], self.logger) and \
                       not checkPerms(self.shadow, [0, 0, 0], self.logger):
                        compliant = False
            else:
                if not checkPerms(self.shadow, [0, 0, 256], self.logger) and \
                   not checkPerms(self.shadow, [0, 0, 0], self.logger):
                    compliant = False
            self.compliant = compliant
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += "\n" + traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

###############################################################################

    def fix(self):
        try:
            if not self.ci.getcurrvalue():
                return
            osfam = self.environ.getosfamily()
            self.detailedresults = ""
            if osfam == "linux":
                command = "/usr/sbin/usermod -L "
                self.rulesuccess = self.fixMain(command)
            elif osfam == "freebsd":
                command = "/usr/sbin/pw lock "
                self.rulesuccess = self.fixMain(command)
            elif osfam == "solaris":
                command = "/usr/bin/passwd -l "
                self.rulesuccess = self.fixMain(command)
            else:
                self.rulesuccess = self.fixOther()
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

###############################################################################

    def fixMain(self, command):
        '''Entries that are found with an empty password field (2nd field)
        should have the blank field replaced with an !
        @author: dwalker

        :param command: 

        '''
        success = True
        if os.path.exists(self.shadow):
            if self.empty:
                for user in self.empty:
                    try:
                        retval = call(command + user, stdout=None, shell=True)
                        if retval != 0:
                            self.detailedresults += "not able to lock the \
following account: " + user + "\n"
                            success = False
                    except OSError:
                        success = False
                        self.detailedresults += traceback.format_exc() + "\n"
                        self.detailedresults += " unable to run the account \
lock command\n"
            if self.ph:
                if self.ph.manager == "apt-get":
                    retval = getUserGroupName("/etc/shadow")
                    if retval[0] != "root" or retval[1] != "shadow":
                        uid = pwd.getpwnam("root").pw_uid
                        gid = grp.getgrnam("shadow").gr_gid
                        setPerms("/etc/shadow", [uid, gid, 416], self.logger)
                else:
                    if not checkPerms(self.shadow, [0, 0, 256], self.logger) \
                       and not checkPerms(self.shadow, [0, 0, 0], self.logger):
                        if not setPerms(self.shadow, [0, 0, 256], self.logger):
                            success = False
            else:
                if not checkPerms(self.shadow, [0, 0, 256], self.logger) and \
                   not checkPerms(self.shadow, [0, 0, 0], self.logger):
                    if not setPerms(self.shadow, [0, 0, 256], self.logger):
                        success = False
            return success
        else:
            self.detailedresults += "/etc/shadow file or /etc/master.passwd \
file not present, cannot perform fix\n"
            return False

###############################################################################

    def fixOther(self):
        config = ""
        success = True
        permswrong = False
        debug = ""
        if not os.path.exists(self.shadow):
            debug += "shadow or master.passwd file not present, \
cannot perform fix"
            self.logger.log(LogPriority.DEBUG, debug)
            return False
        statdata = os.stat(self.shadow)
        owner = statdata.st_uid
        group = statdata.st_gid
        mode = stat.S_IMODE(statdata.st_mode)
        if not checkPerms(self.shadow, [0, 0, 256], self.logger) or \
           not checkPerms(self.shadow, [0, 0, 0], self.logger):
            permswrong = True
            if not setPerms(self.shadow, [0, 0, 256], self.logger):
                success = False
        contents = readFile(self.shadow, self.logger)
        if not contents:
            return False
        if self.empty:
            try:
                for line in contents:
                    for user in self.empty:
                        if re.search(":", line):
                            temp = line.split(':')
                            if temp[0] == user:
                                tempstring = ""
                                if temp[1].strip() == "":
                                    temp[1] = "!"
                                    tempstring = ":".join(temp)
                                    config += tempstring
                                    break
                            else:
                                config += line
                        else:
                            config += line
                            continue
            except IndexError:
                raise
            except Exception:
                self.detailedresults += traceback.format_exc() + "\n"
                self.detailedresults += "Index out of range\n, stonix will \
not continue to complete fix"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                return False
            tempfile = self.shadow + ".tmp"
            if not writeFile(tempfile, config, self.logger):
                success = False
            os.rename(tempfile, self.shadow)
            if permswrong:
                os.chown(self.shadow, 0, 0)
                os.chmod(self.shadow, 256)
            else:
                os.chown(self.shadow, owner, group)
                os.chmod(self.shadow, mode)
        return success

###############################################################################

    def undo(self):
        '''Note! There is no undo method for this rule (NoEmptyPasswords) because
        of the nature of the fix this rule implements and the high risk any
        system carries if this rule is ever not in effect.


        :returns: void :
        @author dwalker

        '''
        try:
            self.detailedresults = "no undo available"
            self.logger.log(LogPriority.INFO, self.detailedresults)
        except(KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.detailedresults = traceback.format_exc()
            self.logger.log(LogPriority.ERROR, self.detailedresults)
