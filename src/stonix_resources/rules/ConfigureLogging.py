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
Created on May 20, 2013

@author: dwalker
@change: 02/12/2014 ekkehard Implemented self.detailedresults flow
@change: 02/12/2014 ekkehard Implemented isapplicable
@change: 04/18/2014 dkennel updated to use new CI class
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2015/04/14 dkennel updated for new isApplicable
@change: 2015/10/07 eball Help text cleanup
@change: 2016/01/22 eball Changed daemon log level from daemon.info to daemon.*
@change: 2016/05/31 ekkehard Added OpenDirectory Logging
@change: 2016/06/22 eball Improved report feedback for reportMac
'''
from __future__ import absolute_import
from ..stonixutilityfunctions import iterate, resetsecon, createFile, getUserGroupName
from ..stonixutilityfunctions import readFile, writeFile, checkPerms, setPerms, checkUserGroupName
from ..ruleKVEditor import RuleKVEditor
from ..pkghelper import Pkghelper
from ..logdispatcher import LogPriority
from ..ServiceHelper import ServiceHelper
from ..CommandHelper import CommandHelper
from ..localize import WINLOG, LANLLOGROTATE
from subprocess import PIPE, Popen
import os
import pwd
import traceback
import re
import grp
import stat


class ConfigureLogging(RuleKVEditor):

    def __init__(self, config, environ, logger, statechglogger):
        RuleKVEditor.__init__(self, config, environ, logger,
                              statechglogger)
        self.logger = logger
        self.rulenumber = 16
        self.rulename = "ConfigureLogging"
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = """This rule combines several tasks. Log Rotation \
ensures that logs don't completely fill up disk space. It also configures \
logwatch on the central log server.
After the fix runs, you may want to reformat the configuration files that were \
altered to line up correctly with columns (such as in newsyslog.conf in \
FreeBSD). This is purely personal preference.
For operating systems such as Linux, many log file entries may have their own \
block as well, and many of the blocks may contain the same contents. Feel \
free to combine all of these on one line.  If an entry in the Linux fix has \
incorrect log specs inside the brackets, the log entry is removed where it \
previously existed and then rewritten with the recommended specs. It does not \
retain any of the user's previous specs.  However, where that log was \
removed, the specs inside the brackets may remain with no log file to \
accompany it.  Delete these, as they will make your configuration file \
invalid."""

        self.guidance = ["2.6.1.1", "2.6.1.2", "2.6.1.3"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.12.10']}}

        datatype = 'bool'
        key = 'CONFIGURELOGGING'
        instructions = "To disable this rule set the value of " + \
            "CONFIGURELOGGING to False."
        default = True
        self.ci = self.initCi(datatype, key, instructions, default)
        self.rootrequired = True
        self.service = ""
        self.logd = ""
        self.iditerator = 0
        self.daemon = ""
        self.sh = ServiceHelper(self.environ, self.logger)
        self.ch = CommandHelper(self.logger)
        self.logs = {"rsyslog": False,
                     "syslog": False}
        self.created1, self.created2 = True, True
        if self.environ.getostype() == "Mac OS X":
            self.addKVEditor("OpenDirectoryLogging",
                             "defaults",
                             "/Library/Preferences/OpenDirectory/opendirectoryd",
                             "",
                             {"Debug Logging Level": ["5", "5"]},
                             "present",
                             "",
                             'Set OpenDirectory "Debug Logging Level" Level to 5 ' + \
                             "This show user creation and deletion events " + \
                             "in '/private/var/log/opendirectoryd.log'.",
                             None,
                             False,
                             {})

    def report(self):
        '''ConfigureLogging.report() Public method to report on the
        configuration status of the logging daemons and associated files.
        Configures logging and log rotation
        @author: dwalker
        @param self - essential if you override this definition
        @return: bool - True if system is compliant, False if it isn't
        '''

        # UPDATE THIS SECTION IF YOU CHANGE THE CONSTANTS BEING USED IN THE RULE
        constlist = [WINLOG, LANLLOGROTATE]
        if not self.checkConsts(constlist):
            self.compliant = False
            self.detailedresults = "\nPlease ensure that the constants: WINLOG and LANLLOGROTATE, in localize.py, are defined and are not None. This rule will not function without them."
            self.formatDetailedResults("report", self.compliant, self.detailedresults)
            return self.compliant

        try:
            self.directories = ["/var/log/daemon",
                                "/var/log/auth",
                                "/var/log/user",
                                "/var/log/kern",
                                "/var/log/lpr",
                                "/var/log/syslog",
                                "/var/log/cron",
                                "/var/log/maillog",
                                "/var/log/local",
                                "/var/log/ftp"]
            self.bootlog = "/var/log/boot.log"
            self.logfiles = {"*.*,mark.*": "/var/log/messages",
                             "daemon.*": "/var/log/daemon",
                             "auth.*,mark.*,authpriv.*": "/var/log/auth",
                             "user.*": "/var/log/user",
                             "kern.*": "/var/log/kern",
                             "lpr.*": "/var/log/lpr",
                             "syslog.*": "/var/log/syslog",
                             "cron.*": "/var/log/cron",
                             "mail,uucp,news.*": "/var/log/maillog",
                             "local0,local1,local2,local3.*": "/var/log/local",
                             "local4,local5,local6,local7.*": "/var/log/local",
                             "ftp.*": "/var/log/ftp",
                             "local7.*": "/var/log/boot.log",
                             "auth,authpriv.*,mark.*": WINLOG}
            self.detailedresults = ""
            self.wronglogrot = []
            self.missinglogrot = []
            self.config = []
            if self.environ.getosfamily() == "linux":
                self.ph = Pkghelper(self.logger, self.environ)
                self.compliant = self.reportSysRSyslog()
            elif self.environ.getosfamily() == "solaris":
                self.helper = Pkghelper(self.logger, self.environ)
                if self.path:
                    self.compliant = self.reportSol(self.path[0], self.path[1])
                else:
                    self.detailedresults = "no log daemons exist\n"
            elif self.environ.getosfamily() == "freebsd":
                if self.path:
                    self.compliant = self.reportFreebsd(self.path[0],
                                                        self.path[1])
                else:
                    self.detailedresults = "no log daemons exist\n"
            elif self.environ.getostype() == "Mac OS X":
                self.compliant = self.reportMac()
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

    def fix(self):
        '''ConfigureLogging.fix() Public method to fix any issues that were
        found in the report method.
        @author: dwalker
        @return: bool - False if the method died during execution
        @param self:essential if you override this definition
        '''

        # UPDATE THIS SECTION IF YOU CHANGE THE CONSTANTS BEING USED IN THE RULE
        constlist = [WINLOG, LANLLOGROTATE]
        if not self.checkConsts(constlist):
            self.rulesuccess = False
            self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)
            return self.rulesuccess

        try:
            if not self.ci.getcurrvalue():
                return
            status = False
            self.detailedresults = ""

            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)

            if self.environ.getosfamily() == "linux":
                status = self.fixSysRsyslog()
            if self.environ.getosfamily() == "solaris":
                if not self.path:
                    self.detailedresults += "report previously found no log \
daemon, will not attempt to install one, unable to proceed with fix\n"
                    self.formatDetailedResults("fix", False,
                                               self.detailedresults)
                    self.logger.log(LogPriority.DEBUG, self.detailedresults)
                    return
                status = self.fixSol(self.path[0], self.path[1])
            if self.environ.getosfamily() == "freebsd":
                if not self.path:
                    self.detailedresults += "report previously found no log \
daemon, will not attempt to install one, unable to proceed with fix\n"
                    self.formatDetailedResults("fix", False,
                                               self.detailedresults)
                    self.logger.log(LogPriority.DEBUG, self.detailedresults)
                    return
                status = self.fixFreebsd(self.path[0], self.path[1])
            if self.environ.getostype() == "Mac OS X":
                status = self.fixMac()
            self.rulesuccess = status
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

    def reportSysRSyslog(self):
        '''
        ConfigureLogging.reporSysRsyslog reports on the logging facilities,
        the log files, and the logging daemons of syslog and rsyslog
        @author: dwalker
        @return: bool - True or False upon success
        '''
        debug = ""
        compliant = True
        self.directories.append("/var/log/messages")
        specs = ["rotate 4",
                 "weekly",
                 "missingok",
                 "notifempty",
                 "compress",
                 "delaycompress",
                 "sharedscripts",
                 "postrotate",
                 "/bin/kill -HUP `/bin/cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true",
                 "/bin/kill -HUP `/bin/cat /var/run/syslog.pid 2> /dev/null` 2> /dev/null || true",
                 "/bin/kill -HUP `/bin/cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true",
                 "endscript"]
        self.expression = "\s*/var/log/user\s+/var/log/daemon\s+/var/log/auth\s+/var/log/kern\s+/var/log/lpr\s+/var/log/syslog\s+/var/log/cron\s+/var/log/maillog\s+/var/log/local\s+/var/log/ftp\s+/var/log/messages\s*\{\s*" + \
            "\s*rotate 4\s+weekly\s+missingok\s+notifempty\s+compress\s+delaycompress\s+sharedscripts\s+postrotate\s+" + \
            "/bin/kill -HUP `/bin/cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null \|\| true\s+" + \
            "/bin/kill -HUP `/bin/cat /var/run/syslog.pid 2> /dev/null` 2> /dev/null \|\| true\s+" + \
            "/bin/kill -HUP `/bin/cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null \|\| true\s+" + \
            "endscript\s*\}"
#        opensuse 13 and later uses systemd-logger instead of rsyslog
#        this logging daemon doesn't have the functionality we need so
#        we remove it firsthand and install rsyslog in the fix.
        if re.search("opensuse", self.environ.getostype().lower()):
            if self.ph.check("systemd-logger"):
                compliant = False
#        check if rsyslog is installed and turned on
        if self.ph.check("rsyslog"):
            self.logs["rsyslog"] = True
            if not self.checkSysRsyslogOn():
                self.detailedresults += "Rsyslog is installed but not on\n"
                compliant = False

#        check if syslog is installed and turned on if rsyslog not installed
        elif self.ph.check("syslog"):
            self.logs["syslog"] = True
            specs.remove("/bin/kill -HUP `/bin/cat /var/run/rsyslogd.pid 2> \
/dev/null` 2> /dev/null || true',")
            if not self.checkSysRsyslogOn():
                self.detailedresults += "Syslog is installed but not on\n"
                compliant = False

#        there is no logging daemon installed
        else:
            compliant = False
            self.detailedresults += "There is no logging daemon installed\n"

        # check if all necessary dirs are present and correct perms
        for item in self.directories:
            if not os.path.exists(item):
                self.detailedresults += "All required logging files \
aren't present\n"
                compliant = False
                break
            else:
                if self.ph.manager == "apt-get":
                    if re.search("debian", self.environ.getostype().lower()):
                        distroowner = "root"
                    elif re.search("ubuntu", self.environ.getostype().lower()):
                        distroowner = "syslog"
                    statdata = os.stat(item)
                    mode = stat.S_IMODE(statdata.st_mode)
                    ownergrp = getUserGroupName(item)
                    owner = ownergrp[0]
                    group = ownergrp[1]
                    if mode != 384:
                        compliant = False
                        self.detailedresults += "permissions on " + item + \
                            "aren't 600\n"
                        debug = "permissions on " + item + " aren't 600\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                    if owner != distroowner:
                        compliant = False
                        self.detailedresults += "Owner of " + item + \
                            " isn't syslog\n"
                        debug = "Owner of " + item + \
                            " isn't syslog\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                    if group != "adm":
                        compliant = False
                        self.detailedresults += "Group of " + item + \
                            " isn't adm\n"
                        debug = "Group of " + item + \
                            " isn't adm\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                elif not checkPerms(item, [0, 0, 384], self.logger):
                    self.detailedresults += "Permissions are not correct on \
all required logging files"
                    compliant = False
                    break
        if not os.path.exists(self.bootlog):
            self.detailedresults += "bootlog file is not present\n"
            compliant = False
        elif not checkPerms(self.bootlog, [0, 0, 420], self.logger):
            self.detailedresults += "Permissions are not correct on \
bootlog file\n"
            compliant = False
        if self.logs["rsyslog"]:
            if self.ph.manager == "apt-get":
                self.logpath = "/etc/rsyslog.d/50-default.conf"
            else:
                self.logpath = "/etc/rsyslog.conf"
        elif self.logs["syslog"]:
            self.logpath = "/etc/syslog.conf"
        else:
            self.logpath = "/etc/rsyslog.conf"
        # check if correct contents of rsyslog.conf file
        if os.path.exists(self.logpath):
            if not checkPerms(self.logpath, [0, 0, 420], self.logger):
                self.detailedresults += "permissions aren't correct on log \
daemon config file: " + self.logpath
                compliant = False
            contents = readFile(self.logpath, self.logger)
            for key in self.logfiles:
                found = False
                for item in contents:
                    if re.search("^#", item.strip()) or re.match("^\s*$",
                                                                 item.strip()):
                        continue
                    line = item.strip()
                    line = re.sub("(\s)+", " ", line)
                    temp = line.split()
                    try:
                        if temp[0].strip() == key:
                            if self.logfiles[key] == temp[1].strip():
                                found = True
                                break
                    except IndexError:
                        debug = traceback.format_exc() + "\n"
                        debug += "Index out of range\n"
                        debug += "from line: " + line + "\n"
                        compliant = False
                if not found:
                    self.config.append(key + "\t\t\t" + self.logfiles[key] +
                                       "\n")
                    self.detailedresults += key + " and value " + self.logfiles[key] + \
                        " not found in " + self.logpath + "\n"
                    compliant = False
        else:
            self.detailedresults += self.logpath + "doesn\'t exist\n"
            for key in self.logfiles:
                self.config.append(key + "\t\t\t" + self.logfiles[key] + "\n")
            compliant = False
        self.logger.log(LogPriority.DEBUG, debug)

        # check if correct contents of logrotate file exist
        self.logrotpath = self.checkLogRotation()
        if self.logrotpath:
            if os.path.exists(self.logrotpath):
                if re.search("Red Hat", self.environ.getostype()) and \
                        re.search("^6", self.environ.getosver()):
                    statdata = os.stat(self.logrotpath)
                    mode = stat.S_IMODE(statdata.st_mode)
                    ownergrp = getUserGroupName(self.logrotpath)
                    owner = ownergrp[0]
                    group = ownergrp[1]
                    if mode != 420:
                        self.detailedresults += "permissions on " + \
                            self.logrotpath + " aren't 644\n"
                        debug = "permissions on " + self.logrotpath + " aren't 644\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        compliant = False
                    if owner != "root":
                        self.detailedresults += "Owner of " + self.logrotpath + \
                            " isn't root\n"
                        debug = "Owner of " + self.logrotpath + " isn't root\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        compliant = False
                    if group != "sys":
                        self.detailedresults += "Group owner of " + \
                            self.logrotpath + " isn't sys\n"
                        debug = "Group owner of " + self.logrotpath + " isn't sys\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        compliant = False
                elif not checkPerms(self.logrotpath, [0, 0, 420], self.logger):
                    self.detailedresults += "permissions aren't correct on log \
    rotation config file: " + self.logrotpath
                    compliant = False

                contents = readFile(self.logrotpath, self.logger)
                contentstring = ""

                for line in contents:
                    contentstring += line
                if not re.search(self.expression, contentstring):
                    self.detailedresults = "logrotate file doesn't " + \
                        "contain the correct log contents\n"
                    compliant = False
        return compliant

###############################################################################

    def fixSysRsyslog(self):
        '''corrects the syslog/rsyslog files and also logrotation files.
        Some failed actions may result in a change of the success variable's
        value which is ultimately returned at the end of the method and some
        failed actions may result in an immediate False return due to
        inability to continue with the rest of the fix.  Appropriate logging
        will occur
        @author: dwalker
        @return: bool - True or False upon success
        '''
        universal = "\n#The following lines were added by stonix\n"
        self.detailedresults = ""
        success = True
        specs = ["rotate 4",
                 "weekly",
                 "missingok",
                 "notifempty",
                 "compress",
                 "delaycompress",
                 "sharedscripts",
                 "postrotate",
                 "endscript",
                 "/bin/kill -HUP `/bin/cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true",
                 "/bin/kill -HUP `/bin/cat /var/run/syslog.pid 2> /dev/null` 2> /dev/null || true",
                 "/bin/kill -HUP `/bin/cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true"]
        addon = "/var/log/user /var/log/daemon /var/log/auth /var/log/kern /var/log/lpr /var/log/syslog /var/log/cron /var/log/maillog /var/log/local /var/log/ftp /var/log/messages{\n" + \
            "rotate 4\nweekly\nmissingok\nnotifempty\ncompress\ndelaycompress\nsharedscripts\npostrotate\n" + \
            "/bin/kill -HUP `/bin/cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true\n" + \
            "/bin/kill -HUP `/bin/cat /var/run/syslog.pid 2> /dev/null` 2> /dev/null || true\n" + \
            "/bin/kill -HUP `/bin/cat /var/run/rsyslogd.pid 2> /dev/null` 2> /dev/null || true\n" + \
            "endscript\n}\n"
#-----------------------------------------------------------------------------#
        #this should actually remove systemd-logger and automatically install
        #rsyslog.  For opensuse systems only
        if re.search("opensuse", self.environ.getostype().lower()):
            if self.ph.check("systemd-logger"):
                if not self.ph.remove("systemd-logger"):
                    debug = "Couldn't remove systemd-logger\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    success = False
                else:
                    self.logs["rsyslog"] = True
                    self.logrotpath = self.checkLogRotation()
                    self.logd = "rsyslog"
        # check if rsyslog package is installed
        if not self.ph.check("rsyslog"):
            if self.ph.checkAvailable("rsyslog"):
                if not self.ph.install("rsyslog"):
                    debug = "Couldn\'t install rsyslog package\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    success = False
                else:
                    self.logs["rsyslog"] = True
                    self.logrotpath = self.checkLogRotation()
                    self.logd = "rsyslog"
            elif not self.ph.check("syslog"):
                if self.ph.checkAvailable("syslog"):
                    if not self.ph.install("syslog"):
                        debug = "Couldn\'t install syslog package\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        success = False
                    else:
                        self.logs["syslog"] = True
                        self.logrotpath = self.checkLogRotation()
                        self.logd = "syslog"
                        specs.remove("/bin/kill -HUP `/bin/cat " + \
                        "/var/run/rsyslogd.pid 2> /dev/null` 2> " + \
                        "/dev/null || true")
                else:
                    debug = "There is no logging daemon available\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    success = False
#-----------------------------------------------------------------------------#
        # check if all necessary dirs are present and correct perms
        if re.search("debian", self.environ.getostype().lower()):
            distroowner = "root"
        elif re.search("ubuntu", self.environ.getostype().lower()):
            distroowner = "syslog"
        for item in self.directories:
            if os.path.exists(item):
                if self.ph.manager == "apt-get":
                    statdata = os.stat(item)
                    mode = stat.S_IMODE(statdata.st_mode)
                    ownergrp = getUserGroupName(item)
                    retval = checkUserGroupName(ownergrp, distroowner, "adm",
                                                mode, 384, self.logger)
                    if isinstance(retval, list):
                        origuid = statdata.st_uid
                        origgid = statdata.st_gid
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        event = {"eventtype": "perm",
                                 "startstate": [origuid, origgid, mode],
                                 "endstated": [retval[0], retval[1], 384],
                                 "filepath": item}
                        self.statechglogger.recordchgevent(myid, event)
                        os.chown(item, retval[0], retval[1])
                        os.chmod(item, 384)
                    elif not retval:
                        self.detailedresults += "There was a problem getting permissions on " + \
                            item + "\n"
                        success = False
                elif not checkPerms(item, [0, 0, 384], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(item, [0, 0, 384], self.logger,
                                    self.statechglogger, myid):
                        debug = "Unable to set " + "permissions on " + item + "\n"
                        self.logger.log(LogPriority.DEBUG, debug)
                        success = False
            else:
                if not createFile(item, self.logger):
                    debug = "Unable to create necessary log file: " + item + \
                        "\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    success = False
                else:
                    self.detailedresults += "Successfully created file: " + \
                        item + "\n"
                    if self.ph.manager == "apt-get":
                        statdata = os.stat(item)
                        mode = stat.S_IMODE(statdata.st_mode)
                        ownergrp = getUserGroupName(item)
                        retval = checkUserGroupName(ownergrp, distroowner,
                                                    "adm", mode, 384, self.logger)
                        if isinstance(retval, list):
                            os.chown(item, retval[0], retval[1])
                            os.chmod(item, 384)
                    else:
                        os.chown(item, 0, 0)
                        os.chmod(item, 384)
                    resetsecon(item)
        if os.path.exists(self.bootlog):
            if not checkPerms(self.bootlog, [0, 0, 420], self.logger):
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                if not setPerms(self.bootlog, [0, 0, 420], self.logger,
                                self.statechglogger, myid):
                    debug = "Unable to set " + "permissions on " + self.bootlog + "\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    success = False
        elif not createFile(self.bootlog, self.logger):
            debug = "Unable to create necessary log file: " + self.bootlog + "\n"
            self.logger.log(LogPriority.DEBUG, debug)
            success = False
        else:
            self.detailedresults += "Successfully created file: " + \
                self.bootlog + "\n"
            os.chown(self.bootlog, 0, 0)
            os.chmod(self.bootlog, 420)
            resetsecon(self.bootlog)
#-----------------------------------------------------------------------------#
        # correct rsyslog/syslog file
        if self.config:
            if not os.path.exists(self.logpath):
                if not createFile(self.logpath, self.logger):
                    debug = "Unable to create missing log daemon config " + \
                        "file: " + self.logpath + "\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    return False
                else:
                    self.created1 = True
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    event = {"eventtype": "creation",
                             "filepath": self.logpath}
                    self.statechglogger.recordchgevent(myid, event)
                    debug = "successfully create log daemon config file: " + \
                        self.logpath + "\n"
                    self.logger.log(LogPriority.DEBUG, debug)
                    if not checkPerms(self.logpath, [0, 0, 420], self.logger):
                        if not setPerms(self.logpath, [0, 0, 420], self.logger):
                            debug = "Unable to set " + \
                                "permissions on " + self.logpath + "\n"
                            self.logger.log(LogPriority.DEBUG, debug)
                            success = False
                        resetsecon(self.logpath)
        tempstring = ""
        tmpfile = self.logpath + '.tmp'
        if not checkPerms(self.logpath, [0, 0, 420], self.logger):
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            if not setPerms(self.logpath, [0, 0, 420], self.logger,
                            self.statechglogger, myid):
                debug = "Unable to set permissions on " + \
                    self.logpath + "\n"
                self.logger.log(LogPriority.DEBUG, debug)
                success = False
        contents = readFile(self.logpath, self.logger)
        for item in contents:
            tempstring += item
        tempstring += universal
        for item in self.config:
            tempstring += item
        if not writeFile(tmpfile, tempstring, self.logger):
            return False
        if not self.created1:
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            event = {'eventtype': 'conf',
                     'filepath': self.logpath}
            self.statechglogger.recordchgevent(myid, event)
            self.statechglogger.recordfilechange(self.logpath, tmpfile, myid)
        os.rename(tmpfile, self.logpath)
        os.chown(self.logpath, 0, 0)
        os.chmod(self.logpath, 420)
        resetsecon(self.logpath)
#-----------------------------------------------------------------------------#
        # correct log rotate file

        #if logrotation file doesn't exist, create it, record createfile event
        if not os.path.exists(self.logrotpath):
            if not createFile(self.logrotpath, self.logger):
                debug = "Unable to create missing log rotation config " + \
                    "file: " + self.logrotpath + "\n"
                self.logger.log(LogPriority.DEBUG, debug)
                return False
            else:
                self.created2 = True
                self.detailedresults += "successfully created log \
rotation config file: " + self.logrotpath + "\n"
                event = {"eventtype": "creation",
                         "filepath": self.logrotpath}
                self.statechglogger.recordchgevent(myid, event)
        #if system is redhat 6 we need to make sure the group owner is sys
        if re.search("^Red Hat*", self.environ.getostype().strip()) and \
                re.search("^6*", self.environ.getosver()):
            gid = grp.getgrnam("sys")[2]
            statdata = os.stat(self.logrotpath)
            mode = stat.S_IMODE(statdata.st_mode)
            ownergrp = getUserGroupName(self.logrotpath)
            owner = ownergrp[0]
            group = ownergrp[1]
            if mode != 420 or owner != "root" or group != "sys":
                origuid = statdata.st_uid
                origgid = statdata.st_gid
                if grp.getgrnam("sys")[2]:
                    if not self.created2:
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        event = {"eventtype": "perm",
                                 "startstate": [origuid, origgid, mode],
                                 "endstate": [0, gid, 420],
                                 "filepath": self.logrotpath}
                        self.statechglogger.recordchgevent(myid, event)
                    os.chmod(self.logrotpath, 420)
                    os.chown(self.logrotpath, 0, gid)
                    resetsecon(self.logrotpath)
                else:
                    success = False
                    debug = "Unable to determine the id " + \
                        "number of sys group.  Will not change " + \
                        "permissions on " + self.logrotpath + " file\n"
                    self.logger.log(LogPriority.DEBUG, debug)
        elif not checkPerms(self.logrotpath, [0, 0, 420], self.logger):
            if not setPerms(self.logrotpath, [0, 0, 420], self.logger):
                debug = "Unable to set " + "permissions on " + self.logrotpath + "\n"
                self.logger.log(LogPriority.DEBUG, debug)
                success = False
        contentstring = ""
        contents = readFile(self.logrotpath, self.logger)
        for line in contents:
            contentstring += line
        if not re.search(self.expression, contentstring):
            contentstring += addon
        tmpfile = self.logrotpath + ".tmp"
        if not writeFile(tmpfile, contentstring, self.logger):
            return False
        if not self.created2:
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            event = {"eventtype": "conf",
                     "filepath": self.logrotpath}
            self.statechglogger.recordchgevent(myid, event)
            self.statechglogger.recordfilechange(self.logrotpath, tmpfile, myid)
        os.rename(tmpfile, self.logrotpath)
        if re.search("^Red Hat", self.environ.getostype().strip()) and \
                re.search("^6", self.environ.getosver()):
            os.chown(self.logrotpath, 0, gid)
        else:
            os.chown(self.logrotpath, 0, 0)
        os.chmod(self.logrotpath, 420)
        resetsecon(self.logrotpath)
        if not self.sh.reloadservice("rsyslog"):
            debug = "Unable to restart the log daemon part 1\n"
            self.logger.log(LogPriority.DEBUG, debug)
        if not self.ch.getReturnCode() != "0":
            debug = "Unable to restart the log daemon part 2\n"
            self.logger.log(LogPriority.DEBUG, debug)
        return success

###############################################################################

    def reportSol(self, logpath, logrotpath):
        '''report method for solaris Operating systems'''
        specs = {'-C': '10',
                 '-p': '1w',
                 '-A': '14w'}
        ifdef = False
        compliant = True
        contents, contents2 = [], []
#-----------------------------------------------------------------------------#
        # check if all necessary dirs are present and correct perms
        for item in self.directories:
            if not os.path.exists(item):
                self.detailedresults += item + " doesn\'t exist\n"
                compliant = False
            else:
                if not checkPerms(item, [0, 0, 384], self.logger):
                    compliant = False
#-----------------------------------------------------------------------------#
        # check if correct contents of rsyslog.conf file
        if os.path.exists(logpath):
            if not checkPerms(logpath, [0, 0, 420], self.logger):
                compliant = False
            contents = readFile(logpath, self.logger)
            if contents:
                iterator = 0
                for line in contents:
                    if re.match('^ifdef', line.strip()):
                        ifdef = True
                        contents2 = contents[iterator:]
                        contents2.pop(0)
                        for log in self.logfiles:
                            found = False
                            for item in contents2:
                                if re.match('^#', item) or re.match('^\s*$',
                                                                    item):
                                    continue
                                if re.match('^\)$', item.strip()):
                                    break
                                if re.search(re.escape(log), item):
                                    temp = re.sub('(\s)+', " ", item)
                                    temp = temp.split()
                                    if temp[1] == self.logfiles[log]:
                                        found = True
                                        break
                                elif re.search('\)$', item.strip()):
                                    break
                            if not found:
                                compliant = False
                                string = log + '\t\t\t\t' + self.logfiles[log] + "\n"
                                self.config.append(string)
                    else:
                        iterator += 1
                        continue
            if not ifdef:
                for log in self.logfiles:
                    string = log + '\t\t\t\t' + self.logfiles[log] + "\n"
                    self.config.append(string)
        else:
            self.detailedresults += logpath + " file doesn\'t exist\n"
            for key in self.logfiles:
                self.config.append(key + "\t\t\t" + self.logfiles[key] + "\n")
            compliant = False
#-----------------------------------------------------------------------------#
        # check if correct contents of logrotate file
        if os.path.exists(logrotpath):
            if not checkPerms(logrotpath, [0, 0, 420], self.logger):
                compliant = False
            contents = readFile(logrotpath, self.logger)
            for directory in self.directories:
                dirfound = False
                missingspecs = {}
                for line in contents:
                    if re.match('^#', line.strip()) or re.match('^\s*$', line):
                        continue
                    elif re.match('^' + directory, line.strip()):
                        dirfound = True
                        temp = re.sub('(\s)+', " ", line)
                        temp = temp.split()
                        temp.pop(0)
                        for spec in specs:
                            iterator = 0
                            found = False
                            for item in temp:
                                if re.match('^' + spec, item.strip()):
                                    try:
                                        if temp[iterator + 1] == specs[spec]:
                                            iterator += 1
                                            found = True
                                            continue
                                        else:
                                            compliant = False
                                            found = False
                                            break
                                    except IndexError:
                                        info = "Index out of range\n"
                                        self.logger.log(LogPriority.INFO, info)
                                        break
                                else:
                                    iterator += 1
                            if not found:
                                missingspecs[spec] = specs[spec]
                        if missingspecs:
                            self.missinglogrot[directory] = missingspecs
                if not dirfound:
                    compliant = False
                    for spec in specs:
                        missingspecs[spec] = specs[spec]
                    self.missinglogrot[directory] = missingspecs
        else:
            self.detailedresults += logrotpath + "doesn\'t exist"
            for directory in self.directories:
                self.missinglogrot[directory] = specs
            compliant = False
        return compliant

##############################################################################

    def fixSol(self, logpath, logrotpath):
        ifdef = False
        universal = "\n#The following lines were added by stonix\n"
        success = True
#-----------------------------------------------------------------------------#
        # check if all necessary dirs are present and correct perms
        for item in self.directories:
            if os.path.exists(item):
                if not checkPerms(item, [0, 0, 384], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(item, [0, 0, 384], self.logger,
                                                    self.statechglogger, myid):
                        success = False
            else:
                if not createFile(item, self.logger):
                    self.detailedresults += "Unable to create necessary \
log file: " + item + "\n"
                    success = False
                else:
                    self.detailedresults += "Successfully created log file: \
" + item
                    os.chown(item, 0, 0)
                    os.chmod(item, 384)
                    resetsecon(item)
#-----------------------------------------------------------------------------#
        if self.config:
            tempstring = ""
            tmpfile = logpath + ".tmp"
            if not os.path.exists(logpath):
                if not createFile(logpath, self.logger):
                    self.detailedresults += "Unable to create log daemon \
file: " + logpath + "\n"
                    return False
                elif not checkPerms(logpath, [0, 0, 420], self.logger):
                    if not setPerms(logpath, [0, 0, 420], self.logger):
                        success = False
            else:
                if not checkPerms(logpath, [0, 0, 420], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(logpath, [0, 0, 420], self.logger,
                                                    self.statechglogger, myid):
                        success = False
            contents = readFile(logpath, self.logger)
            iterator = 0
            if contents:
                for item in contents:
                    if re.match('^ifdef', item.strip()):
                        ifdef = True
                        tempstring += item
                        for item2 in self.config:
                            tempstring += item2
                        contents2 = contents[iterator:]
                        contents2.pop(0)
                        for item2 in contents2:
                            tempstring += item2
                        break
                    else:
                        iterator += 1
                        tempstring += item
            if not ifdef:
                tempstring = "ifdef(`LOGHOST', ,\n"
                for item in self.config:
                    tempstring += item
                tempstring += ")"
            if not writeFile(tmpfile, tempstring, self.logger):
                return False
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            event = {"eventtype": "conf",
                     "filepath": logpath}
            self.statechglogger.recordchgevent(myid, event)
            self.statechglogger.recordfilechange(logpath, tmpfile, myid)
            os.rename(tmpfile, logpath)
            os.chown(logpath, 0, 0)
            os.chmod(logpath, 420)
            resetsecon(logpath)
#-----------------------------------------------------------------------------#
        if self.missinglogrot:
            tempstring = ""
            tmpfile = logrotpath + ".tmp"
            if not createFile(logrotpath, self.logger):
                self.detailedresults += "Unable to create log rotation file: \
" + logrotpath + "\n"
                return False
            elif not checkPerms(logrotpath, [0, 0, 420], self.logger):
                if not setPerms(logrotpath, [0, 0, 420], self.logger):
                    success = False
                else:
                    if not checkPerms(logrotpath, [0, 0, 420], self.logger):
                        self.iditerator += 1
                        myid = iterate(self.iditerator, self.rulenumber)
                        if not setPerms(logrotpath, [0, 0, 420], self.logger,
                                                    self.statechglogger, myid):
                            success = False
            contents = readFile(logrotpath, self.logger)
            if contents:
                for line in contents:
                    found = False
                    if re.match('^#', line.strip()) or re.match('^\s*$', line):
                        tempstring += line
                        continue
                    for key in self.missinglogrot:
                        if re.search(key, line):
                            string = key + " "
                            string2 = ""
                            temp = re.sub('(\s)+', " ", line)
                            temp = temp.split(" ")
                            temp.pop(0)
                            specs = self.missinglogrot[key]
                            for spec in specs:
                                iterator = 0
                                for item2 in temp:
                                    if spec == item2.strip():
                                        temp.pop(iterator)
                                        temp.pop(iterator)
                                        # iterator = iterator + 1
                                    else:
                                        iterator = iterator + 1
                            for entry in temp:
                                string += entry + " "

                            for spec in specs:
                                string2 += spec + " " + specs[spec] + " "
                            tempstring += string + string2
                            del self.missinglogrot[key]
                            break
                    if not found:
                        tempstring += line
                    tempstring += universal

            for key in self.missinglogrot:
                string = key + " "
                specs = self.missinglogrot[key]
                for spec in specs:
                    string += spec + " " + specs[spec] + " "
                tempstring += string + "\n"

            if not writeFile(tmpfile, tempstring, self.logger):
                return False
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            event = {"eventtype": "conf",
                     "filepath": logrotpath}
            self.statechglogger.recordchgevent(myid, event)
            self.statechglogger.recordfilechange(logrotpath, tmpfile, myid)
            os.rename(tmpfile, logrotpath)
            os.chown(logrotpath, 0, 0)
            os.chmod(logrotpath, 420)
            resetsecon(logrotpath)
#-----------------------------------------------------------------------------#
        # restart log daemon
        if not self.sh.reloadservice(self.service):
            success = False
        return success

###############################################################################

    def reportFreebsd(self, logpath, logrotpath):
        compliant = True
        self.missinglogrot = False
        debug = ""
#-----------------------------------------------------------------------------#
        # check if all necessary dirs are present and correct perms
        for item in self.directories:
            if not os.path.exists(item):
                self.detailedresults += item + " doesn\'t exist\n"
                compliant = False
            else:
                if not checkPerms(item, [0, 0, 384], self.logger):
                    compliant = False
#-----------------------------------------------------------------------------#
        # check if correct contents of syslog.conf file
        if os.path.exists(logpath):
            if not checkPerms(logpath, [0, 0, 420], self.logger):
                compliant = False
            contents = readFile(logpath, self.logger)
            if contents:
                for key in self.logfiles:
                    found = False
                    for item in contents:
                        if re.search("^\#", item) or re.match('^\s*$', item):
                            continue
                        else:
                            line = item.strip()
                            line = re.sub('(\s)+', " ", line)
                            temp = line.split()
                            if temp[0].strip() == key:
                                if self.logfiles[key] == temp[1].strip():
                                    found = True
                                    break
                    if not found:
                        self.config.append(key + "\t\t\t" + self.logfiles[key] + "\n")
                        compliant = False
        else:
            self.detailedresults += logpath + "doesn\'t exist\n"
            for key in self.logfiles:
                self.config.append(key + "\t\t\t" + self.logfiles[key] + "\n")
            compliant = False
#-----------------------------------------------------------------------------#
        # check /etc/newsyslog.conf file
        if os.path.exists(logrotpath):
            if not checkPerms(logrotpath, [0, 0, 420], self.logger):
                compliant = False
            contents = readFile(logrotpath, self.logger)
            if contents:
                for directory in self.directories:
                    found = False
                    for line in contents:
                        if re.match('^#', line.strip()) or re.match('^\s*$', line):
                            continue
                        if re.search('^' + directory, line.strip()):
                            found = True
                            line = re.sub('(\s)+', " ", line)
                            temp = line.split()
                            temp.pop(0)
                            try:
                                if re.search(':', temp[0]):
                                    temp.pop(0)
                                # if re.match('[1-7][0-7]{2}', temp[0]):#for the mode
                                if re.match("[0-7][0-7][0-7]", temp[0]):
                                    if temp[0] != "600":
                                        self.missinglogrot = True
                                        compliant = False
                                    temp.pop(0)
                                else:
                                    self.missinglogrot = True
                                if re.match('[0-9]{1,4}', temp[0]):  # for the count
                                    if temp[0] != "4":
                                        self.missinglogrot = True
                                        compliant = False
                                    temp.pop(0)
                                else:
                                    self.missinglogrot = True
                                if re.match('[*]{1}|[0-9]{1,4}', temp[0]):
                                    if temp[0] != "*":
                                        self.missinglogrot = True
                                        compliant = False
                                    temp.pop(0)
                                else:
                                    self.missinglogrot = True
                                if re.match('^[@$*]{1}([A-Z]|[0-9])*', temp[0]):
                                    if temp[0] != "$W0D23":
                                        self.missinglogrot = True
                                        compliant = False
                                else:
                                    self.missinglogrot = True
                            except IndexError:
                                raise
                            except Exception:
                                debug += traceback.format_exc() + "\n"
                                debug += "Index out of range\n"
                    if not found:
                        self.missinglogrot = True
                        compliant = False
        else:
            self.missinglogrot = True
            self.detailedresults += logrotpath + " doesn\'t exist"
            compliant = False
        return compliant

###############################################################################

    def fixFreebsd(self, logpath, logrotpath):
        '''Assumptions: for logrotate file, we assume newsyslog.conf doesn't
        contain duplicate entries for files to be logrotated and that the 5
        mandatory fields are actually present(filename,mode,count,size,when)
        If either of these cases apply to the system, the user must delete or
        correct the line in question'''
        universal = "\n#The following lines were added by stonix\n"
        success = True
        debug = ""
        # create and/or correct perms on missing log files
        for item in self.directories:
            if os.path.exists(item):
                if not checkPerms(item, [0, 0, 384], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(item, [0, 0, 384], self.logger,
                                    self.statechglogger, myid):
                        success = False
            else:
                if not createFile(item, self.logger):
                    self.detailedresults += "Unable to create necessary log \
file: " + item + "\n"
                    success = False
                else:
                    self.detailedresults += "Successfully created log file: \
" + item + "\n"
                    os.chown(item, 0, 0)
                    os.chmod(item, 384)
                    resetsecon(item)
#-----------------------------------------------------------------------------#
        if self.config:
            tempstring = ""
            tmpfile = logpath + '.tmp'
            if not os.path.exists(logpath):
                if not createFile(logpath, self.logger):
                    self.detailedresults += "unable to create the log file: \
" + logpath + "\n"
                elif not checkPerms(logpath, [0, 0, 420], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(logpath, [0, 0, 420], self.logger,
                                    self.statechglogger, myid):
                        success = False
            else:
                if not checkPerms(logpath, [0, 0, 420], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(logpath, [0, 0, 420], self.logger,
                                    self.statechglogger, myid):
                        success = False
            if os.path.exists(logpath):
                contents = readFile(logpath, self.logger)
                if contents:
                    for item in contents:
                        tempstring += item
                    tempstring += universal
                    for item in self.config:
                        tempstring += item
                    if not writeFile(tmpfile, tempstring, self.logger):
                        return False
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    event = {"eventtype": "conf",
                             "filepath": logpath}
                    self.statechglogger.recordchgevent(myid, event)
                    self.statechglogger.recordfilechange(logpath, tmpfile,
                                                         myid)
                    os.rename(tmpfile, logpath)
                    os.chown(logpath, 0, 0)
                    os.chmod(logpath, 420)
                    resetsecon(logpath)
#-----------------------------------------------------------------------------#
        if self.missinglogrot:
            tempstring = ""
            tmpfile = logrotpath + '.tmp'
            if not os.path.exists(logrotpath):
                if not createFile(logrotpath, self.logger):
                    self.detailedresults += "unable to create log rotation \
file: " + logrotpath + "\n"
                elif not checkPerms(logrotpath, [0, 0, 420], self.logger):
                    if not setPerms(logrotpath, [0, 0, 420], self.logger):
                        success = False
            else:
                if not checkPerms(logrotpath, [0, 0, 420], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(logrotpath, [0, 0, 420], self.logger,
                                    self.statechglogger, myid):
                        success = False
            found = False
            if os.path.exists(logrotpath):
                contents = readFile(logrotpath, self.logger)
                if contents:
                    for line in contents:
                        if re.match('^#', line.strip()) or re.match('^\s*$',
                                                                    line):
                            tempstring += line
                            continue
                        for directory in self.directories:
                            badformat = False
                            found = False
                            if re.match('^' + directory, line.strip()):
                                found = True
                                string = ""
                                self.directories.remove(directory)
                                line = re.sub('(\s)+', " ", line)
                                temp = line.split()
                                string += temp.pop(0) + " "
                                try:
                                    if re.search(':', temp[0]):
                                        string += temp.pop(0) + " "
                                    else:
                                        string += '\t\t\t'
                                    # if re.match('[1-7][0-7]{2}',temp[0]):
                                    if re.match("[0-7][0-7][0-7]", temp[0]):
                                        if temp[0] != "600":
                                            string += "600  "
                                            temp.pop(0)
                                        else:
                                            string += temp.pop(0) + "  "
                                    else:
                                        badformat = True
                                        break
                                    if re.match('[0-9]{1,3}', temp[0]):
                                        if temp[0] != "4":
                                            string += "4     "
                                            temp.pop(0)
                                        else:
                                            string += temp.pop(0) + "    "

                                    else:
                                        badformat = True
                                        break
                                    if re.match('[*]{1}|[0-9]{1,3}', temp[0]):
                                        if temp[0] != "*":
                                            string += "*    "
                                            temp.pop(0)
                                        else:
                                            string += temp.pop(0) + "    "
                                    else:
                                        badformat = True
                                        break
                                    if re.match('^[@$*]{1}([A-Z]|[0-9])*',
                                                temp[0]):
                                        if temp[0] != "$W0D23":
                                            string += "$W0D23 "
                                            temp.pop(0)
                                        else:
                                            string += temp.pop(0) + " "
                                    else:
                                        badformat = True
                                        break
                                except IndexError:
                                    debug += traceback.format_exc() + "\n"
                                    debug += " Index out of range\n"
                                    self.logger.log(LogPriority.DEBUG, debug)
                                    raise
                                try:
                                    if temp[0]:  # if flags value exists
                                        string += temp.pop(0) + " "
                                    if temp[0]:  # if /pid_file exists
                                        string += temp.pop(0) + " "
                                    if temp[0]:  # if sig_num exists
                                        string += temp.pop(0) + " "
                                except IndexError:
                                    debug += traceback.format_exc() + "\n"
                                    debug += "Index out of range but that's ok \
because these values are optional\n"
                                    self.logger.log(LogPriority.DEBUG, debug)
                                    break
                                tempstring += string + "\n"
                                badformat = False
                                found = True
                        if badformat:
                            tempstring += directory + "\t\t\t\t" + "600  " + "4     " + "*    " + "$W0D23" + "\n"
                        elif not found:
                            tempstring += line
                if self.directories:
                    for directory in self.directories:
                        tempstring += directory + "\t\t\t\t" + "600  " + "4     " + "*    " + "$W0D23" + "\n"
                if not writeFile(tmpfile, tempstring, self.logger):
                    return False
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "conf",
                         "filepath": logrotpath}
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(logrotpath, tmpfile, myid)
                os.rename(tmpfile, logrotpath)
                os.chown(logrotpath, 0, 0)
                os.chmod(logrotpath, 420)
                resetsecon(logrotpath)
        self.missinglogrot = {}
#-----------------------------------------------------------------------------#
        if not self.checkSysRsyslogOn():
            message = Popen([self.service, "restart"], stdout=PIPE,
                            stderr=PIPE, shell=False)
            while message.poll() is None:
                continue
            if message.poll() != 0:
                self.detailedresults += "Couldn\'t'\ restart syslog daemon\n"
                success = False
        return success

###############################################################################

    def reportMac(self):
        debug = ""
        compliant = RuleKVEditor.report(self, True)
        self.detailedresults += "\n"
        self.macDirs = ["/var/log/cron.log",
                        "/var/log/daemon.log",
                        "/var/log/kern.log",
                        "/var/log/local.log",
                        "/var/log/syslog.log",
                        "/var/log/user.log",
                        "/var/log/stonix.log",
                        "/var/log/system.log",
                        "/var/log/lpr.log",
                        "/var/log/mail.log",
                        "/var/log/install.log",
                        "/var/log/netinfo.log",
                        "/var/log/secure.log"]
        self.logfiles = {"*.*": "/var/log/system.log",
                         "daemon.*": "/var/log/daemon.log",
                         "auth.*": "/var/log/secure.log",
                         "user.*": "/var/log/user.log",
                         "kern.*": "/var/log/kern.log",
                         "lpr.*": "/var/log/lpr.log",
                         "syslog.*": "/var/log/syslog.log",
                         "cron.*": "/var/log/cron.log",
                         "mail,uucp,news.*": "/var/log/mail.log",
                         "local0,local1,local2,local3.*": "/var/log/local.log",
                         "local4,local,local6,local7.*": "/var/log/local.log",
                         "local5.*": "/var/log/stonix.log",
                         "install.*": "/var/log/install.log",
                         "netinfo.*": "/var/log/netinfo.log",
                         "remoteauth,authpriv.*": "/var/log/secure.log",
                         "*.crit": "/dev/console",
                         "auth.info,authpriv.info,mark.info": WINLOG}
        self.asl = ["? [T com.apple.message.domain] store_dir /var/log/DiagnosticMessages",
                    "? [A= Facility com.apple.performance] store_dir /var/log/performance",
                    "? [A= Facility com.apple.eventmonitor] store_dir /var/log/eventmonitor",
                    "? [= Facility authpriv] access 0 80",
                    "? [= Facility remoteauth] [<= Level critical] access 0 80",
                    "? [= Level emergency] broadcast",
                    "? [<= PID 1] store",
                    "? [= Facility internal] ignore",
                    "? [<= Level notice] store",
                    "? [= Facility install] file /var/log/install.log format=bsd",
                    "? [= Facility install] ignore",
                    "? [= Sender kernel] file /var/log/system.log mode=0600 gid=80 format=bsd",
                    "? [<= Level notice] file /var/log/system.log",
                    "? [= Facility auth] [<= Level info] file /var/log/system.log",
                    "? [= Facility authpriv] file /var/log/system.log",
                    "? [= Facility mail] file /var/log/mail.log mode=0644 format=bsd",
                    "? [= Facility com.apple.alf.logging] file /var/log/appfirewall.log]"]
        exist = []
        syslog = "/etc/syslog.conf"
        newsyslog = "/etc/newsyslog.conf"
        aslfile = "/etc/asl.conf"
        service = " /System/Library/LaunchDaemons/com.apple.syslogd.plist"
        servicename = "com.apple.syslogd"
        for path in self.macDirs:
            if not os.path.exists(path):
                compliant = False
                self.detailedresults += path + " logfile doesn't exist\n"

        # if LANLLOGROTATE const is set to none, this is a public environment
        # (not lanl related) so ignore the next bit of code
        if LANLLOGROTATE != None:
            if os.path.exists("/etc/periodic/weekly/" + LANLLOGROTATE):
                compliant = False
                self.detailedresults += "old logrotation file exists\n"

#----------Check /etc/syslog.conf file for correct contents-------------------#
        contents = readFile(syslog, self.logger)
        bad = False
        missing = []
        for log in self.logfiles:
            found = False
            for line in contents:
                if re.search("^#", line.strip()) or re.match("^\s*$", line.strip()):
                    continue
                elif re.search("^" + re.escape(log), line):
                    line = line.strip()
                    line = re.sub("(\s)+", " ", line)
                    temp = line.split()
                    try:
                        if self.logfiles[log] == temp[1].strip():
                            found = True
                            break
                    except IndexError:
                        debug = traceback.format_exc() + "\n"
                        debug += "Index out of range\n"
                        debug += "from line: " + line + "\n"
                        self.logger.log(LogPriority, debug)
                        compliant = False
                        raise
            if found:
                exist.append(log)
            else:
                bad = True
                debug = "didn't find: " + str(log) + " in " + syslog + "\n"
                self.logger.log(LogPriority, debug)
                missing.append(log)
                compliant = False
        if exist:
            for item in exist:
                del self.logfiles[item]
        if bad:
            self.detailedresults += "The following lines were not found in " + \
                syslog + ":\n"
            for item in missing:
                self.detailedresults += str(item) + "\n"
#-------------------Check asl.conf file---------------------------------------#
        bad = False
        exist = []
        missing = []
        contents = readFile(aslfile, self.logger)
        for asl in self.asl:
            found = False
            for line in contents:
                if line.strip() == asl:
                    found = True
                    break
            if found:
                exist.append(asl)
            else:
                bad = True
                debug = "didn't find: " + str(asl) + " in " + aslfile + "\n"
                self.logger.log(LogPriority.DEBUG, debug)
                missing.append(asl)
                compliant = False
        if exist:
            for item in exist:
                self.asl.remove(item)
        if bad:
            self.detailedresults += "The following lines were not found in " + \
                aslfile + ":\n"
            for item in missing:
                self.detailedresults += str(item) + "\n"
#-----------------check newsyslog.conf file-----------------------------------#
        if os.path.exists(newsyslog):
            contents = readFile(newsyslog, self.logger)
            for directory in self.macDirs:
                found = False
                for line in contents:
                    if re.match('^#', line.strip()) or re.match('^\s*$', line):
                        continue
                    if re.search('^' + directory, line.strip()):
                        found = True
                        line = re.sub('(\s)+', " ", line)
                        temp = line.split()
                        temp.pop(0)
                        try:
                            if re.search(':', temp[0]):
                                temp.pop(0)
                            # if re.match('[1-7][0-7]{2}', temp[0]):#for the mode
                            if re.match("[0-7][0-7][0-7]", temp[0]):
                                if temp[0] != "600":
                                    self.missinglogrot = True
                                    compliant = False
                                temp.pop(0)
                            else:
                                self.missinglogrot = True
                            if re.match('[0-9]{1,4}', temp[0]):  # for the count
                                if temp[0] != "4":
                                    self.missinglogrot = True
                                    compliant = False
                                temp.pop(0)
                            else:
                                self.missinglogrot = True
                            if re.match('[*]{1}|[0-9]{1,4}', temp[0]):
                                if temp[0] != "*":
                                    self.missinglogrot = True
                                    compliant = False
                                temp.pop(0)
                            else:
                                self.missinglogrot = True
                            if re.match('^[@$*]{1}([A-Z]|[0-9])*', temp[0]):
                                if temp[0] != "$W0D23":
                                    self.missinglogrot = True
                                    compliant = False
                            else:
                                self.missinglogrot = True
                        except IndexError:
                            debug = "Index out of range\n"
                            self.logger.log(LogPriority.DEBUG, debug)

                if not found:
                    self.missinglogrot = True
                    compliant = False
        if not self.sh.isrunning(service, servicename):
            compliant = False
            self.detailedresults += "syslogd is not running\n"
        if not compliant:
            self.detailedresults += "Log rotation is not correctly " + \
                "set up in " + newsyslog + "\n"
        return compliant

###############################################################################

    def fixMac(self):
        syslog = "/etc/syslog.conf"
        newsyslog = "/etc/newsyslog.conf"
        aslfile = "/etc/asl.conf"
        service = "/System/Library/LaunchDaemons/com.apple.syslogd.plist"
        servicename = "com.apple.syslogd"
        success = RuleKVEditor.fix(self, True)
        debug = ""
        universal = "#The following lines were added by stonix\n"
        for path in self.macDirs:
            if not os.path.exists(path):
                if not createFile(path, self.logger):
                    success = False
                    self.detailedresults += "unsuccessful in creating file: \
" + path + "\n"

        # if the LANLLOGROTATE const is set to none, this is a public environment
        # (not lanl related) so ignore the next bit of code
        if LANLLOGROTATE != None:
            if os.path.exists("/etc/periodic/weekly/" + LANLLOGROTATE):
                os.remove("/etc/periodic/weekly/" + LANLLOGROTATE)
        if os.path.exists(syslog):
            tempstring = ""
            contents = readFile(syslog, self.logger)
            for line in contents:
                if re.search(universal, line):
                    continue
                tempstring += line
            tempstring += universal
            for item in self.logfiles:
                tempstring += item + "\t" + self.logfiles[item] + "\n"
            tmpfile = syslog + ".tmp"
            if writeFile(tmpfile, tempstring, self.logger):
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "conf",
                         "filepath": syslog}
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(syslog, tmpfile, myid)
                os.rename(tmpfile, syslog)
            else:
                success = False
                self.detailedresults += "Unable to write to /etc/syslog\n"
        else:
            success = False
            self.detailedresults += "/etc/syslog does not exist, will not \
attempt to create this file. Please make sure syslog is installed and create \
the file manually\n"
        if os.path.exists(aslfile):
            contents = readFile(aslfile, self.logger)
            tempstring = ""
            for line in contents:
                if re.search(universal, line):
                    continue
                tempstring += line
            tempstring += universal
            for item in self.asl:
                tempstring += item + "\n"
            tmpfile = aslfile + ".tmp"
            if writeFile(tmpfile, tempstring, self.logger):
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "conf",
                         "filepath": aslfile}
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(aslfile, tmpfile, myid)
                os.rename(tmpfile, aslfile)
            else:
                success = False
                self.detailedresults += "Unable to write to /etc/asl.conf\n"
        else:
            success = False
            self.detailedresults += "/etc/asl.conf does not exist, will not \
attempt to create this file.\n"
        if os.path.exists(newsyslog):
            contents = readFile(newsyslog, self.logger)
            if contents:
                tempstring = ""
                for line in contents:
                    if re.match('^#', line.strip()) or re.match('^\s*$', line):
                        tempstring += line
                        continue
                    for directory in self.macDirs:
                        badformat = False
                        found = False
                        if re.match('^' + directory, line.strip()):
                            found = True
                            string = ""
                            self.macDirs.remove(directory)
                            line = re.sub('(\s)+', " ", line)
                            temp = line.split()
                            string += temp.pop(0) + " "
                            try:
                                if re.search(':', temp[0]):
                                    string += temp.pop(0) + " "
                                else:
                                    string += '\t\t\t'
                                if re.match("[0-7][0-7][0-7]", temp[0]):
                                    if temp[0] != "600":
                                        string += "600  "
                                        temp.pop(0)
                                    else:
                                        string += temp.pop(0) + "  "
                                else:
                                    badformat = True
                                    break
                                if re.match('[0-9]{1,3}', temp[0]):
                                    if temp[0] != "4":
                                        string += "4     "
                                        temp.pop(0)
                                    else:
                                        string += temp.pop(0) + "    "

                                else:
                                    badformat = True
                                    break
                                if re.match('[*]{1}|[0-9]{1,3}', temp[0]):
                                    if temp[0] != "*":
                                        string += "*    "
                                        temp.pop(0)
                                    else:
                                        string += temp.pop(0) + "    "
                                else:
                                    badformat = True
                                    break
                                if re.match('^[@$*]{1}([A-Z]|[0-9])*',temp[0]):
                                    if temp[0] != "$W0D23":
                                        string += "$W0D23 "
                                        temp.pop(0)
                                    else:
                                        string += temp.pop(0) + " "
                                else:
                                    badformat = True
                                    break
                            except IndexError:
                                debug = " Index out of range\n"
                                self.logger.log(LogPriority.DEBUG, debug)
                                badformat = True
                            try:
                                if temp[0]:  # if flags value exists
                                    string += temp.pop(0) + " "
                                if temp[0]:  # if /pid_file exists
                                    string += temp.pop(0) + " "
                                if temp[0]:  # if sig_num exists
                                    string += temp.pop(0) + " "
                            except IndexError:
                                debug = "Index out of range but that's ok \
because these values are optional\n"
                                self.logger.log(LogPriority.DEBUG, debug)
                                tempstring += string + "\n"
                                break
                            tempstring += string + "\n"
                            badformat = False
                            found = True
                    if badformat:
                        tempstring += directory + "\t\t\t\t" + "600  " + "4     " + "*    " + "$W0D23" + "\n"
                        self.macDirs.remove(directory)
                    if not found:
                        tempstring += line
            if self.macDirs:
                for directory in self.macDirs:
                    tempstring += directory + "\t\t\t\t" + "600  " + "4     " + "*    " + "$W0D23" + "\n"
            if writeFile(tmpfile, tempstring, self.logger):
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {"eventtype": "conf",
                         "filepath": newsyslog}
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(newsyslog, tmpfile, myid)
                os.rename(tmpfile, newsyslog)
            else:
                success = False
                debug = "Unable to write to /etc/newsyslog.conf\n"
                self.logger.log(LogPriority, debug)
        else:
            success = False
            debug = "/etc/newsyslog.conf does not exist, \
will not attempt to create this file.\n"
            self.logger.log(LogPriority, debug)

        if not self.sh.reloadservice(service, servicename):
            success = False
        return success

###############################################################################

    def checkSysRsyslogOn(self):
        '''checks if rsyslog/syslog daemon is running
        @author: dwalker
        @return: bool'''
        if self.environ.getosfamily() == "solaris" or \
                        re.search("opensuse", self.environ.getostype().lower()):
            ps = "/usr/bin/ps"
        else:
            ps = "/bin/ps"
        message = Popen([ps, '-elf'], stdout=PIPE, stderr=PIPE, shell=False)
        info = message.stdout.readlines()
        for line in info:
            if re.search(self.daemon, line):
                return True
        return False

###############################################################################
    def checkLogRotation(self):
        '''
        checks the path of the log rotation
        @author: dwalker
        @return: string
        '''
        logrotpath = ""
        if self.logs["rsyslog"]:
            if os.path.exists("/etc/logrotate.d/syslog"):
                logrotpath = "/etc/logrotate.d/syslog"
            elif os.path.exists("/etc/logrotate.d/syslog.conf"):
                logrotpath = "/etc/logrotate.d/syslog.conf"
            elif os.path.exists("/etc/logrotate.d/rsyslog"):
                logrotpath = "/etc/logrotate.d/rsyslog"
            elif os.path.exists("/etc/logrotate.d/rsyslog.conf"):
                logrotpath = "/etc/logrotate.d/rsyslog.conf"
            else:
                logrotpath = "/etc/logrotate.d/syslog"
        elif self.logs["syslog"]:
            if os.path.exists("/etc/logrotate.d/syslog"):
                logrotpath = "/etc/logrotate.d/syslog"
            elif os.path.exists("/etc/logrotate.d/syslog.conf"):
                logrotpath = "/etc/logrotate.d/syslog.conf"
            else:
                logrotpath = "/etc/logrotate.d/syslog"
        return logrotpath
