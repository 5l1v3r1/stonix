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

import re
from logdispatcher import LogPriority
from CommandHelper import CommandHelper
import glob


class Portage(object):
    '''
    The template class that provides a framework that must be implemented by
    all platform specific pkgmgr classes.

    :version:
    @author: Derek T Walker 08-06-2012
    @change: Breen Malmberg - 4/18/2017 - minor method edits; added doc strings;
            added logging; added parameter validation; removed detailedresults
            reset in __init__ of this class (should only be done in rule template
            and the individual rules); fixed some pep8 grammar; fixed the location
            of emerge (changed 'emerge' to '/usr/bin/emerge')
    '''

    def __init__(self, logger):
        self.logger = logger
        self.ch = CommandHelper(self.logger)
        self.install = "/usr/bin/emerge "
        self.remove = self.install + " --unmerge "
        self.search = self.install + " --search "

###############################################################################
    def installpackage(self, package):
        '''
        Install a package. Return a bool indicating success or failure.

        @param package: string; Name of the package to be installed, must be 
                recognizable to the underlying package manager.
        @return installed
        @rtype: bool
        @author: Derek T Walker 08-06-2012
        @change: Breen Malmberg - 4/18/2017 - fixed return var logic; fixed
                doc string; added parameter validation; changed detailedresults
                to logging
        '''

        installed = False

        try:

            # parameter validation
            if not package:
                self.logger.log(LogPriority.DEBUG, "Parameter: package was blank!")
                return installed
            if not isinstance(package, basestring):
                self.logger.log(LogPriority.DEBUG, "Parameter: package must be of type string. Got: " + str(type(package)))
                return installed

            self.ch.executeCommand(self.install + package)

            if self.ch.getReturnCode() == 0:
                installed = True
                self.logger.log(LogPriority.DEBUG, "Package " + str(package) + " was successfully installed")
            else:
                self.logger.log(LogPriority.DEBUG, "Failed to install package " + str(package))

        except Exception:
            raise
        return installed

###############################################################################
    def removepackage(self, package):
        '''
        Remove a package. Return a bool indicating success or failure.

        @param package: string; Name of the package to be removed, must be 
                recognizable to the underlying package manager.
        @return: removed
        @rtype: bool
        @author: Derek T Walker 08-6-2012
        @change: Breen Malmberg - 4/18/2017 - minor edit; replaced detailedresults
                with logging; fixed return var logic; added parameter validation;
                fixed doc string
        '''

        removed = False

        try:

            # parameter validation
            if not package:
                self.logger.log(LogPriority.DEBUG, "Parameter: package was blank!")
                return removed
            if not isinstance(package, basestring):
                self.logger.log(LogPriority.DEBUG, "Parameter package must be of type string. Got: " + str(type(package)))
                return removed

            self.ch.executeCommand(self.remove + package)

            if self.ch.getReturnCode() == 0:
                removed = True
                self.logger.log(LogPriority.DEBUG, "Package " + str(package) + " was successfully removed")
            else:
                self.logger.log(LogPriority.DEBUG, "Failed to remove package " + str(package))

        except Exception:
            raise
        return removed

###############################################################################
    def checkInstall(self, package):
        '''
        Check the installation status of a package. Return a bool; 
        True if the package is installed.

        @param package: string; Name of the package whose installation status 
                is to be checked, must be recognizable to the underlying package 
                manager
        @return installed
        @rtype: bool
        @author: Derek T. Walker
        @change: Breen Malmberg - 4/18/2017 - fixed doc string; minor edit;
                replaced detailedresults with logging (detailedresults should
                be handled in the calling rule); changed name of return var;
                added parameter validation
        '''

        installed = False

        try:

            # parameter validation
            if not package:
                self.logger.log(LogPriority.DEBUG, "Parameter: package was blank!")
                return installed
            if not isinstance(package, basestring):
                self.logger.log(LogPriority.DEBUG, "Parameter: package must be of type string. Got: " + str(type(package)))
                return installed

            stringToinstalled = "(.*)" + package + "(.*)"

            f = glob.glob('/var/db/pkg')

            for item in f:
                if re.search(stringToinstalled, item):
                    installed = True
                    break

            if installed:
                self.logger.log(LogPriority.DEBUG, "\nPackage " + str(package) + " is installed")
            else:
                self.logger.log(LogPriority.DEBUG, "\nPackage " + str(package) + " is NOT installed")

        except Exception:
            raise
        return installed

###############################################################################
    def checkAvailable(self, package):
        '''
        check if the specified package is available
        return True if found
        return False if not found

        @param package: string; name of package to check for
        @return: found
        @rtype: bool
        @author: Derek T. Walker
        @change: Breen Malmberg - 4/18/2017 - added doc string; minor edit;
                parameter validation added; added code comments; added logging;
                replaced detailedresults with logging
        '''

        available = False

        try:

            # parameter validation
            if not package:
                self.logger.log(LogPriority.DEBUG, "Parameter: package was blank!")
                return available
            if not isinstance(package, basestring):
                self.logger.log(LogPriority.DEBUG, "Parameter: package must be of type string. Got: " + str(type(package)))
                return available

            self.ch.executeCommand(self.search + package)
            if self.ch.getReturnCode() == 0:
                available = True
                self.logger.log(LogPriority.DEBUG, "Package " + str(package) + " is available to install")
            else:
                self.logger.log(LogPriority.DEBUG, "Package " + str(package) + " is NOT available to install")

        except Exception:
            raise
        return available

    def checkUpdate(self, package=""):
        '''
        check for updates for the specified package
        or if not package is specified, check for
        all updates on the system

        @param package: string; name of package, for which, to check updates
        @return: updatesavail
        @rtype: bool
        @author: Breen Malmberg
        '''

        # defaults
        updatesavail = False
        searchpkg = self.search + package + " &> /dev/null"

        try:

            # I have no idea how to check for ALL updates, with portage/emerge..

            if package:
                # parameter validation
                if not isinstance(package, basestring):
                    self.logger.log(LogPriority.DEBUG, "Parameter package must be of type string. Got: " + str(type(package)))
                    return updatesavail

                # check for updates for specified package
                self.ch.executeCommand(searchpkg)
                if self.ch.getReturnCode() == 100:
                    updatesavail = True
            else:
                self.logger.log(LogPriority.DEBUG, "No package specified. Did NOT search for all updates.")

        except Exception:
            raise
        return updatesavail

    def Update(self, package=""):
        '''
        update either the specified package or all packages
        on the system, if no package is specified

        @param pacakge: string; name of package to update
        @return: updated
        @rtype: bool
        @author: Breen Malmberg
        '''

        # defaults
        updated = True
        updatepkg = self.install + " -avDuN " + package
        updateall = self.install + " -uDU --with-bdeps=y @world"

        try:

            if package:
                self.logger.log(LogPriority.DEBUG, "Attempting to update package " + str(package) + " ...")
                self.ch.executeCommand(updatepkg)
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    updated = False
                    self.logger.log(LogPriority.DEBUG, "Failed to update package " + str(package))
                    self.logger.log(LogPriority.DEBUG, "Error code: " + str(retcode))
            else:
                self.logger.log(LogPriority.DEBUG, "Attempting to update all packages...")
                self.ch.executeCommand(updateall)
                retcode = self.ch.getReturnCode()
                if retcode != 0:
                    updated = False
                    self.logger.log(LogPriority.DEBUG, "Failed to update packages")
                    self.logger.log(LogPriority.DEBUG, "Error code: " + str(retcode))

        except Exception:
            raise
        return updated

###############################################################################
    def getInstall(self):
        return self.install

###############################################################################
    def getRemove(self):
        return self.remove

    def getSearch(self):
        return self.search
