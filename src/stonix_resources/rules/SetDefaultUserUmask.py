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


"""
Created on Dec 11, 2012
The SetDefaultUserUmask class sets the default user umask to 077. Also accepts
user input of alternate 027 umask.

@author: Breen Malmberg
@change: 02/16/2014 ekkehard Implemented self.detailedresults flow
@change: 02/16/2014 ekkehard Implemented isapplicable
@change: 04/18/2014 ekkehard ci updates and ci fix method implementation
@change: 07/10/2014 rsn change assignments to comparisons and if on mac & root,
                    use 022 as the umask
@change: 08/05/2014 ekkehard added removeStonixUMASKCodeFromFile
@change: 08/25/2014 Breen Malmberg completely re-written
@change: 08/27/2014 Breen Malmberg added documentation, cleaned up some existing
        documentation
@change: 2015/04/17 dkennel updated for new isApplicable. Tuned text.
@change: 2017/07/17 ekkehard - make eligible for macOS High Sierra 10.13
@change: 2017/11/13 ekkehard - make eligible for OS X El Capitan 10.11+
@change: 2018/06/08 ekkehard - make eligible for macOS Mojave 10.14
@change: 2019/03/12 ekkehard - make eligible for macOS Sierra 10.12+
@change: 2019/08/07 ekkehard - enable for macOS Catalina 10.15 only
"""

import os
import re
import traceback
import shutil

from rule import Rule
from stonixutilityfunctions import iterate
from logdispatcher import LogPriority
from CommandHelper import CommandHelper


class SetDefaultUserUmask(Rule):
    """The SetDefaultUserUmask class sets the default user umask to 077. Also
    accepts user input of alternate 027 umask.
    
    For OS X documentation on this can be found at:
    http://support.apple.com/kb/HT2202
    """

    def __init__(self, config, environ, logdispatch, statechglogger):
        """
        Constructor
        """

        Rule.__init__(self, config, environ, logdispatch, statechglogger)
        self.config = config
        self.environ = environ
        self.logger = logdispatch
        self.statechglogger = statechglogger
        self.rulenumber = 48
        self.rulename = 'SetDefaultUserUmask'
        self.formatDetailedResults("initialize")
        self.compliant = False
        self.mandatory = True
        self.sethelptext()
        self.rootrequired = True
        self.guidance = ['CIS', 'NSA(2.3.4.4)', 'CCE-3844-8', 'CCE-4227-5',
                         'CCE-3870-3', 'CCE-4737-6']

        # set up which system types this rule will be applicable to
        self.applicable = {'type': 'white',
                           'family': 'linux',
                           'os': {'Mac OS X': ['10.15', 'r', '10.15.10']}}

        # decide what the default umask value should be, based on osfamily
        if self.environ.getosfamily() == 'darwin':
            self.userumask = "022"
        else:
            self.userumask = "077"
        self.rootumask = "022"

        self.ci = self.initCi("bool",
                              "SetDefaultUserUmask",
                              "To prevent stonix from setting the " + \
                              "default user umask, set the value of " + \
                              "SetDefaultUserUmask to False.",
                              True)

        # init CIs
        user_ci_type = "string"
        user_ci_name = "DEFAULTUSERUMASK"
        user_ci_instructions = "Set the default user umask value. Correct format is " + "a 3-digit, 0-padded integer. This value will determine the default permissions for every file created by non-privileged users."
        self.userUmask = self.initCi(user_ci_type, user_ci_name, user_ci_instructions, self.userumask)

        root_ci_type = "string"
        root_ci_name = "DEFAULTROOTUMASK"
        root_ci_instructions = "Set the default root umask value. Correct format is a 3-digit, 0-padded integer. Setting this to a value more restrictive than 022 may cause issues on your system. This value will determine the default permissions for every file created by the root user."
        self.rootUmask = self.initCi(root_ci_type, root_ci_name, root_ci_instructions, self.rootumask)

    def report(self):
        """
        The report method examines the current configuration and determines
        whether or not it is correct. If the config is correct then the
        self.compliant, self.detailedresults and self.currstate properties are
        updated to reflect the system status. self.rulesuccess will be updated
        if the rule does not succeed.

        :return: self.compliant
        :rtype: bool
        """

        # defaults
        self.detailedresults = ""
        self.ch = CommandHelper(self.logger)

        # set up list of files which need to be checked and configured
        self.rootfiledict = {"/root/.bash_profile": False,
                             "/root/.bashrc": False,
                             "/root/.cshrc": False,
                             "/root/.tcshrc": False}

        self.userfiledict = {"/etc/profile": False,
                             "/etc/csh.login": False,
                             "/etc/csh.cshrc": False,
                             "/etc/bashrc": False,
                             "/etc/zshrc": False,
                             "/etc/login.conf": False,
                             "/etc/bash.bashrc": False,
                             "/etc/login.defs": False}

        try:

            # decide which report method to run based on osfamily
            if self.environ.getosfamily() == 'darwin':
                self.compliant = self.reportmac()
            else:
                self.compliant = self.reportnix()

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.compliant = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
            " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("report", self.compliant, self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)

        return self.compliant

    def reportnix(self):
        """
        private method for reporting compliance status of *nix based systems

        :return: configured
        :rtype: bool
        """

        # defaults
        configured = True

        try:

            # check for presence of umask config line in user files
            for item in self.userfiledict:
                if not os.path.exists(item):
                    self.detailedresults += "\nMissing required configuration file: " + str(item)
                    configured = False
                elif self.searchString('^umask\s*' + str(self.userUmask.getcurrvalue()), item):
                    self.userfiledict[item] = True

            for item in self.userfiledict:
                if os.path.exists(item):
                    if not self.userfiledict[item]:
                        self.detailedresults += "\nFile: " + str(item) + " has an incorrect user umask configuration."
                        configured = False

            # check for presence of umask config line in root files
            for item in self.rootfiledict:
                if not os.path.exists(item):
                    self.detailedresults += "\nMissing required configuration file: " + str(item)
                    configured = False
                elif self.searchString('^umask\s*' + str(self.rootUmask.getcurrvalue()), item):
                    self.rootfiledict[item] = True

            for item in self.rootfiledict:
                if os.path.exists(item):
                    if not self.rootfiledict[item]:
                        self.detailedresults += "\nFile: " + str(item) + " has an incorrect root umask configuration."
                        configured = False

        except Exception:
            raise

        return configured

    def reportmac(self):
        """the system's default user umask value (if set to something other than 022,
        will be stored in the file /var/db/com.apple.xpc.launchd/config/user.plist
        on versions of mac os x equal to or greater than 10.10


        :return: retval

        :rtype: bool
@author: Breen Malmberg

        """

        valid = False
        pathexists = True
        plistpath = "/var/db/com.apple.xpc.launchd/config/user.plist"
        cmd = "/usr/bin/defaults read " + str(plistpath) + " Umask"
        # mac transforms the umask value to a different integer value
        # the algorithm is unknown, but these values are tested and determined to be
        # 022, 027 and 077 respectively
        umaskTrans = {'022': '18',
                      '027': '23',
                      '077': '63'}

        if not os.path.exists(plistpath):
            pathexists = False
        else:
            self.ch.executeCommand(cmd)
            retcode = self.ch.getReturnCode()
            if retcode != 0:
                errstr = self.ch.getErrorString()
                self.logger.log(LogPriority.DEBUG, errstr)
            outputstr = self.ch.getOutputString()
            if self.userumask in umaskTrans:
                if re.search(umaskTrans[self.userumask], outputstr, re.IGNORECASE):
                    valid = True
            else:
                valid = False

        retval = bool(valid and pathexists)

        return retval

    def fix(self):
        """The fix method will apply the required settings to the system.
        self.rulesuccess will be updated if the rule does not succeed.
        Method to set the default users umask to 077 (or 027 if specified in
        the related config file.


        :return: bool
        @author: Breen Malmberg

        """

        # defaults
        self.detailedresults = ""
        self.iditerator = 0

        try:

            # if the ci is enabled/True, proceed
            if self.ci.getcurrvalue():

                # decide which fix method to run, based on osfamily
                if self.environ.getosfamily() == 'darwin':
                    self.rulesuccess = self.fixmac()
                else:
                    self.rulesuccess = self.fixnix()

            # if the ci is not enabled, or False, report this in
            # detailedresults
            else:
                self.detailedresults = str(self.ci.getkey()) + \
                " was disabled. No action was taken."

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as err:
            self.rulesuccess = False
            self.detailedresults = self.detailedresults + "\n" + str(err) + \
            " - " + str(traceback.format_exc())
            self.logdispatch.log(LogPriority.ERROR, self.detailedresults)
        self.formatDetailedResults("fix", self.rulesuccess,
                                   self.detailedresults)
        self.logdispatch.log(LogPriority.INFO, self.detailedresults)
        return self.rulesuccess

    def fixmac(self):
        """Canonical way of setting user umask in mac os x 10.10 and later
        reference: https://support.apple.com/en-us/HT201684


        :return: retval

        :rtype: bool
@author: Breen Malmberg
@change: 01/17/2018 - Breen Malmberg - added this method for newer mac os versions

        """

        retval = True

        user_command = "/bin/launchctl config user umask " + str(self.userumask)
        umask_conf_file = "/private/var/db/com.apple.xpc.launchd/config"

        if not os.path.exists(umask_conf_file):
            os.makedirs(umask_conf_file, 0o755)

        self.ch.executeCommand(user_command)
        if self.ch.getReturnCode() != 0:
            errstr = self.ch.getErrorString()
            retval = False
            self.detailedresults += "\nFailed to set user umask"
            self.logger.log(LogPriority.DEBUG, "Failed to set user umask\n" + str(errstr))

        return retval

    def fixnix(self):
        """
        private method to apply umask config changes to *nix systems

        :return: success
        :rtype: bool
        """

        # defaults
        success = True

        try:

            # iterate through list of user files
            # append the umask config line to each file
            for item in self.userfiledict:
                if not self.userfiledict[item]:
                    self.configFile('umask    ' + str(self.userUmask.getcurrvalue()) + "\n", item, 0o644, [0, 0], True)

            # do any of the root umask conf files exist?
            for item in self.rootfiledict:
                if not self.rootfiledict[item]:
                    self.configFile('umask    ' + str(self.rootUmask.getcurrvalue()) + "\n", item, 0o644, [0, 0], True)

        except Exception:
            raise
        return success

    def searchString(self, searchRE, filepath):
        """
        private method for searching for a given string in a given file

        :param searchRE: 
        :param filepath: 
        :return: retval
        :rtype: bool
        """

        # defaults
        stringfound = False
        noduplicates = True
        entries_found = 0

        try:

            # check if path exists, then open it and read its contents
            if os.path.exists(filepath):
                self.logger.log(LogPriority.DEBUG, "\nFound configuration file: " + str(filepath))
                f = open(filepath, 'r')
                contentlines = f.readlines()
                f.close()

                self.logger.log(LogPriority.DEBUG, "Checking " + str(filepath) + " for configuration...\n")

                # search for the searchRE; if found, set return val to True
                for line in contentlines:
                    if re.search(searchRE, line, re.IGNORECASE):
                        stringfound = True
                        entries_found += 1
                        self.logger.log(LogPriority.DEBUG, "Found correct configuration in file: " + str(filepath))

                if not stringfound:
                    self.logger.log(LogPriority.DEBUG, "File: " + str(filepath) + " did NOT contain correct config.")
                if entries_found > 1:
                    duplicates = entries_found - 1
                    self.detailedresults += "\n" + str(duplicates) + " duplicate entries found in file: " + str(filepath)
                    self.logger.log(LogPriority.DEBUG, str(duplicates) + " duplicate entries found in file: " + str(filepath))
                    noduplicates = False
            else:
                self.logger.log(LogPriority.DEBUG, "Specified file: " + str(filepath) + " does not exist.")

        except Exception:
            raise

        retval = stringfound and noduplicates

        return retval

    def configFile(self, configString, filepath, perms, owner, create=False):
        """private method for adding a configString to a given filepath

        :param configString: 
        :param filepath: 
        :param perms: 
        :param owner: 
        :param create:  (Default value = False)

        """

        umask_entries = 0

        try:

            if os.path.exists(filepath):
                tmpfile = filepath + '.stonixtmp'

                # open the file, read its contents
                f = open(filepath, 'r')
                contentlines = f.readlines()
                f.close()

                for line in contentlines:
                    self.logger.log(LogPriority.DEBUG, "Searching new line for umask entry...")
                    if re.search('^umask', line, re.IGNORECASE):
                        self.logger.log(LogPriority.DEBUG, "Found umask config line. Is it a duplicate?")
                        umask_entries += 1
                        if umask_entries > 1:
                            self.logger.log(LogPriority.DEBUG, "Yes. It is a duplicate. umask_entries = " + str(umask_entries))
                            self.logger.log(LogPriority.DEBUG, "Deleting duplicate line: " + line)
                            contentlines.remove(line)
                        else:
                            self.logger.log(LogPriority.DEBUG, "No. It is not a duplicate. umask_entries = " + str(umask_entries))
                            self.logger.log(LogPriority.DEBUG, "Replacing existing umask config line with the provided one...")
                            contentlines = [c.replace(line, configString) for c in contentlines]

                if umask_entries == 0:
                    # append the config string
                    contentlines.append('\n' + configString)

                # open temporary file, write new contents
                tf = open(tmpfile, 'w')
                tf.writelines(contentlines)
                tf.close()

                # create undo id and dict and save change record
                event = {'eventtype': 'conf',
                         'filepath': filepath}
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                self.statechglogger.recordchgevent(myid, event)
                self.statechglogger.recordfilechange(tmpfile, filepath, myid)

                # set permission and ownership on rewritten file
                os.rename(tmpfile, filepath)
                os.chmod(filepath, perms)
                os.chown(filepath, owner[0], owner[1])
            elif create:
                f = open(filepath, 'w')
                f.write(configString)
                f.close()
                event = {'eventtype': 'creation',
                         'filepath': filepath}
                self.iditerator += 1
                myid = iterate(self.iditerator, self.rulenumber)
                self.statechglogger.recordchgevent(myid, event)
                os.chmod(filepath, perms)
                os.chown(filepath, owner[0], owner[1])

        except Exception:
            raise

    def appendDetailedResults(self, message):
        """
        append given message to self.detailedresults

        :param message: string; ?
        """

        self.detailedresults += '\n' + str(message) + '\n'

    def removeStonixUMASKCodeFromFile(self, filelist=[]):
        """
        Removes the STONIX sets default umask block from list
        of files presented

        :param filelist:  (Default value = [])
        :return: success
        :rtype: bool
        """

        success = True
        bakFile = ""

        for myfile in filelist:
            if os.path.exists(myfile):
                removedBlockSuccessfully = False

                try:
                    rfh = open(myfile, "r")
                except Exception:
                    self.appendDetailedResults("File: " + \
                    str(myfile) + " - Open For Reading Failed - " + \
                    str(traceback.format_exc()))
                else:
                    try:
                        bakFile = "/tmp/removeUMASK-" + \
                        os.path.basename(myfile) + ".bak"
                        wfh = open(bakFile, "w")
                    except Exception:
                        self.logdispatch.log(LogPriority.ERROR, "Failed to create backup for umask file")
                    else:
                        startOfUMASKBlock = False
                        endOfUMASKBlock = False
                        for line in rfh:
                            if "# This block added by STONIX sets default umask" in line:
                                startOfUMASKBlock = True
                            if startOfUMASKBlock and not endOfUMASKBlock:
                                self.logdispatch.log(LogPriority.DEBUG,
                                                     "File: " + str(myfile) + \
                                                     "; Removing Line: '" + \
                                                     line.strip() + "'")
                            else:
                                wfh.write(line)
                            if startOfUMASKBlock and "# End STONIX default umask block." in line:
                                endOfUMASKBlock = True

                        if startOfUMASKBlock and endOfUMASKBlock:
                            removedBlockSuccessfully = True
                        rfh.close()
                        wfh.close()
#####
# Using this method as os.rename (which is used in a file "move") is not
# consistent across platforms, and this is.
                if removedBlockSuccessfully:
### delete myfile
                    os.unlink(myfile)
### copy back to real
                    shutil.copyfile(bakFile, myfile)
                    self.appendDetailedResults("File: " + str(myfile) + \
                        " - Removed STONIX sets default umask block!")
                else:
                    self.appendDetailedResults("File: " + str(myfile) + \
                        " - NO STONIX sets default umask block found in!")
### delete bak
                os.unlink(bakFile)
            else:
                self.appendDetailedResults("File: " + str(myfile) + \
                " does not exist.")
        return success
