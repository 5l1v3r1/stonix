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

# ============================================================================ #
#               Filename          $RCSfile: stonix/configuration.py,v $
#               Description       Security Configuration Script
#               OS                Linux, Mac OS X, Solaris, BSD
#               Author            Dave Kennel
#               Last updated by   $Author: $
#               Notes             Based on CIS Benchmarks, NSA RHEL 
#                                 Guidelines, NIST and DISA STIG/Checklist
#               Release           $Revision: 1.0 $
#               Modified Date     $Date: 2011/10/24 14:00:00 $
# ============================================================================ #

'''
Created on Aug 24, 2010

@author: dkennel
The Configuration object handles the STONIX config file. The config file is
organized into sections by rule name as follows:
['MAIN']
The main section contains the version of the config file.
['rule name']
Each rule has a section under it's rule name
ruleconfig  = True|False|str|int|other
Each directive is in a keyword = value format. Values may be any python data
type and it is up to the rule to validate the contents.
ruleconfiguc = "string"
Each directive has a user comment (uc) directive associated with it.
Calls to getconfvalue for non-existent entries will generate a KeyError.
'''
import ConfigParser
import sys
import os
import re


class Configuration:

    """
    Manages the stonix configuration data. Constructor takes no arguments.
    :version: 1.0
    :author: David Kennel
    """

    def __init__(self, environment):
        self.environment = environment
        self.configpath = self.environment.get_config_path()
        # print 'DEBUG: CONFIGURATION: Config_path: ' + self.configpath
        self.programconfig = self.__loadconfig()
        # print self.programconfig

    def getconfvalue(self, rulename, confkey):
        """
        Fetch the value for a given rule and key
        @param string rulename : name of the rule
        @param string confkey : Keyword for configuration value
        @return string :
        @author D. Kennel
        """
        try:
            value = self.programconfig[rulename][confkey]
        except KeyError:
            confkey = confkey.lower()
            value = self.programconfig[rulename][confkey]
        return value

    def setconfvalue(self, rulename, confkey, confvalue):
        """

        Warning! FIX ME : This may be appendix code on account of the refactor
        that created the configurationitem class. Analyze this method to see
        if it can be removed.

        Set the conf value for a given rule and key.
        @param string rulename : name of the rule
        @param string confkey :
        @param string confvalue :
        @return  :
        @author D. Kennel
        """
        if rulename not in self.programconfig:
            self.programconfig[rulename] = {}
        self.programconfig[rulename][confkey] = confvalue

    def setcommenttxt(self, rulename, commentstr):
        """

        Warning! FIX ME : This may be appendix code on account of the refactor
        that created the configurationitem class. Analyze this method to see
        if it can be removed.

        Set the comment text associated with a given rule.
        @param string rulename : name of the rule
        @param string commentstr :
        @author: D. Kennel
        """
        if rulename not in self.programconfig:
            self.programconfig[rulename] = {}
        self.programconfig[rulename]['comment_text'] = commentstr

    def setsimple(self, rulename, simple):
        """
        This method sets a bool for the named rule as to whether or not that
        rule belongs in the simple config.

        Warning! FIX ME : This may be appendix code on account of the refactor
        that created the configurationitem class. Analyze this method to see
        if it can be removed.

        @param string rulename: name of the rule
        @param bool simple: True to indicate that it belongs in the simple conf
        @author: D. Kennel
        """
        if rulename not in self.programconfig:
            self.programconfig[rulename] = {}
        self.programconfig[rulename]['simpleconf'] = simple

    def writeconfig(self, simpleconf, ruledata):
        """
        Writes current configuration data to the config file. If simpleconf is
        True we only write values that are changed or values that are marked
        as being in the simple configuration.

        @param bool simpleconf : Bool for whether or not the configuration file
        generated should be simple or full.
        @param dict: ruledata a dictionary of lists keyed by rulename and
        containing a packed list where index 0 is the rule help text and all
        remaining entries (if any) are configurationitem instances.
        @return  : void
        @author D. Kennel
        """
        confheader = """# STONIX.CONF
# STONIX configuration file
# This file is documented in the STONIX documentation. You may also review the
# documentation for this file with man stonix.conf.
[MAIN]
version = 100
"""
        conf = ''
        newline = '\n'
        conf = conf + confheader
        for rule in ruledata:
            sectionhead = '[' + rule + ']' + newline
            helptext = ruledata[rule][0]
            helptext = re.sub('^', '# ', helptext)
            helptext = re.sub('\\n', '\n# ', helptext)
            conf = conf + sectionhead
            conf = conf + helptext + newline
            for item in ruledata[rule]:
                try:
                    key = item.getkey()
                    value = item.getcurrvalue()
                    datatype = item.getdatatype()
                    defvalue = item.getdefvalue()
                    instruct = item.getinstructions()
                    instruct = re.sub('^', '# ', instruct)
                    instruct = re.sub('\\n', '\n# ', instruct)
                    usrcomment = item.getusercomment()
                    if datatype == 'list':
                        newval = ''
                        for element in value:
                            newval = newval + element + ' '
                        value = newval
                except(AttributeError):
                    continue
                uckey = 'UC' + key
                kvline = key + ' = ' + str(value) + newline
                instruct = instruct + newline
                ucline = uckey + ' = ' + usrcomment + newline
                if not simpleconf:
                    conf = conf + instruct
                    conf = conf + kvline
                    conf = conf + ucline
                elif simpleconf and item.insimple():
                    conf = conf + instruct
                    conf = conf + kvline
                    conf = conf + ucline
                elif value != defvalue:
                    conf = conf + instruct
                    conf = conf + kvline
                    conf = conf + ucline
            conf = conf + newline
        try:
            fhandle = open(self.configpath, 'w')
            fhandle.write(conf)
            fhandle.close()
            os.chmod(self.configpath, 0644)
        except (IOError):
            print "FATAL ERROR: Could not write to config file"
            print "Check path to " + self.configpath
            sys.exit(1)

    def setusercomment(self, rulename, confkey, keycomment):
        """

        Warning! FIX ME : This may be appendix code on account of the refactor
        that created the configurationitem class. Analyze this method to see
        if it can be removed.

        @param string rulename : name of the rule
        @param string confkey :
        @param string keycomment : Configuration value comment text associated
        with the given confKey
        @return  :
        @author : D. Kennel
        """
        uckey = confkey + 'uc'
        if rulename not in self.programconfig:
            self.programconfig[rulename] = {}
        self.programconfig[rulename][uckey] = keycomment

    def getusercomment(self, rulename, confkey):
        """
        Returns the user comment text associated with a given rule and
        configuration key.

        @param string rulename : name of the rule
        @param string confkey :
        @return string :
        @author D. Kennel
        """
        uckey = confkey + 'uc'
        usercomment = self.programconfig[rulename][uckey]
        return usercomment

    def __loadconfig(self):
        """
        Private method to read in the current config file and return the values
        as a list of dictionaries.

        @return  list of dictionaries :
        @author D. Kennel
        """
        progconfig = {}
        config = ConfigParser.SafeConfigParser()
        try:
            config.readfp(open(self.configpath))
        except (IOError):
            print "FATAL ERROR: Could not read config file from " \
            + self.configpath
            sys.exit(1)
        # print config.sections()
        # print config.options('MAIN')
        for section in config.sections():
            # print 'Section: ' + section
            progconfig[section] = {}
            for key in config.options(section):
                # print 'Key: ' + key
                value = config.get(section, key)
                # print 'Value: ' + value
                progconfig[section][key] = value
        return progconfig
