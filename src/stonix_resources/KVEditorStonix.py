'''
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
Created on Jun 12, 2013

@author: dwalker
'''
from KVEditor import KVEditor
from logdispatcher import LogPriority
import os


class KVEditorStonix(KVEditor):
    '''The Stonix specific class for The Key Value Editor Class group that
    inherits from the Parent KVEditor class.  If kvtype is conf or tagconf:
    1. Create object editor = KVEditorStonix(....)
    2. Call the report def to see if the specified values are either present
       or not based on the intent, "present" or "notpresent", where, "present"
       means the values in data variable are desired in the configuration file
       and "notpresent" means the values in data variable are not desired in
       the configuration file.
    3. If report returns False then run the fix method. If you create object
       with data values that are desired in the config file, and later, in the
       same rule, you have data values that are not desired in the config file,
       the kveditorstonix easily keeps track of all values that are desired or
       undesired in a config file no matter how many different occasions the
       intent may change.  Set intent and set Data to the new values (can also
       be done during instantiation) run the report then run the fix.  Repeat
       those four actions in that order as many times as needed.
    4. Once all reports and fixes have been run, finally run the commit.
       Running the commit only once at the end ensure that only one statechange
       event is recorded.'''

    '''If kvtype is defaults or plist, upon instantiation of the kveditorstonix
    object, id's will be created for each item in the data variable and passed
    through the kveditor object, essentially making each defaults or plist
    command a separate event.  Same rules apply as above however there is no
    intent variable and data can only be set once upon instantiation'''

    def __init__(self, stchlgr, logger, kvtype, path, tmpPath, data, intent="",
                                                                configType=""):
        '''If kvtype is conf or tagconf, although not mandatory, intent and
        configType should be passed as parameters at object instantiation time
        '''
        self.logger = logger
        KVEditor.__init__(self, stchlgr, logger, kvtype, path, tmpPath, data,
                                                            intent, configType)
        self.stchlgr = stchlgr
        self.kvtype = kvtype
        self.eid = ""
###############################################################################
    def report(self):
        retval = self.validate()
        if retval == "invalid":
            self.detailedresults = "Data is not in correct format\n"
            raise(self.detailedresults)
        elif retval:
            return True
        else:
            return False
###############################################################################
    def fix(self):
        if self.update():
            return True
        else:
            return False
###############################################################################
    def commit(self):
        if self.kvtype == "defaults":
            if self.editor.nocmd:
                return True
            if not self.editor.commit():
                return False
            if isinstance(self.editor.getundoCmd(),str):
                eventtype = "commandstring"
            else:
                eventtype = "comm"
            event = {"eventtype": eventtype,
                     "startstate": "notconfigured",
                     "endstate": "configured",
                     "command": self.editor.getundoCmd()}
            if self.getEventID():
                self.stchlgr.recordchgevent(self.getEventID(),event)
            return True
        elif self.editor.commit():
            event = {'eventtype': 'conf',
                     'startstate': 'notconfigured',
                     'endstate': 'configured',
                     'filepath': self.path}
            if self.getEventID():
                self.stchlgr.recordchgevent(self.getEventID(), event)
                self.stchlgr.recordfilechange(self.path, self.tmpPath, self.eid)
            try:
                os.rename(self.tmpPath, self.path)
            except OSError:
                self.detailedresults = "couldn't rename file"
                self.logger.log(LogPriority.DEBUG, self.detailedresults)
                raise
            return True
        else:
            return False
###############################################################################
    def getEventID(self):
        return self.eid
###############################################################################
    def setEventID(self, eid):
        self.eid = eid
###############################################################################
    def setPath(self,path):
        self.path = path
###############################################################################
    def updatedata(self,data):
        success = self.editor.updateData(data)
        return success
###############################################################################
    def getvalue(self):
        retval = self.editor.getValue()
        return retval
###############################################################################
    def setCurrentHostBool(self, val):
        self.editor.setCurrentHostbool(val)