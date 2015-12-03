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
Created on Aug 28, 2012

@author: dwalker
@change: 02/16/2014 ekkehard Implemented self.detailedresults flow
@change: 02/16/2014 ekkehard Implemented isapplicable
@change: 02/16/2014 ekkehard blacklisted darwin seems to mess up OS X
@change: 04/18/2014 dkennel Replaced old-style CI invocation
@change: 2014/07/29 dkennel Removed undefined variables from code. Remnants of old "method"
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
variable.
@change: 2015/04/15 dkennel updated for new isApplicable
@change: 2015/10/07 eball Help text cleanup
@change: 2015/11/09 ekkehard - make eligible of OS X El Capitan
'''
from __future__ import absolute_import
from ..stonixutilityfunctions import resetsecon, iterate, readFile, writeFile
from ..stonixutilityfunctions import checkPerms, setPerms, createFile
from ..rule import Rule
from ..logdispatcher import LogPriority
from ..CommandHelper import CommandHelper
from subprocess import Popen, PIPE, call
from ..KVEditorStonix import KVEditorStonix
import os
import traceback
import re


class NetworkTuning(Rule):

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.logger = logger
        self.rulenumber = 15
        self.cmdhelper = CommandHelper(self.logger)
        self.rulename = "NetworkTuning"
        self.formatDetailedResults("initialize")
        self.mandatory = True
        self.helptext = "This rule configures the system's network stack " + \
            "settings.\nFor Solaris systems, this rule requires a full " + \
            "system reboot to take effect, and may show up as non-compliant " + \
            "until the system is rebooted. Also for Solaris systems, if you " + \
            "have a startup script that configures your network stack, " + \
            "this file should appear in /etc/init.d " + \
            "and, in order to pass compliance, it will check for " + \
            "the existence for a file named S70ndd-nettune. Of course, " + \
            "this may not be the name of your file that controls your " + \
            "network parameter tuning, so the system may fail compliance " + \
            "due to this issue."

        if self.environ.getostype() == "Mac OS X":
            self.networkTuning2 = self.__InitializeNetworkTuning2()
        else:
            self.networkTuning1 = self.__InitializeNetworkTuning1()
            self.networkTuning2 = self.__InitializeNetworkTuning2()
        self.guidance = ["NSA 2.5.1.1", "NSA 2.5.1.2"]
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}
        self.iditerator = 0
        self.rep1success = True
        self.rep2success = True
        self.solarisFor = False
        self.solarisRou = False
        self.missing = []
        self.iditerator = 0
        self.editor = ""
        self.ch = CommandHelper(self.logger)

###############################################################################

    def __InitializeNetworkTuning1(self):
        '''Private method to initialize the configurationitem object for the
        NetworkTuning bool.
        @return: configurationitem object instance'''

        datatype = 'bool'
        key = "NETWORKTUNING1"
        instructions = "Network Parameter Tuning.  You should not need " + \
            "to override this unless you are doing something really weird."
        default = True
        ci = self.initCi(datatype, key, instructions, default)
        return ci

###############################################################################

    def __InitializeNetworkTuning2(self):
        '''Private method to initialize the configurationitem object for the
        NoNetworkTuning bool.
        @return: configurationitem object instance'''

        key = "NETWORKTUNING2"
        instructions = "Additional network Parameters.  Set this to 'no' " + \
            "if you are running a router or a bridge.  Also, in rare " + \
            "cases, you may need to set this to no for vmware, if you are " + \
            "using normal vmware routing yes is OK."
        default = True
        datatype = "bool"
        ci = self.initCi(datatype, key, instructions, default)
        return ci

###############################################################################

    def report(self):
        '''Main parent report method that calls the sub report methods
        @return: bool'''
        try:
            self.detailedresults = ""
            if self.environ.getosfamily() == "linux":
                self.path = "/etc/sysctl.conf"
                self.tmpPath = "/etc/sysctl.conf.tmp"
                self.original = readFile(self.path, self.logger)
                rep1success = self.reportLinux1()
                rep2success = self.reportLinux2()
            elif self.environ.getosfamily() == "solaris":
                rep1success = self.reportSolaris1()
                rep2success = self.reportSolaris2()
            elif self.environ.getosfamily() == "freebsd":
                self.path = "/etc/sysctl.conf"
                self.tmpPath = "/etc/sysctl.conf.tmp"
                self.original = readFile(self.path, self.logger)
                rep1success = self.reportFreebsd1()
                rep2success = self.reportFreebsd2()
            elif self.environ.getostype() == "Mac OS X":
                self.path = "/private/etc/sysctl.conf"
                self.tmpPath = "/private/etc/sysctl.conf.tmp"
                rep1success = True
                rep2success = self.reportMac2()
            if rep1success and rep2success:
                self.detailedresults += "NetworkTuning report has been " + \
                    "run and the system is compliant\n"
                self.compliant = True
            else:
                self.detailedresults += "NetworkTuning report has been " + \
                    "run and the system is not compliant\n"
                self.compliant = False
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
        '''Main parent fix method that calls the sub fix methods
        @return: bool'''
        try:
            if not self.networkTuning2 and not self.networkTuning1:
                return
            self.detailedresults = ""

            self.iditerator = 0
            eventlist = self.statechglogger.findrulechanges(self.rulenumber)
            for event in eventlist:
                self.statechglogger.deleteentry(event)

            success1, success2 = True, True
            if self.environ.getosfamily() == "linux":
                success1 = self.fixLinux()
            elif self.environ.getosfamily() == "freebsd":
                success1 = self.fixFreebsd()
            elif self.environ.getosfamily() == "darwin":
                success1 = self.fixMac()
            elif self.environ.getosfamily() == "solaris":
                if self.networkTuning1.getcurrvalue():
                    success1 = self.fixSolaris1()
                if self.networkTuning2.getcurrvalue():
                    success2 = self.fixSolaris2()
            if success1 and success2:
                self.rulesuccess = True
            else:
                self.rulesuccess = False
            return
        except (KeyboardInterrupt, SystemExit):
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

    def reportLinux1(self):
        '''Linux specific report method that ensures the items in fileContents
        exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
        exist in the file.  Returns True if successful in updating the file
        @return: bool'''
        compliant = True
        if not os.path.exists(self.path):
            createFile(self.path, self.logger)
        lfc = {"net.ipv4.conf.all.secure_redirects": "0",
               "net.ipv4.conf.all.accept_redirects": "0",
               "net.ipv4.conf.all.rp_filter": "1",
               "net.ipv4.conf.all.log_martians": "1",
               "net.ipv4.conf.all.accept_source_route": "0",
               "net.ipv4.conf.default.accept_redirects": "0",
               "net.ipv4.conf.default.secure_redirects": "0",
               "net.ipv4.conf.default.rp_filter": "1",
               "net.ipv4.conf.default.accept_source_route": "0",
               "net.ipv4.tcp_syncookies": "1",
               "net.ipv4.icmp_echo_ignore_broadcasts": "1",
               "net.ipv4.tcp_max_syn_backlog": "4096"}
        kvtype = "conf"
        intent = "present"
        self.editor = KVEditorStonix(self.statechglogger, self.logger, kvtype,
                                     self.path, self.tmpPath, lfc, intent,
                                     "openeq")
        if not self.editor.report():
            self.detailedresults += "/etc/sysctl.conf is not configured " + \
                "correctly for checked configuration item 1\n"
            compliant = False
        else:
            self.detailedresults += "/etc/sysctl.conf is configured " + \
                "correctly for checked configuration item 1\n"
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.detailedresults += "Permissions are incorrect on " + \
                "/etc/sysctl.con\n"
            compliant = False
        return compliant
###############################################################################

    def reportLinux2(self):
        '''Linux specific report method2 that ensures the items in fileContents
        exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
        exist in the file.  Returns True if successful in updating the file
        @return: bool'''
        compliant = True
        if not os.path.exists(self.path):
            createFile(self.path, self.logger)
        lfc = {"net.ipv4.conf.default.send_redirects": "0",
               "net.ipv4.conf.all.send_redirects": "0",
               "net.ipv4.ip_forward": "0"}
        if not self.networkTuning1.getcurrvalue():
            kvtype = "conf"
            intent = "present"
            self.editor = KVEditorStonix(self.statechglogger, self.logger,
                                         kvtype, self.path, self.tmpPath, lfc,
                                         intent, "openeq")
        else:
            self.editor.setData(lfc)
        if not self.editor.report():
            self.detailedresults += "/etc/sysctl.conf is not configured " + \
                "correctly for checked configuration item 2\n"
            compliant = False
        else:
            self.detailedresults += "/etc/sysctl.conf is configured " + \
                "correctly for checked configuration item 2\n"
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.detailedresults += "Permissions are incorrect on " + \
                "/etc/sysctl.con\nf"
            compliant = False
        return compliant
###############################################################################
#     def reportMac1(self,method):
#         '''Mac specific report method1 that ensures the items in fileContents
#         exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
#         exist in the file.
#         @return: bool'''
#         compliant = True
#         method += ".reportMac1"
#         if re.search("10\.9\.*",self.enviro.getosver()):
#             mfc = {}
#         elif re.search("10\.8\.*",self.enviro.getosver()):
# #              mfc = {"kern.ipc.somaxconn":"4096",
# #                     "net.inet.ip.accept_sourceroute":"0",
# #                     "net.inet.icmp.bmcastecho":"1"}
#         kvtype = "conf"
#         intent = "present"
#         self.editor = KVEditorStonix(self.statechglogger,self.logger,kvtype,
#                                   self.path,self.tmpPath,mfc,intent,"closedeq")
#         if not self.editor.report():
#             compliant = False
#         if not checkPerms(self.path,[0,0,420],self.logger,method):
#             compliant = False
#         return compliant
###############################################################################

    def reportMac2(self):
        '''Mac specific report method1 that ensures the items in fileContents
        exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
        exist in the file.
        @return: bool'''
        compliant = True
        if not os.path.exists(self.path):
            createFile(self.path, self.logger)
        mfc = {"net.inet.ip.forwarding": "0",
               "net.inet.ip.redirect": "0"}
        kvtype = "conf"
        intent = "present"
        self.editor = KVEditorStonix(self.statechglogger, self.logger,
                                     kvtype, self.path, self.tmpPath, mfc,
                                     intent, "closedeq")
        if not self.editor.report():
            self.detailedresults += "/private/etc/sysctl.conf is not \
configured correctly\n"
            compliant = False
        else:
            self.detailedresults += "/private/etc/sysctl.conf is configured \
correctly\n"
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.detailedresults += "Permissions are incorrect on \
/private/etc/sysctl.conf\n"
            compliant = False
        return compliant
###############################################################################

    def reportSolaris1(self):
        compliant = True
        wrongFormat = False
        sfc = {"ndd -set /dev/tcp tcp_rev_src_routes": "0",
               "ndd -set /dev/tcp tcp_conn_req_max_q0": "4096",
               "ndd -set /dev/tcp tcp_conn_req_max_q": "1024",
               "ndd -set /dev/tcp tcp_extra_priv_ports_add": "6112",
               "ndd -set /dev/arp arp_cleanup_interval": "60000",
               "ndd -set /dev/ip ip_forward_src_routed": "0",
               "ndd -set /dev/ip ip6_forward_src_routed": "0",
               "ndd -set /dev/ip ip_forward_directed_broadcasts": "0",
               "ndd -set /dev/ip ip_respond_to_timestamp": "0",
               "ndd -set /dev/ip ip_respond_to_timestamp_broadcast": "0",
               "ndd -set /dev/ip ip_respond_to_address_mask_broadcast": "0",
               "ndd -set /dev/ip ip_respond_to_echo_broadcast": "0",
               "ndd -set /dev/ip ip_ire_arp_interval": "60000",
               "ndd -set /dev/ip ip_ignore_redirect": "1",
               "ndd -set /dev/ip ip6_ignore_redirect": "1",
               "ndd -set /dev/ip ip_strict_dst_multihoming": "1",
               "ndd -set /dev/ip ip6_strict_dst_multihoming": "1",
               "ndd -set /dev/ip ip_send_redirects": "0"}
        path = "/etc/init.d/S70ndd-nettune"
        if os.path.exists(path):
            if not checkPerms(path, [0, 3, 484], self.logger):
                compliant = False
            contents = readFile(path, self.logger)
            if not contents:
                compliant = False
            else:
                for key in sfc:
                    foundKey = False
                    correctVal = True
                    keysplit = key.split()
                    for line in contents:
                        linesplit = line.split()
                        if re.search(keysplit[3], linesplit[3].strip()):
                            if len(linesplit) != 5:
                                compliant = False
                                wrongFormat = True
                                break
                            else:
                                foundKey = True
                                if linesplit[0].strip() != "ndd":
                                    wrongFormat = True
                                    break
                                elif linesplit[1].strip() != "-set":
                                    wrongFormat = True
                                    break
                                elif linesplit[2].strip() != \
                                        keysplit[2].strip():
                                    wrongFormat = True
                                    break
                                elif linesplit[4].strip() != sfc[key]:
                                    correctVal = False
                                    break
                    if wrongFormat:
                        compliant = False
                        break
                    if not correctVal:
                        compliant = False
                        break
                    if not foundKey:
                        compliant = False
                        break
        else:
            compliant = False
        '''with each of the three links we need to make sure that they exist
        and also point to the right file'''
        sympath = "/etc/init.d/S70ndd-nettune"
        path = "/etc/rc1.d/K70ndd-nettune"
        if not os.path.exists(path):
            self.detailedresults = path + " doesn't exist"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        elif not os.path.islink(path):
            self.detailedresults = path + " exists but is not a link"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        else:
            cmd = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmd):
                compliant = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if re.search("->", output[0]) and \
                            output[0].split()[-1] != sympath:
                        self.detailedresults = path + " is a link but \
                        doesn't point to the correct file"
                        self.logger.log(LogPriority.DEBUG,
                                        self.detailedresults)
                        compliant = False
                elif error:
                    compliant = False
                    self.logger.log(LogPriority.DEBUG, error)

        path = "/etc/rc2.d/S70ndd-nettune"
        if not os.path.exists(path):
            self.detailedresults = path + " doesn't exist"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        elif not os.path.islink(path):
            self.detailedresults = path + " exists but is not a link"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        else:
            cmd = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmd):
                compliant = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if re.search("->", output[0]) and \
                            output[0].split()[-1] != sympath:
                        self.detailedresults = path + " is a link but \
                        doesn't point to the correct file"
                        self.logger.log(LogPriority.DEBUG,
                                        self.detailedresults)
                        compliant = False
                elif error:
                    compliant = False
                    self.logger.log(LogPriority.DEBUG, error)

        path = "/etc/rcS.d/K70ndd-nettune"
        if not os.path.exists(path):
            self.detailedresults = path + " doesn't exist"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        elif not os.path.islink(path):
            self.detailedresults = path + " exists but is not a link"
            self.logger.log(LogPriority.DEBUG, self.detailedresults)
            compliant = False
        else:
            cmd = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmd):
                compliant = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if re.search("->", output[0]) and \
                            output[0].split()[-1] != sympath:
                        self.detailedresults = path + " is a link but \
                        doesn't point to the correct file"
                        self.logger.log(LogPriority.DEBUG,
                                        self.detailedresults)
                        compliant = False
                elif error:
                    compliant = False
                    self.logger.log(LogPriority.DEBUG, error)
        return compliant
###############################################################################

    def reportSolaris2(self):
        '''Solaris specific report method2 that Sets self.compliant to True if
        command is successful.
        @return: bool'''
        message = Popen(['/usr/sbin/routeadm'], stdout=PIPE, shell=False)
        info = message.stdout.readlines()
        for item in info:
            item = item.strip()
            item = re.sub('(\s)+', " ", item)
            item2 = item.split(" ")
            try:
                if item2[0] == "IPv4" and item2[1] == "forwarding":
                    if item2[2] == "enabled" or item2[3] == "enabled":
                        self.solarisFor = True
                if item2[0] == "IPv4" and item2[1] == "routing":
                    if item2[2] == "enabled" or item2[3] == "enabled":
                        self.solarisRou = True
            except(IndexError):
                continue
###############################################################################

    def reportFreebsd1(self):
        '''Freebsd specific report method1 that ensures the items in the file
        exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
        exist in the file.  Returns True if successful in updating the file
        @return: bool'''
        compliant = True
        if not os.path.exists(self.path):
            createFile(self.path, self.logger)
        ffc = {"net.inet.icmp.bmcastecho": "0",
               "net.inet.ip.redirect": "0",
               "net.inet.icmp.maskrepl": "0",
               "net.inet.ip.sourceroute": "0",
               "net.inet.ip.accept_sourceroute": "0",
               "net.inet.tcp.syncookies": "1"}
        kvtype = "conf"
        intent = "present"
        self.editor = KVEditorStonix(self.statechglogger, self.logger, kvtype,
                                     self.path, self.tmpPath, ffc, intent,
                                     "openeq")
        if not self.editor.report():
            compliant = False
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            compliant = False
        return compliant
###############################################################################

    def reportFreebsd2(self):
        '''Freebsd specific report method1 that ensures the items in fileContents 
        exist in /etc/sysctl.conf.  Sets self.compliant to True if all items
        exist in the file.  Returns True if successful in updating the file
        @return: bool'''
        compliant = True
        if not os.path.exists(self.path):
            createFile(self.path, self.logger)
        ffc = {"net.inet.ip.forwarding": "0",
               "net.inet.ip.fastforwarding": "0"}
        if not self.networkTuning1.getcurrvalue():
            kvtype = "conf"
            intent = "present"
            self.editor = KVEditorStonix(self.statechglogger, self.logger,
                                         kvtype, self.path, self.tmpPath, ffc,
                                         intent, "closedeq")
        else:
            self.editor.setData(ffc)
        if not self.editor.report():
            compliant = False
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            compliant = False
        return compliant
###############################################################################

    def fixLinux(self):
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            if not setPerms(self.path, [0, 0, 420], self.logger,
                            self.statechglogger, myid):
                return False
        if self.networkTuning1.getcurrvalue() or \
                self.networkTuning2.getcurrvalue():
            if self.editor.fixables:
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                self.editor.setEventID(myid)
                if not self.editor.fix():
                    return False
                elif not self.editor.commit():
                    return False
                os.chown(self.path, 0, 0)
                os.chmod(self.path, 420)
                resetsecon(self.path)
                cmd = ["/sbin/sysctl", "-q", "-e", "-p"]
                self.ch.executeCommand(cmd)
                if self.ch.getReturnCode() != 0:
                    self.detailedresults += "Unable to restart sysctl\n"
                    self.logger.log(LogPriority.DEBUG, self.detailedresults)
                    return False
                else:
                    return True
            else:
                return True
##############################################################################

    def fixMac(self):
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            if not setPerms(self.path, [0, 0, 420], self.logger,
                            self.statechglogger, myid):
                return False
        if self.networkTuning2.getcurrvalue():
            if self.editor.fixables:
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                self.editor.setEventID(myid)
                if not self.editor.fix():
                    return False
                elif not self.editor.commit():
                    return False
                os.chown(self.path, 0, 0)
                os.chmod(self.path, 420)
                resetsecon(self.path)
                return True
            else:
                return True
###############################################################################

    def fixSolaris1(self):
        sfc = {"ndd -set /dev/tcp tcp_rev_src_routes": "0",
               "ndd -set /dev/tcp tcp_conn_req_max_q0": "4096",
               "ndd -set /dev/tcp tcp_conn_req_max_q": "1024",
               "ndd -set /dev/tcp tcp_extra_priv_ports_add": "6112",
               "ndd -set /dev/arp arp_cleanup_interval": "60000",
               "ndd -set /dev/ip ip_forward_src_routed": "0",
               "ndd -set /dev/ip ip6_forward_src_routed": "0",
               "ndd -set /dev/ip ip_forward_directed_broadcasts": "0",
               "ndd -set /dev/ip ip_respond_to_timestamp": "0",
               "ndd -set /dev/ip ip_respond_to_timestamp_broadcast": "0",
               "ndd -set /dev/ip ip_respond_to_address_mask_broadcast": "0",
               "ndd -set /dev/ip ip_respond_to_echo_broadcast": "0",
               "ndd -set /dev/ip ip_ire_arp_interval": "60000",
               "ndd -set /dev/ip ip_ignore_redirect": "1",
               "ndd -set /dev/ip ip6_ignore_redirect": "1",
               "ndd -set /dev/ip ip_strict_dst_multihoming": "1",
               "ndd -set /dev/ip ip6_strict_dst_multihoming": "1",
               "ndd -set /dev/ip ip_send_redirects": "0"}
        path = "/etc/init.d/S70ndd-nettune"
        tmppath = "/etc/init.d/S70ndd-nettune.tmp"
        success = True
        # file exists...
        if os.path.exists(path):
            contents = readFile(path, self.logger)
            # but it's blank do the following:
            if not contents:
                tempstring = ""
                for key in sfc:
                    tempstring += key + " " + sfc[key] + "\n"
            # it's not blank do the following
            else:
                if not checkPerms(path, [0, 3, 484], self.logger):
                    self.iditerator += 1
                    myid = iterate(self.iditerator, self.rulenumber)
                    if not setPerms(path, [0, 3, 484], self.logger,
                                    self.statechglogger, myid):
                        self.detailedresults = "Couldn\'t'set the permissions \
                                                                   on: " + path
                        self.logger.log(LogPriority.DEBUG,
                                        self.detailedresults)
                        success = False
                tempstring = ""
                for key in sfc:
                    found = False
                    newcontents = []
                    keysplit = key.split()
                    for line in contents:
                        linesplit = line.split()
                        if re.search(keysplit[3] + "?", line):
                            if len(linesplit) != 5:
                                continue
                            else:
                                if linesplit[0].strip() != "ndd":
                                    continue
                                elif linesplit[1].strip() != "-set":
                                    continue
                                elif linesplit[2].strip() != \
                                        keysplit[2].strip():
                                    continue
                                elif linesplit[4].strip() != sfc[key]:
                                    continue
                                else:
                                    found = True
                                    newcontents.append(line)
                        else:
                            newcontents.append(line)
                    if not found:
                        newcontents.append(key + " " + sfc[key] + "\n")
                    contents = newcontents
                for line in contents:
                    tempstring += line
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            if writeFile(tmppath, tempstring, self.logger):
                event = {"eventtype": "conf",
                         "filepath": path}
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(path, tmppath, myid)
                os.rename(tmppath, path)
                os.chown(path, 0, 3)
                os.chmod(path, 484)
                resetsecon(path)
            else:
                success = False
        # file doesn't exist, just write all directives to file
        else:
            try:
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                file(path, "w+")
                event = {"eventtype": "creation",
                         "filepath": path,
                         "id": myid}
                self.statechglogger.recordchgevent(myid, event)
                tempstring = ""
                for key in sfc:
                    tempstring += key + " " + sfc[key] + "\n"
                if writeFile(path, tempstring, self.logger):
                    if not checkPerms(path, [0, 3, 484], self.logger):
                        os.chown(path, 0, 3)
                        os.chmod(path, 484)
                else:
                    success = False
            except IOError:
                self.detailedresults = "unable to open the specified file"
                self.detailedresults += traceback.format_exc()
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False

        sympath = "/etc/init.d/S70ndd-nettune"
        path = "/etc/rc1.d/K70ndd-nettune"
        cmd = ["ln", "-s", sympath, path]

        # symbolic link doesn't exist
        if not os.path.exists(path):
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # file exists but isn't a link
        elif not os.path.islink(path):
            os.remove("/etc/rc1.d/K70ndd-nettune")
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # check to see if link exists but doesn't point to the right file
        else:
            cmdls = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmdls):
                self.detailedresults = "unable to run command: ls -l " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if output[-2] == "->" and output[-1] != sympath:
                        os.remove(path)
                        if not self.cmdhelper.executeCommand(cmd):
                            self.detailedresults = "unable to create link"
                            self.logger.log(LogPriority.DEBUG,
                                            self.detailedresults)
                            success = False
                elif error:
                    self.logger.log(LogPriority.DEBUG, error)
                    success = False
        # symbolic link doesn't exist
        path = "/etc/rc2.d/S70ndd-nettune"
        cmd = ["ln", "-s", sympath, path]
        if not os.path.exists(path):
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path + "\n"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # file exists but isn't a link
        elif not os.path.islink(path):
            os.remove(path)
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path + "\n"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # check to see if link exists but doesn't point to the right file
        else:
            cmd = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to run command: ls -l " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if output[-2] == "->" and output[-1] != sympath:
                        os.remove(path)
                        if not self.cmdhelper.executeCommand(cmd):
                            self.detailedresults = "unable to create link"
                            self.logger.log(LogPriority.DEBUG,
                                            self.detailedresults)
                            success = False
                elif error:
                    self.logger.log(LogPriority.DEBUG, error)
                    success = False
        # symbolic link doesn't exist
        path = "/etc/rcS.d/K70ndd-nettune"
        cmd = ["ln", "-s", sympath, path]
        if not os.path.exists(path):
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # file exists but isn't a link
        elif not os.path.islink(path):
            os.remove(path)
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to create link between "
                self.detailedresults += sympath + " and " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
        # check to see if link exists but doesn't point to the right file
        else:
            cmd = ["ls", "-l", path]
            if not self.cmdhelper.executeCommand(cmd):
                self.detailedresults = "unable to run command: ls -l " + path
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
            else:
                output = self.cmdhelper.getOutput()
                error = self.cmdhelper.getError()
                if output:
                    if output[-2] == "->" and output[-1] != sympath:
                        if not self.cmdhelper.executeCommand(cmd):
                            self.detailedresults = "unable to create link"
                            self.logger.log(LogPriority.DEBUG,
                                            self.detailedresults)
                            success = False
                elif error:
                    self.logger.log(LogPriority.DEBUG, [error])
                    success = False
        return success
###############################################################################

    def fixSolaris2(self):
        '''Solaris specific fix method 2 that runs routeadm commands
        @return: bool'''
        success = True
        if self.solarisFor:
            retval = call(["/usr/sbin/routeadm", "-ud", "ipv4-forwarding"],
                          stdout=None, shell=False)
            if retval != 0:
                self.detailedresults = "IPv4 forwarding couldn't be disabled\n"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
            else:
                command = ['/usr/sbin/routeadm', '-ue', 'ipv4-forwarding']
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {'eventtype': 'comm',
                         'startstate': 'enabled',
                         'endstate': 'disabled',
                         'command': command,
                         'id': myid}
                self.statechglogger.recordchgevent(myid, event)
        if self.solarisRou:
            retval = call(["/usr/sbin/routeadm", "-ud", "ipv4-routing"],
                          stdout=None, shell=False)
            if retval != 0:
                self.detailedresults = "IPv4 routing couldn't be disabled"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                success = False
            else:
                command = ['/usr/sbin/routeadm', '-ue', 'ipv4-routing']
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                event = {'eventtype': 'comm',
                         'startstate': 'enabled',
                         'endstate': 'disabled',
                         'command': command,
                         'id': myid}
                self.statechglogger.recordchgevent(myid, event)
        return success
###############################################################################

    def fixFreebsd(self):
        if not checkPerms(self.path, [0, 0, 420], self.logger):
            self.iditerator += 1
            myid = iterate(self.iditerator, self.rulenumber)
            if not setPerms(self.path, [0, 0, 420], self.logger,
                            self.statechglogger, myid):
                return False
        if self.networkTuning1.getcurrvalue() or \
                self.networkTuning2.getcurrvalue():
            if self.editor.fixables:
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                self.editor.setEventID(myid)
                if not self.editor.fix():
                    return False
                elif not self.editor.commit():
                    return False
                os.chown(self.path, 0, 0)
                os.chmod(self.path, 420)
                resetsecon(self.path)
                cmd = ["/usr/sbin/service", "sysctl", "restart"]
                self.ch.executeCommand(cmd)
                if self.ch.getReturnCode() != 0:
                    self.detailedresults = "Unable to restart sysctl\n"
                    self.logger.log(LogPriority.DEBUG, self.detailedresults)
                    return False
                else:
                    return True
            else:
                return True
