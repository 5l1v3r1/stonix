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
Created on Jul 7, 2014

This class handles muting the microphone input levels.

@author: dkennel
@change: 2014/10/17 ekkehard OS X Yosemite 10.10 Update
@change: 2014/12/15 dkennel Fix for Macs with no microphones (and ergo no input)
@change: 2015/04/15 dkennel updated for new isApplicable
@change: 2015/10/07 eball Help text cleanup
@change: 2016/03/14 eball Fixed possible casting error, PEP8 cleanup
@change: 2016/07/19 Breen Malmberg added fixmac() and fixlinux() methods;
altered report() and fix() methods to init variables to defaults and fix()
method to use the new fixmac and fixlinux methods
'''
from __future__ import absolute_import
import traceback
import os
import re
import subprocess

from ..rule import Rule
from ..logdispatcher import LogPriority
from ..stonixutilityfunctions import resetsecon
from ..CommandHelper import CommandHelper


class MuteMic(Rule):
    '''
    This class is responsible for muting the microphone input levels to
    help prevent attacks that would attempt to use the system as a listening
    device.

    @author: dkennel
    '''

    def __init__(self, config, environ, logger, statechglogger):
        '''
        Constructor
        '''
        Rule.__init__(self, config, environ, logger, statechglogger)
        self.rulenumber = 201
        self.rulename = 'MuteMic'
        self.logger = logger
        self.formatDetailedResults("initialize")
        self.mandatory = False
        self.helptext = '''The MuteMic rule will mute or set the microphone \
input levels to zero. This can help prevent a compromised computer from being \
used as a listening device. On most platforms input volume changes require no \
privileges so this setting can be easily undone.'''
        self.rootrequired = False
        self.mutemicrophone = self.__initializeMuteMicrophone()
        self.guidance = ['CIS']
        self.applicable = {'type': 'white',
                           'family': ['linux', 'solaris', 'freebsd'],
                           'os': {'Mac OS X': ['10.9', 'r', '10.11.10']}}
        self.pulsedefaults = '/etc/pulse/default.pa'

        self.rcorig = self.getOrigRCcontents()

    def __initializeMuteMicrophone(self):
        '''
        Private method to initialize the configurationitem object for the
        MUTEMICROPHONE bool.
        @return: configuration object instance
        @author: dkennel
        '''
        datatype = 'bool'
        key = 'mutemicrophone'
        instructions = '''If set to yes or true the MUTEMICROPHONE action \
will mute the microphone. This rule should always be set to TRUE with few \
valid exceptions.'''
        default = True
        myci = self.initCi(datatype, key, instructions, default)
        return myci

    def getOrigRCcontents(self):
        '''
        retrieve the original contents of rc.local
        if it exists

        @return: origcontents
        @rtype: list
        @author: Breen Malmberg
        '''

        origcontents = []

        try:

            if os.path.exists("/etc/rc.d/rc.local"):
                f = open("/etc/rc.d/rc.local", "r")
                origcontents = f.readlines()
                f.close()

        except Exception:
            raise
        return origcontents

    def findPulseMic(self):
        '''
        This method will attempt to determine the indexes of the sources that
        contain microphone inputs. It will return a list of strings that are
        index numbers. It is legal for the list to be of zero length in the
        cases where pulse is not running or there are no sources with
        microphones.

        @author: dkennel
        @return: list of numbers in string format
        '''
        indexlist = []
        index = ''
        listcmd = '/usr/bin/pacmd list-sources'
        proc = subprocess.Popen(listcmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, shell=True)
        pulsesourcelist = proc.stdout.readlines()
        for line in pulsesourcelist:
            if re.search('index:', line):
                self.logdispatch.log(LogPriority.DEBUG,
                                     ['MuteMic.findPulseMic',
                                      'Scanning ' + line])
                try:
                    elements = line.split(' ')
                    for element in elements:
                        if re.search('\d', element):
                            index = int(element)
                except (KeyboardInterrupt, SystemExit):
                    # User initiated exit
                    raise
                except ValueError:
                    self.logdispatch.log(LogPriority.DEBUG,
                                         ['MuteMic.findPulseMic',
                                          'Oops! Tried to convert non-integer '
                                          + element])
            if re.search('input-microphone', line):
                self.logdispatch.log(LogPriority.DEBUG,
                                     ['MuteMic.findPulseMic',
                                      'Found mic at index ' + str(index)])
                index = str(index)
                if index not in indexlist:
                    indexlist.append(index)
        return indexlist

    def checkpulseaudio(self):
        '''
        Report method for checking the pulse audio configuration to ensure that
        the Microphone defaults to muted. Returns True if the system is
        compliant

        @author: dkennel
        @return: Bool
        '''
        linesfound = 0
        if not os.path.exists(self.pulsedefaults):
            return True

        expectedlines = []
        try:
            indexlist = self.findPulseMic()
            if len(indexlist) > 0:
                for index in indexlist:
                    line = 'set-source-mute ' + index + ' 1\n'
                    expectedlines.append(line)

                fhandle = open(self.pulsedefaults, 'r')
                defaultsdata = fhandle.readlines()
                fhandle.close()

                for eline in expectedlines:
                    for pulseline in defaultsdata:
                        if re.search(eline, pulseline):
                            self.logdispatch.log(LogPriority.DEBUG,
                                                 ['MuteMic.findPulseMic',
                                                  'Found expected line ' +
                                                  str(pulseline)])
                            linesfound = linesfound + 1
                if linesfound == len(indexlist):
                    return True
                else:
                    return False
        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        return True

    def reportlinux(self):
        '''
        determine the volume level and mute status of all mic's
        and capture devices, using linux-specific mechanisms and
        commands/paths

        @return: retval
        @rtype: bool
        @author: Breen Malmberg
        '''

        retval = True
        getc0Controls = "/usr/bin/amixer -c 0 scontrols"
        getgenCap = "/usr/bin/amixer sget 'Capture'"
        miccontrols = []
        micbcontrols = []
        c0Capcontrols = []

        try:

            self.ch.executeCommand(getc0Controls)
            output = self.ch.getOutput()
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(getc0Controls)
                self.logger.log(LogPriority.DEBUG, ["MuteMic.reportlinux", "\n\nRETURN CODE WAS: " + str(retcode) + "\n\n"])
            for line in output:
                if re.search("^Simple\s+mixer\s+control\s+\'.*Mic\'", line, re.IGNORECASE):
                    sline = line.split("'")
                    miccontrols.append("'" + str(sline[1]) + "'")
                elif re.search("^Simple\s+mixer\s+control\s+\'.*Mic\s+Boost.*\'", line, re.IGNORECASE):
                    sline = line.split("'")
                    micbcontrols.append("'" + str(sline[1]) + "'")
                elif re.search("^Simple\s+mixer\s+control\s+\'.*Capture.*\'", line, re.IGNORECASE):
                    sline = line.split("'")
                    c0Capcontrols.append("'" + str(sline[1]) + "'")
            for mc in miccontrols:
                getc0mic = "/usr/bin/amixer -c 0 sget " + mc
                self.ch.executeCommand(getc0mic)
                output = self.ch.getOutput()
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    retval = False
                    self.detailedresults += "\nError while running command: " + str(getc0mic)
                    self.logger.log(LogPriority.DEBUG, ["MuteMic.reportlinux", "\n\nRETURN CODE WAS: " + str(retcode) + "\n\n"])
                for line in output:
                    if re.search("\[[0-9]+\%\]", line, re.IGNORECASE):
                        if not re.search("\[0\%\]", line, re.IGNORECASE):
                            retval = False
                            self.detailedresults += "The microphone labeled: " + str(mc) + " does not have its volume level set to 0"
            for mcb in micbcontrols:
                getc0micb = "/usr/bin/amixer -c 0 sget " + mcb
                self.ch.executeCommand(getc0micb)
                output = self.ch.getOutput()
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    retval = False
                    self.detailedresults += "\nError while running command: " + str(getc0micb)
                    self.logger.log(LogPriority.DEBUG, "\n\nRETURN CODE WAS: " + str(retcode) + "\n\n")
                for line in output:
                    if re.search("\[[0-9]+\%\]", line, re.IGNORECASE):
                        if not re.search("\[0\%\]", line, re.IGNORECASE):
                            retval = False
                            self.detailedresults += "The microphone boost labeled: " + str(mcb) + " does not have its volume level set to 0"
                    elif re.search("\[on\]|\[off\]", line, re.IGNORECASE):
                        if not re.search("\[off\]", line, re.IGNORECASE):
                            retval = False
                            self.detailedresults += "The microphone boost labeled: " + str(mcb) + " is not turned off"

            for cap in c0Capcontrols:
                getc0Cap = "/usr/bin/amixer -c 0 sget " + cap
                self.ch.executeCommand(getc0Cap)
                output = self.ch.getOutput()
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    retval = False
                    self.detailedresults += "\nError while running command: " + str(getc0Cap)
                for line in output:
                    if re.search("\[[0-9]+\%\]", line, re.IGNORECASE):
                        if not re.search("\[0\%\]", line, re.IGNORECASE):
                            retval = False
                            self.detailedresults += "\nCapture control labeled: " + str(cap) + " does not have its volume level set to 0"
                            break
                for line in output:
                    if re.search("\[on\]", line, re.IGNORECASE):
                        retval = False
                        self.detailedresults += "\nCapture control labeled: " + str(cap) + " is not turned off"
                        break

            self.ch.executeCommand(getgenCap)
            output = self.ch.getOutput()
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(getgenCap)
            for line in output:
                    if re.search("\[[0-9]+\%\]", line, re.IGNORECASE):
                        if not re.search("\[0\%\]", line, re.IGNORECASE):
                            retval = False
                            self.detailedresults += "\nGeneric Capture control does not have its volume level set to 0"
            for line in output:
                if re.search("\[on\]", line, re.IGNORECASE):
                    retval = False
                    self.detailedresults += "\nGeneric Capture control is not turned off"
                    break

            systype = self.getSysType()

            if systype == "systemd":
                if not os.path.exists("/usr/lib/systemd/system/stonix-mute-mic.service"):
                    retval = False
                    self.detailedresults += "\nThe startup script to mute mics was not found"
            if systype == "sysvinit":
                if os.path.exists("/etc/rc.d/rc.local"):
                    f = open("/etc/rc.d/rc.local", "r")
                    contentlines = f.readlines()
                    f.close()
                    found = False
                    for line in contentlines:
                        if re.search("amixer", line, re.IGNORECASE):
                            found = True
                    if not found:
                        retval = False
                        self.detailedresults += "\nSystem not configured to mute mics on startup."

        except Exception:
            raise
        return retval

    def reportmac(self):
        '''
        determine the volume level of the input device on a mac

        @return: retval
        @rtype: bool
        @author: Breen Malmberg
        '''

        retval = True
        command = "/usr/bin/osascript -e 'get the input volume of (get volume settings)'"

        try:

            self.ch.executeCommand(command)
            output = self.ch.getOutputString()
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(command)
            if re.search("[1-9]+", output.strip(), re.IGNORECASE):
                retval = False
                self.detailedresults += "\nThe microphone is not muted"

        except Exception:
            raise
        return retval

    def report(self):
        '''
        Report method for MuteMic. Uses the platform native method to read
        the input levels. Levels must be zero to pass. Note for Linux the use
        of amixer presumes pulseaudio.

        @author: dkennel
        @change: Breen Malmberg - 07/19/2016 - added variable defaults initialization;
        added commandhelper object self.ch
        '''

        # defaults
        self.compliant = True
        self.detailedresults = ""
        self.ch = CommandHelper(self.logger)

        try:

            if self.environ.getosfamily() == 'darwin':
                if not self.reportmac():
                    self.compliant = False
            elif os.path.exists("/usr/bin/amixer"):
                if not self.reportlinux():
                    self.compliant = False
            if os.path.exists(self.pulsedefaults):
                if not self.checkpulseaudio():
                    self.compliant = False

        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.compliant

    def fixPulseAudio(self):
        '''
        This method adds lines to the end of the pulse audio services default
        settings definitions file to ensure that the microphones are muted by
        default.

        @return: retval
        @rtype: bool
        @author: dkennel
        @change: Breen Malmberg - 07/19/2016 - fixed comment block; init default return
        param value, retval; made sure method always returns something
        '''

        retval = True

        if not os.path.exists(self.pulsedefaults):
            return retval

        if self.checkpulseaudio():
            return retval

        expectedlines = []

        try:

            indexlist = self.findPulseMic()

            if len(indexlist) > 0:
                for index in indexlist:
                    line = 'set-source-mute ' + index + ' 1\n'
                    expectedlines.append(line)

                fhandle = open(self.pulsedefaults, 'r')
                defaultsdata = fhandle.readlines()
                fhandle.close()

                for eline in expectedlines:
                    elinefound = False
                    for pulseline in defaultsdata:
                        if re.search(eline, pulseline):
                            self.logdispatch.log(LogPriority.DEBUG,
                                                 ['fixPulseAudio',
                                                  'Found expected line ' +
                                                  str(pulseline)])
                            elinefound = True
                    if not elinefound:
                        defaultsdata.append(eline)
                        self.logdispatch.log(LogPriority.DEBUG,
                                             ['fixPulseAudio',
                                              'Appended line ' + str(eline)])
                tempfile = self.pulsedefaults + '.stonixtmp'
                whandle = open(tempfile, 'w')
                for line in defaultsdata:
                    whandle.write(line)
                whandle.close()
                mytype1 = 'conf'
                mystart1 = self.currstate
                myend1 = self.targetstate
                myid1 = '0201001'
                self.statechglogger.recordfilechange(self.pulsedefaults,
                                                     tempfile, myid1)
                event1 = {'eventtype': mytype1,
                          'startstate': mystart1,
                          'endstate': myend1,
                          'myfile': self.pulsedefaults}
                self.statechglogger.recordchgevent(myid1, event1)
                os.rename(tempfile, self.pulsedefaults)
                os.chown(self.pulsedefaults, 0, 0)
                os.chmod(self.pulsedefaults, 420)  # int of 644
                resetsecon(self.pulsedefaults)

        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.rulesuccess = False
            retval = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)

        return retval

    def fix(self):
        '''
        Fix method for MuteMic. Uses platform native methods to set the input
        levels to zero. Note for Linux the use of amixer presumes pulseaudio.

        @return: self.rulesuccess
        @rtype: bool
        @author: dkennel
        @change: Breen Malmberg - 07/19/2016 - fixed comment block; init return
        value to default and self.detailedresults as well; commands now run
        through commandhelper object: self.ch; wrapped entire method in try/except;
        added more debugging output
        '''

        # defaults
        self.detailedresults = ""
        self.rulesuccess = True

        try:

            # if the CI is disabled, then don't run the fix
            if not self.mutemicrophone.getcurrvalue():
                self.logger.log(LogPriority.DEBUG, "\n\n\nmute microphone CI was not enabled so nothing will be done!\n\n\n")
                return

            self.logger.log(LogPriority.DEBUG, "Attempting to mute all mic's and capture sources...")
            if self.environ.getosfamily() == 'darwin':
                if not self.fixmac():
                    self.rulesuccess = False

            if os.path.exists('/usr/bin/amixer'):
                if not self.fixlinux():
                    self.rulesuccess = False

            if os.path.exists(self.pulsedefaults) and self.environ.geteuid() == 0:
                if not self.fixPulseAudio():
                    self.rulesuccess = False

            self.logger.log(LogPriority.DEBUG, "Finished muting all mic's and capture sources")

        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception:
            self.rulesuccess = False
            self.detailedresults += traceback.format_exc()
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess, self.detailedresults)

        return self.rulesuccess

    def fixmac(self):
        '''
        run commands to turn off microphones on mac

        @return: retval
        @rtype: bool
        @author: Breen Malmberg
        '''

        # defaults
        retval = True
        command = "/usr/bin/osascript -e 'set volume input volume 0'"

        self.logger.log(LogPriority.DEBUG, "System detected as: darwin. Running fixmac()...")

        try:

            self.ch.executeCommand(command)
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(command)

        except Exception:
            raise
        return retval

    def getDevices(self):
        '''
        retrieve a list of device indexes

        @return: indexes
        @rtype: list
        @author: Breen Malmberg
        '''

        indexes = []

        cmd = "/usr/bin/pacmd list-sinks"

        try:

            self.ch.executeCommand(cmd)
            retcode = self.ch.getReturnCode()
            output = self.ch.getOutput()
            if retcode != 0:
                self.detailedresults += "\nError while running command: " + str(cmd)
                return indexes
            for line in output:
                if re.search("index\:", line, re.IGNORECASE):
                    sline = line.split(":")
                    indexes.append(str(sline[1]).strip())

        except Exception:
            raise
        if not indexes:
            self.logger.log(LogPriority.DEBUG, "Returning a blank list for indexes!")
        return indexes

    def getMics(self, index):
        '''
        return a list of simple mixer control mics for the
        specified device index

        @return: mics
        @rtype: list
        @author: Breen Malmberg
        '''

        mics = []
        cmd = "/usr/bin/amixer -c " + index + " scontrols"

        try:

            self.ch.executeCommand(cmd)
            retcode = self.ch.getReturnCode()
            output = self.ch.getOutput()
            if retcode != 0:
                self.detailedresults += "\nError while running command: " + str(cmd)
            for line in output:
                if re.search("^Simple\s+mixer\s+control\s+\'.*Mic\'", line, re.IGNORECASE):
                    sline = line.split("'")
                    mics.append("'" + str(sline[1]).strip() + "'")
        except Exception:
            raise
        if not mics:
            self.logger.log(LogPriority.DEBUG, "Returning a blank list for mics!")
        return mics

    def buildScript(self, systype):
        '''
        dynamically build the boot up script and return
        a list of the lines to be written

        @return: script
        @rtype: list
        @author: Breen Malmberg
        '''

        script = []

        try:

            if systype == "systemd":
                # create the systemdservice script
                for item in self.systemdcomment:
                    script.append(item)
                for item in self.systemdunit:
                    script.append(item)
                for item in self.systemdservice:
                    script.append(item)
                for item in self.systemdinstall:
                    script.append(item)
            if systype == "sysvinit":

                # if the script already exists, put the
                # existing contents at the beginning
                f = open(self.sysvscriptname, "r")
                contentlines = f.readlines()
                f.close()

                for line in contentlines:
                    script.append(line)
                script.append("\n")
                for line in self.sysvscriptcmds:
                    script.append(line)

        except Exception:
            raise
        return script

    def getSysType(self):
        '''
        determine whether the os type is
        systemd-based or sysvinit-based

        @return: systype
        @rtype: string
        @author: Breen Malmberg
        '''

        # determine if os is systemd-based or sysvinit
        systemd = False
        sysvinit = False
        checkbasecmd = "pidof systemd && echo 'systemd' || echo 'sysvinit'"
        systype = ""

        try:

            self.logger.log(LogPriority.DEBUG, "Detecting whether OS is systemd or sysvinit based...")
            self.ch.executeCommand(checkbasecmd)
            retcode = self.ch.getReturnCode()
            output = self.ch.getOutput()
    
            if retcode != 0:
                self.detailedresults += "\nError while running command: " +str(checkbasecmd)
    
            for line in output:
                if re.search("systemd", line, re.IGNORECASE):
                    systemd = True
                    self.logger.log(LogPriority.DEBUG, "OS detected as systemd based")
                if re.search("sysvinit", line, re.IGNORECASE):
                    sysvinit = True
                    self.logger.log(LogPriority.DEBUG, "OS detected as sysvinit based")
            if not systemd and not sysvinit:
                self.logger.log(LogPriority.DEBUG, "\n\n\nDid not detect either systemd or sysvinit in output\n\n\n")
            if systemd:
                systype = "systemd"
            if sysvinit:
                systype = "sysvinit"
        except Exception:
            raise
        return systype

    def finishScript(self, systype, script):
        '''
        write the script to disk and run any
        final needed command(s)

        @return: void
        @author: Breen Malmberg
        '''

        try:

            if systype == "systemd":
    
                tempsystemdscriptname = self.systemdscriptname + ".stonixtmp"
    
                # make sure the base directory exists
                # before we attempt to write a file to it
                if not os.path.exists(self.systemdbase):
                    os.makedirs(self.systemdbase, 0755)
        
                # write the script to disk
                tf = open(tempsystemdscriptname, "w")
                tf.writelines(script)
                tf.close()
        
                os.rename(tempsystemdscriptname, self.systemdscriptname)
        
                # own the script by root root
                # make the script executable
                os.chown(self.systemdscriptname, 0, 0)
                os.chmod(self.systemdscriptname, 0644)
        
                # tell systemd to pull in the script unit
                # when starting its target
                enablescript = self.systemctl + " enable " + self.systemdscriptname
                self.ch.executeCommand(enablescript)
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    self.detailedresults += "\nError while running command: " + str(enablescript)
    
            if systype == "sysvinit":
    
                sysvscriptname = "/etc/rc.d/rc.local"
                tempsysvscriptname = sysvscriptname + ".stonixtmp"
    
                # write the script to disk
                tf = open(tempsysvscriptname, "w")
                tf.writelines(script)
                tf.close()
    
                os.rename(tempsysvscriptname, sysvscriptname)
    
                # make sure permissions are correct
                os.chown(sysvscriptname, 0, 0)
                os.chmod(sysvscriptname, 0755)

        except Exception:
            raise

    def fixlinux(self):
        '''
        run commands to turn off microphones on linux

        @return: retval
        @rtype: bool
        @author: Breen Malmberg
        '''

        retval = True
        amixer = "/usr/bin/amixer"
        self.systemctl = "/usr/bin/systemctl"
        self.systemdcomment = ["# Added by STONIX\n\n"]
        self.systemdunit = ["[Unit]\n", "Description=Mute Mic at system boot\n", "After=basic.target\n\n"]
        self.systemdservice = ["[Service]\n", "Type=oneshot\n"]
        self.systemdinstall = ["\n[Install]\n", "WantedBy=basic.target\n"]
        self.systemdbase = "/usr/lib/systemd/system/"
        self.systemdscriptname = self.systemdbase + "stonix-mute-mic.service"
        self.sysvscriptcmds = []
        self.systemdscript = []
        self.sysvscriptname = "/etc/rc.d/rc.local"

        self.logger.log(LogPriority.DEBUG, "\n\n\nSystem detected as: linux. Running fixlinux()...\n\n\n")

        try:

            devices = self.getDevices()
            self.logger.log(LogPriority.DEBUG, "\nNumber of devices on this system is: " + str(len(devices)))

            if not devices:
                mics = self.getMics("0")
                for m in mics:
                    mutemiccmd = amixer + " -c 0 sset " + m + " 0% nocap mute off"
                    self.systemdservice.append("ExecStart=" + str(mutemiccmd) + "\n")
                    self.sysvscriptcmds.append(str(mutemiccmd) + "\n")
                    self.ch.executeCommand(mutemiccmd)
                mutecapturecmd = amixer + " -c 0 sset 'Capture' 0% mute off"
                self.ch.executeCommand(mutecapturecmd)
                self.systemdservice.append("ExecStart=" + str(mutecapturecmd) + "\n")
                self.sysvscriptcmds.append(str(mutecapturecmd) + "\n")

            else:
                for di in devices:
                    mics = self.getMics(di)
                    self.logger.log(LogPriority.DEBUG, "\nNumber of mic's on device index " + str(di) + " is " + str(len(mics)))
                    for m in mics:
                        mutemiccmd = amixer + " -c " + di + " sset " + m + " 0% nocap mute off"
                        self.systemdservice.append("ExecStart=" + str(mutemiccmd) + "\n")
                        self.sysvscriptcmds.append(str(mutemiccmd) + "\n")
                        self.ch.executeCommand(mutemiccmd)
                    mutecapturecmd = amixer + " -c " + di + " sset 'Capture' 0% mute off"
                    self.ch.executeCommand(mutecapturecmd)
                    self.systemdservice.append("ExecStart=" + str(mutecapturecmd) + "\n")
                    self.sysvscriptcmds.append(str(mutecapturecmd) + "\n")

            # get card 0 Capture control info
            # this is separate from the general Capture
            self.ch.executeCommand(amixer + " -c 0 sget Capture")
            output = self.ch.getOutput()
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(amixer + " -c 0 sget Capture")
            for line in output:
                # toggle the c0 Capture control off (mute it)
                if re.search("\[on\]", line, re.IGNORECASE):
                    self.ch.executeCommand(amixer + " -c 0 sset Capture toggle")
                    retcodeB = self.ch.getReturnCode()
                    if retcodeB != 0:
                        retval = False
                        self.detailedresults += "\nError while running command: " + str(amixer +  " -c 0 sset Capture toggle")
                    # again, we don't want to toggle more than once
                    break

            # set card 0 Capture volume to 0
            self.ch.executeCommand(amixer + " -c 0 sset Capture 0")
            self.systemdservice.append("ExecStart=" + amixer + " -c 0 sset Capture 0\n")
            self.sysvscriptcmds.append(amixer + " -c 0 sset Capture 0\n")
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(amixer + " -c 0 sset Capture 0")

            setGenCap = amixer + " sset 'Capture' 0% nocap off mute"
            self.systemdservice.append("ExecStart=" + str(setGenCap) + "\n")
            self.sysvscriptcmds.append(setGenCap)
            self.ch.executeCommand(setGenCap)
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                retval = False
                self.detailedresults += "\nError while running command: " + str(setGenCap)

            systype = self.getSysType()
            script = self.buildScript(systype)
            self.finishScript(systype, script)

        except Exception:
            raise
        return retval

    def undo(self):
        '''
        Undo method for MuteMic. Sets the inpnumut levels to 100.

        @author: dkennel
        '''

        setlevels = None

        try:

            if self.environ.getosfamily() == 'darwin':
                setlevels = "/usr/bin/osascript -e 'set volume input volume 100'"
            elif os.path.exists('/usr/bin/amixer'):
                setlevels = '/usr/bin/amixer sset Capture Volume 65536,65536 unmute'

            subprocess.call(setlevels, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)

            systemdscriptname = "/usr/lib/systemd/system/stonix-mute-mic.service"
            disablesysdscript = "/usr/bin/systemctl disable " + systemdscriptname
            if os.path.exists(systemdscriptname):
                self.ch.executeCommand(disablesysdscript)
                os.remove(systemdscriptname)
            if os.path.exists("/etc/rc.d/rc.local"):
                f = open("/etc/rc.d/rc.local", "w")
                f.writelines(self.rcorig)
                f.close()

                os.chown("/etc/rc.d/rc.local", 0, 0)
                os.chmod("/etc/rc.d/rc.local", 0755)

        except (KeyboardInterrupt, SystemExit):
            # User initiated exit
            raise
        except Exception, err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
                " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
