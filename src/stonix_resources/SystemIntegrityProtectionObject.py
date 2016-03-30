#!/usr/bin/python

'''
###############################################################################
#                                                                             #
# Copyright 2016.  Los Alamos National Security, LLC. This material was       #
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

@author: ekkehard j. koch
@change: 2016/03/03 ekkehard original implementation
@change: 2016/03/30 ekkehard comments & bug fixes
'''
import os
import traceback
import types
from CommandHelper import CommandHelper
from logdispatcher import LogPriority


class SystemIntegrityProtectionObject():
    '''
    lanlMacInfo gets information from the mac and LDAP to help set basic
    computer data for the mac this includes:
    ComputerName
    HostName
    LocalHostname
    asset_id (property number)
    endUserName (owner)
    @author: ekkehard
    '''

    def __init__(self, logdispatcher):
        '''
        initialize lanlMacInfo
        @author: ekkehard
        '''
# Make sure we have the full path for all commands
        self.logdispatch = logdispatcher
        self.ch = CommandHelper(self.logdispatch)
        self.csrutil = "/usr/bin/csrutil"
        self.sw_vers = "/usr/bin/sw_vers"
        self.osx_major_version = 0
        self.osx_minor_version = 0
        self.osx_version_string = ""
        self.initializeOSXVersionBoolean = False
        self.initializeSIPStatusBoolean = False
        self.sipstatus = ""
# Reset messages
        self.messageReset()

    def getSIPStatus(self):
        '''
        get the current System Integrity Protection (SIP) status
        @author: ekkehard
        @return: dictionary entry
        '''
        osx_version = self.initializeOSXVersion()
        sipstatus = self.initializeSIPStatus()
        msg = "SIP status is "+ str(sipstatus) + ". OS X Version string is " + str(osx_version) + "."
        self.logdispatch.log(LogPriority.DEBUG, msg)
        return self.sipstatus

    def initializeOSXVersion(self, forceInitializtion = False):
        '''
        initialize OS X version info
        @author: ekkehard
        @return: boolean - True
        '''
        success = True
        if forceInitializtion:
            self.initializeOSXVersionBoolean = False
        if not self.initializeOSXVersionBoolean:
            try:
                self.initializeOSXVersionBoolean = True
# Get the major version of OS X
                command = self.sw_vers + " -productVersion | awk -F. '{print $1}'"
                self.ch.executeCommand(command)
                errorcode = self.ch.getError()
                osxmajorversion = self.ch.getOutputString().strip()
                self.osx_major_version = int(osxmajorversion)
                msg = "("+ str(errorcode) + ") OS X Major Version is " + str(self.osx_major_version)
                self.logdispatch.log(LogPriority.DEBUG, msg)
# Get the minor version of OS X
                command = self.sw_vers + " -productVersion | awk -F. '{print $2}'"
                self.ch.executeCommand(command)
                errorcode = self.ch.getError()
                osxminorversion = self.ch.getOutputString().strip()
                self.osx_minor_version = int(osxminorversion)
                msg = "("+ str(errorcode) + ") OS X Minor Version is " + str(self.osx_minor_version)
                self.logdispatch.log(LogPriority.DEBUG, msg)
# Get full version string
                command = self.sw_vers + " -productVersion"
                self.ch.executeCommand(command)
                errorcode = self.ch.getError()
                self.osx_version_string = self.ch.getOutputString().strip()
                self.osx_minor_version = int(osxminorversion)
                msg = "("+ str(errorcode) + ") OS X Version string is " + str(self.osx_minor_version)
                self.logdispatch.log(LogPriority.DEBUG, msg)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                msg = traceback.format_exc()
                self.logdispatch.log(LogPriority.ERROR, msg)
                success = False
        return success 
                
    def initializeSIPStatus(self, forceInitializtion = False):
        '''
        Initialize SIP Status
        @author: ekkehard
        @return: boolean - True
        '''
        success = True
        if forceInitializtion:
            self.initializeSIPStatusBoolean = False
        if not self.initializeSIPStatusBoolean:
            try:
                self.initializeSIPStatusBoolean = True
                if self.osx_major_version < 10:
                    self.sipstatus = "Not Applicable"
                elif self.osx_minor_version < 11:
                    command = self.sw_vers + " -productVersion"
                    self.ch.executeCommand(command)
                    errorcode = self.ch.getError()
                    self.sipstatus = "Not Applicable For " + self.osx_version_string
                    msg = "("+ str(errorcode) + ") SIP status is " + str(self.sipstatus)
                    self.logdispatch.log(LogPriority.DEBUG, msg)
                elif os.path.exists(self.csrutil):
                    command = self.csrutil + " status | awk '/status/ {print $5}' | sed 's/\.$//'"
                    self.ch.executeCommand(command)
                    errorcode = self.ch.getError()
                    sipstatus = self.ch.getOutputString().strip()
                    if sipstatus == "disabled":
                        self.sipstatus = "Disabled"
                    elif sipstatus == "enabled":
                        self.sipstatus = "Enabled"
                    else:
                        self.sipstatus = "Not Applicable - " + str(sipstatus) + " not a know status value."
                    msg = "("+ str(errorcode) + ") SIP status is " + str(self.sipstatus)
                    self.logdispatch.log(LogPriority.DEBUG, msg)
                else:
                    self.sipstatus = "Not Applicable - " + str(self.csrutil) + " not available!"
                msg = "The System Ingegrity Protection status is " + str(self.sipstatus)
                self.logdispatch.log(LogPriority.DEBUG, msg)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                msg = traceback.format_exc()
                self.logdispatch.log(LogPriority.ERROR, msg)
                success = False
        return success

    def report(self):
        '''
        report if the SIP status is anabled or disabled.
        @param self:essential if you override this definition
        @return: boolean
        @note: None
        '''
        compliant = True
        sipstatus = self.getSIPStatus()
        if sipstatus == "Disabled":
            compliant = False
            msg = self.messageAppend("- System Ingegrity Protection (SIP) is disabled but should be enabled!")
            self.logdispatch.log(LogPriority.DEBUG, msg)
        elif sipstatus == "Enabled":
            msg = self.messageAppend("- System Ingegrity Protection (SIP) is enabled!")
            self.logdispatch.log(LogPriority.DEBUG, msg)
        else:
            msg = self.messageAppend("- " + str(sipstatus))
            self.logdispatch.log(LogPriority.DEBUG, msg)
        return compliant

    def fix(self):
        fixed = True
        return fixed

    def messageGet(self):
        '''
        get the formatted message string.
        @author: ekkehard j. koch
        @param self:essential if you override this definition
        @return: string
        @note: None
        '''
        return self.msg

    def messageAppend(self, pMessage=""):
        '''
        append and format message to the message string.
        @author: ekkehard j. koch
        @param self:essential if you override this definition
        @return: boolean - true
        @note: None
        '''
        datatype = type(pMessage)
        if datatype == types.StringType:
            if not (pMessage == ""):
                msg = pMessage
                if (self.msg == ""):
                    self.msg = msg
                else:
                    self.msg = self.msg + "\n" + \
                    msg
        elif datatype == types.ListType:
            if not (pMessage == []):
                for item in pMessage:
                    msg = item
                    if (self.msg == ""):
                        self.msg = msg
                    else:
                        self.msg = self.msg + "\n" + \
                        msg
        else:
            raise TypeError("pMessage with value" + str(pMessage) + \
                            "is of type " + str(datatype) + " not of " + \
                            "type " + str(types.StringType) + \
                            " or type " + str(types.ListType) + \
                            " as expected!")
        return self.msg

    def messageReset(self):
        '''
        reset the message string.
        @author: ekkehard j. koch
        @param self:essential if you override this definition
        @return: boolean - true
        @note: none
        '''
        self.msg = ""
        return self.msg
