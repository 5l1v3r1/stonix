#!/usr/bin/env python

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
# ============================================================================#
#               Filename          $RCSfile: stonix/logdispatcher.py,v $
#               Description       Security Configuration Script
#               OS                Linux, Mac OS X, Solaris, BSD
#               Author            Dave Kennel
#               Last updated by   $Author: $
#               Notes             Based on CIS Benchmarks, NSA RHEL
#                                 Guidelines, NIST and DISA STIG/Checklist
#               Release           $Revision: 1.0 $
#               Modified Date     $Date: 2013/10/3 14:00:00 $
# ============================================================================#
'''
Created on Aug 24, 2010

@author: dkennel
@change: 2016/07/18 eball Added smtplib.SMTPRecipientsRefused to try/except for
    reporterr method, and added debug output for both exceptions.
'''

from observable import Observable

import re
import logging
import localize
import logging.handlers
import os.path
import os
import socket
import inspect
import traceback
import smtplib
import xml.etree.ElementTree as ET
import requests

from shutil import move


def singleton_decorator(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton_decorator
class LogDispatcher (Observable):

    """
    Responsible for taking any log data and formating both a human readable log
    and an xml report containing machine info and run errors.
    :version: 1
    :author: scmcleni
    """

    def __init__(self, environment):
        Observable.__init__(self)
        self.environment = environment
        self.debug = self.environment.getdebugmode()
        self.verbose = self.environment.getverbosemode()
        self.constsrequired = [localize.REPORTSERVER,
                               localize.STONIXDEVS,
                               localize.STONIXERR,
                               localize.MAILRELAYSERVER]
        reportfile = 'stonix-report.log'
        xmlfile = 'stonix-xmlreport.xml'
        self.logpath = self.environment.get_log_path()
        self.reportlog = os.path.join(self.logpath, reportfile)
        self.xmllog = os.path.join(self.logpath, xmlfile)
        if self.debug:
            print 'LOGDISPATCHER: xml log path: ' + self.xmllog
        if os.path.isfile(self.xmllog):
            try:
                if os.path.exists(self.xmllog + '.old'):
                    os.remove(self.xmllog + '.old')
                move(self.xmllog, self.xmllog + '.old')
            except (KeyboardInterrupt, SystemExit):
                # User initiated exit
                raise
            except Exception, err:
                print 'logdispatcher: '
                print traceback.format_exc()
                print err
        self.xmlreport = xmlReport(self.xmllog, self.debug)
        self.metadataopen = False
        self.__initializelogs()
        self.last_message_received = ""
        self.last_prio = LogPriority.ERROR

    def __del__(self):
        """
        This class has an explicit destructor to ensure that log data is not
        lost in the event of an abnormal exit.
        @author: D. Kennel
        """
        # self.xmlreport.closeReport()
        # !FIXME This destructor is doing nothing. Evaluate for removal.
        pass

    def postreport(self):
        """postreport()

        Sends the XML formatted stor report file to the server
        responsible for gathering and processing them.

        @author: dkennel
        @change: Breen Malmberg - 10/17/2018 - replaced curl method of uploading xmlreport log file
                with requests python std lib method
        """

        constsmissing = False

        for const in self.constsrequired:
            if not const:
                constsmissing = True
            elif const == None:
                constsmissing = True

        if constsmissing:
            print "\nUNABLE TO LOG DUE TO ONE OR MORE OF THE FOLLOWING CONSTANTS NOT BEING SET, OR BEING SET TO None, in localize.py: STONIXERR, STONIXDEVS, MAILRELAYSERVER, REPORTSERVER\n"
            return False

        if self.environment.geteuid() != 0:
            return False

        uploadstatus = True
        self.xmlreport.closeReport()
        xmlreportfile = self.xmllog
        resolvable = True

        # check socket establish
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((localize.REPORTSERVER, 80))
            sock.close()
        except (socket.gaierror, socket.timeout, socket.error) as sockerr:
            self.log(LogPriority.DEBUG, str(sockerr))
            resolvable = False

        # upload the report
        try:
            if resolvable:

                try:
                    files = {'file': (xmlreportfile, open(xmlreportfile, 'rb'))}
                    r = requests.post('http://' + localize.REPORTSERVER + '/stonix/results' + xmlreportfile, files=files)
                except Exception as uploaderr:
                    self.log(LogPriority.DEBUG, "Failed to upload STONIX report to log server" + "\n" + str(uploaderr))

            else:
                self.log(LogPriority.DEBUG, "Could not reach log server")

            # clean up file after done
            if os.path.exists(xmlreportfile):
                os.remove(xmlreportfile)

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            trace = traceback.format_exc()
            self.log(LogPriority.ERROR, trace)

    def log(self, priority, msg_data):
        """
        Handles all writing of logger data to files. `msg_data` should be
        passed as an array of [tag, message_details] where tag is a
        descriptive string for the detailed message and XML log. For example

        ['StonixRunDateTime', '2000-01-11 11:40:01']

        If msg_data is passed as only a string then it will be tagged as "None"

        For STONIX logging purposes all essential notifications should come in
        on the "WARNING" channel. All informational notifications should come
        in on the "INFO" channel. Debug messages should use "DEBUG". Program
        errors should be sent to the "ERROR" facility. "CRITICAL" is reserved
        for events that stop the stonix program.

        @param: enum priority
        @param: string msg_data
        @return: void
        @author scmcleni
        @author: dkennel
        """

        entry = self.format_message_data(msg_data)

        self.last_message_received = entry
        self.last_prio = priority
        if isinstance(msg_data, list):
            msg = str(msg_data[0]).strip() + ':' + str(msg_data[1]).strip()
        else:
            # msg = 'none' + ':' + msg_data.strip()
            msg = msg_data.strip()
        if self.debug:
            #####
            # Set up inspect to use stack variables to log file and
            # method/function that is being called. Message to be in the
            # format:
            # DEBUG:<name_of_module>:<name of function>(<line number>): <message to print>
            stack1 = inspect.stack()[1]
            mod = inspect.getmodule(stack1[0])
            if mod:
                prefix = mod.__name__ + \
                      ":" + stack1[3] + \
                      "(" + str(stack1[2]) + "): "
            else:
                prefix = stack1[3] + \
                      "(" + str(stack1[2]) + "): "
        else:
            stack1 = inspect.stack()[1]
            mod = inspect.getmodule(stack1[0])
            if mod:
                prefix = mod.__name__ + \
                      ":" + stack1[3] + ":"
            else:
                prefix = stack1[3] + ":"

        if re.search('RULE START', msg):
            prefix = ''
            msg = msg + '\n\n'
        if re.search('RULE END', msg):
            prefix = ''
            msg = msg + '\n\n'
        if re.search('START REPORT', msg):
            prefix = ''
            msg = msg + '\n'
        if re.search('END REPORT', msg):
            prefix = ''
            msg = msg + '\n'
        if re.search('START FIX', msg):
            prefix = ''
            msg = msg + '\n'
        if re.search('END FIX', msg):
            prefix = ''
            msg = msg + '\n'

        if priority == LogPriority.INFO:
            logging.info('INFO:' + prefix + msg)
            # self.write_xml_log(priority, entry)
        elif priority == LogPriority.WARNING:
            logging.warning('WARNING:' + msg)
            if self.metadataopen:
                # self.writemetadataentry(entry)
                self.xmlreport.writeMetadata(entry)
            else:
                # self.write_xml_log(entry)
                self.xmlreport.writeFinding(entry)
        elif priority == LogPriority.ERROR:
            logging.error('ERROR:' + prefix + msg)
            # self.write_xml_log(priority, entry)
            self.reporterr(msg, prefix)
        elif priority == LogPriority.CRITICAL:
            logging.critical('CRITICAL:' + prefix + msg)
            # self.write_xml_log(priority, entry)
            self.reporterr(msg, prefix)
        elif priority == LogPriority.DEBUG:
            logging.debug('DEBUG:' + prefix + msg)
            # self.write_xml_log(priority, entry)
        else:
            # Invalid log priority
            pass

        self.set_dirty()
        self.notify_check()

    def reporterr(self, errmsg, prefix):
        """reporterr(errmsg)

        reporterr sends error messages generated by STONIX to the unixeffort
        email address. Requires an error message string.

        @param string: Error message
        @author: dkennel
        """

        constsmissing = False

        for const in self.constsrequired:
            if not const:
                constsmissing = True
            elif const == None:
                constsmissing = True

        if constsmissing:
            print "\nUNABLE TO LOG DUE TO ONE OR MORE OF THE FOLLOWING CONSTANTS NOT BEING SET, OR BEING SET TO None, in localize.py: STONIXERR, STONIXDEVS, MAILRELAYSERVER, REPORTSERVER\n"
            return

        # Function wrapped in try/except to allow the program to keep running
        # when the mail server is unavailable.
        try:
            message = '''From: ''' + localize.STONIXERR + '''
To: ''' + localize.STONIXDEVS + '''
Subject: STONIX Error Report: ''' + prefix + '''

'''
            message = prefix + ' ' + message + 'Sent by: ' + \
            self.environment.gethostname() + ' IP: ' \
            + self.environment.getipaddress() + ' OS: ' + \
            self.environment.getostype() + ': ' + \
            str(self.environment.getosver()) + \
            ' STONIX Ver: ' + str(self.environment.getstonixversion())
            message = message + '\n' + errmsg
            to = localize.STONIXDEVS + '\r\n'
            frm = localize.STONIXERR + '\r\n'

            server = smtplib.SMTP(localize.MAILRELAYSERVER)
            server.sendmail(frm, to, message)
            server.quit()
        except socket.error:
            self.log(LogPriority.DEBUG, "Could not send error e-mail: " +
                     "error contacting e-mail server")
        except smtplib.SMTPRecipientsRefused:
            self.log(LogPriority.DEBUG, "Could not send error e-mail: " +
                     "bad e-mail address in localize.STONIXDEVS")

    def format_message_data(self, msg_data):
        """
        If the expected 2 item array is passed then attach those items to
        a MessageData object. Index 0 is expected to be a tag, Index 1 is
        expected to be the detail. If an array is not passed then it is assumed
        that there is no tag (defaults to 'None') and the passed data is set
        as the Detail of the MessageData object.
        @return MessageData
        @author: scmcleni
        """
        entry = MessageData()
        if isinstance(msg_data, list):
            entry.Tag = msg_data[0].strip()
            detail = str(msg_data[1])
            entry.Detail = detail.strip()
        else:
            entry.Detail = msg_data.strip()

        return entry

    def getconsolemessage(self):
        """
        Returns the current message if called while in a dirty state.

        @return: MessageData
        @author: scmcleni
        """
        return self.last_message_received

    def getmessageprio(self):
        """
        Returns the message priority of the last message received.

        @return: LogPriority instance
        @author: dkennel
        """
        return self.last_prio

    def closereports(self):
        '''
        This method is intended for use by the single rule and undo methods
        which don't post a report as a part of their workflow. Failure to call
        this may result in the element tree dying in an exceedingly ugly
        manner when it goes out of scope.

        @author: dkennel
        '''
        try:
            self.xmlreport.closeReport()
        except Exception:
            pass

    def displaylastrun(self):
        """
        Read through the entirety of the stonix_last.log file and return it.

        @return: string
        @author: scmcleni
        """
        # Make sure the file exists first
        if os.path.isfile(self.reportlog + '.old'):
            try:
                last_log = open(self.reportlog + '.old').readlines()
                # removed DK because it's a noop
                # last_log = filter(None, last_log)
                return ''.join(last_log)

            except (KeyboardInterrupt, SystemExit):
                # User initiated exit
                raise
            except Exception, err:
                print 'logdispatcher: '
                print traceback.format_exc()
                print err
                return False

    def logRuleCount(self):
        '''
        This method logs the rule count. This is part of the run metadata but
        is processed seperately due to timing issues in the controller's init

        @author: dkennel
        '''

        self.metadataopen = True
        self.log(LogPriority.DEBUG, ['RuleCount', self.environment.getnumrules()])
        self.metadataopen = False

    def __initializelogs(self):
        """
        Open a handle to a text file (stonix.log) making it available for
        writing (append) mode. Also need to look for an old log file (prior run)
        and move it to stonix_last.log.

        @return: void
        @author: scmcleni
        @author: D. Kennel
        """

        # Check for old log file and move it to a different file name
        # overwriting any old one if it exists.
        if not os.path.isdir(self.logpath):
            try:
                os.makedirs(self.logpath, 0750)
            except (KeyboardInterrupt, SystemExit):
                # User initiated exit
                raise
            except Exception, err:
                print 'logdispatcher: '
                print traceback.format_exc()
                print err
                return False
        if os.path.isfile(self.reportlog):
            try:
                if os.path.exists(self.reportlog + '.old'):
                    os.remove(self.reportlog + '.old')
                move(self.reportlog, self.reportlog + '.old')
            except (KeyboardInterrupt, SystemExit):
                # User initiated exit
                raise
            except Exception, err:
                print 'logdispatcher: '
                print traceback.format_exc()
                print err
                return False

        # It's important that this happens after the attempt to move
        # the old log file.
        # Configure the python logging utility. Set the minimum reported log
        # data to warning or higher. (INFO and DEBUG messages will be ignored)

        if self.environment.getdebugmode():
            logging.basicConfig(filename=self.reportlog,
                                level=logging.DEBUG)
        elif self.environment.getverbosemode():
            logging.basicConfig(filename=self.reportlog,
                                level=logging.INFO)
        else:
            logging.basicConfig(filename=self.reportlog,
                                level=logging.WARNING)
        console = logging.StreamHandler()
        if self.environment.getdebugmode():
            console.setLevel(logging.DEBUG)
        elif self.environment.getverbosemode():
            console.setLevel(logging.INFO)
        else:
            console.setLevel(logging.WARNING)
        try:
            syslogs = logging.handlers.SysLogHandler()
            syslogs.setLevel(logging.WARNING)
            logging.getLogger('').addHandler(syslogs)
            logging.getLogger('').addHandler(console)
        except socket.error:
            logging.getLogger('').addHandler(console)
            self.log(LogPriority.ERROR,
                     ['LogDispatcher',
                      'SYSLOG not accepting connections!'])

        self.metadataopen = True
        self.log(LogPriority.INFO,
                 ["Hostname", self.environment.hostname])
        self.log(LogPriority.INFO,
                 ["IPAddress", self.environment.ipaddress])
        self.log(LogPriority.INFO,
                 ["MACAddress", self.environment.macaddress])
        self.log(LogPriority.INFO,
                 ["OS", str(self.environment.getosreportstring())])
        self.log(LogPriority.INFO,
                 ["STONIXversion", self.environment.getstonixversion()])
        self.log(LogPriority.INFO,
                 ['RunTime', self.environment.getruntime()])
        self.log(LogPriority.INFO,
                 ['PropertyNumber',
                  str(self.environment.get_property_number())])
        self.log(LogPriority.INFO,
                 ['SystemSerialNo',
                  self.environment.get_system_serial_number()])
        self.log(LogPriority.INFO,
                 ['ChassisSerialNo',
                  self.environment.get_chassis_serial_number()])
        self.log(LogPriority.INFO,
                 ['SystemManufacturer',
                  self.environment.get_system_manufacturer()])
        self.log(LogPriority.INFO,
                 ['ChassisManufacturer',
                  self.environment.get_chassis_manfacturer()])
        self.log(LogPriority.INFO,
                 ['UUID', self.environment.get_sys_uuid()])
        self.log(LogPriority.INFO,
                 ['PropertyNumber', self.environment.get_property_number()])
        self.log(LogPriority.DEBUG,
                 ['ScriptPath', self.environment.get_script_path()])
        self.log(LogPriority.DEBUG,
                 ['ResourcePath', self.environment.get_resources_path()])
        self.log(LogPriority.DEBUG,
                 ['RulePath', self.environment.get_rules_path()])
        self.log(LogPriority.DEBUG,
                 ['ConfigurationPath', self.environment.get_config_path()])
        self.log(LogPriority.DEBUG,
                 ['LogPath', self.environment.get_log_path()])
        self.log(LogPriority.DEBUG,
                 ['IconPath', self.environment.get_icon_path()])
        # --- End machine specific information


class MessageData:
    """
    Simple object for handling Message Data in a concrete fashion.
    @author: scmcleni
    """
    Tag = "None"
    Detail = "None"


class LogPriority:
    """
    Enum (python way) of log levels.

    @author: scmcleni
    """

    # I'm not really happy about doing it this way, but it's the shortest
    # way to be able to compare and get a string name back from an 'enum'
    # in python.

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class xmlReport:
    '''
    Simple class to manage the STONIX XML report formatting.

    @author: dkennel
    '''
    def __init__(self, path, debug=False):
        '''
        xmlReport.__init__(path): The xmlReport constructor. Requires a string
        version of the fully qualified path to the file where the XML version
        of the report will be written.

        @param path: string - fully qualified path to the report file
        @param debug: Bool - whether or not to run in debug mode
        @author: dkennel
        '''
        self.path = path
        self.debug = debug
        self.root = ET.Element('run')
        self.meta = ET.SubElement(self.root, 'metadata')
        self.findings = ET.SubElement(self.root, 'findings')
        self.closed = False

    def __del__(self):
        """
        This class has an explicit destructor to ensure that log data is
        written to disk.
        @author: D. Kennel
        """
        try:
            if not self.closed:
                self.closeReport()
        except Exception:
            pass
            #

    def writeMetadata(self, entry):
        '''
        xmlReport.writeMetadata(entry): The xmlReport method to add a metadata
        entry to the report. Requires a STONIX log entry which is a list of
        two elements; the tag and the detail. See the LogDispatcher log method.

        @param entry: Formatted version of the log data.
        @author: dkennel
        '''
        ET.SubElement(self.meta, entry.Tag, val=entry.Detail)
        if self.debug:
            print 'xmlReport.writeMetadata: Added entry ' + entry.Tag + \
            ' ' + entry.Detail

    def writeFinding(self, entry):
        '''
        xmlReport.writeFindings(entry): The xmlReport method to add a findings
        entry to the report. Requires a STONIX log entry which is a list of
        two elements; the tag and the detail. See the LogDispatcher log method.

        @param entry: Formatted version of the log data.
        @author: dkennel
        '''
        ET.SubElement(self.findings, entry.Tag, val=entry.Detail)
        if self.debug:
            print 'xmlReport.writeFinding: Added entry ' + entry.Tag + \
            ' ' + entry.Detail

    def closeReport(self):
        '''
        xmlReport.closeReport(): This method will write the xmlReport to disk.

        @author: dkennel
        '''
        try:
            if not self.closed:
                ET.ElementTree(self.root).write(self.path)
                self.closed = True
            if self.debug:
                print 'xmlReport.closeReport: dumping the ElementTree: '
                ET.dump(self.root)
        except Exception, err:
            if self.debug:
                print 'logdispatcher.xmlReport.closeReport: Error encountered processing xml'
                print err
                trace = traceback.format_exc()
                print trace
