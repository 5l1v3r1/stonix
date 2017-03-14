#!/bin/env python
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
Created on Feb 28, 2014

build script for stonix package on debian systems

@author Breen Malmberg
@change: Breen Malmberg - 3/14/2017 - updated controltext and
        changelog text
'''

import os
import re
import glob
import shutil
import traceback

from src.stonix_resources.localize import STONIXVERSION


curruserid = os.geteuid()

if curruserid != 0:
    print "This script must be run as root or with sudo"
    exit

# Defaults
stonixversion = STONIXVERSION

# change package name to stonix-red if
# packaging for the red network
controltext = '''Package: stonix
Version: ''' + str(stonixversion) + '''
Architecture: all
Maintainer: STONIX Dev's <stonix-dev@lanl.gov>
Depends: python
Section: python
Priority: extra
Description: ''' + str(stonixversion) + ''' release of STONIX hardening tool for Ubuntu
'''

changelogtext = str(stonixversion) + ''' BETA release notes:
[Packager needs to modify these to reflect current release notes]
'''

copyrighttext = '''###############################################################################
#                                                                             #
# Copyright, 2008, Los Alamos National Security, LLC.                         #
#                                                                             #
# This software was produced under a U.S. Government contract by Los Alamos   #
# National Laboratory, which is operated by Los Alamos National Security,     #
# LLC., under Contract No. DE-AC52-06NA25396 with the U.S. Department of      #
# Energy.                                                                     #
#                                                                             #
# The U.S. Government is licensed to use, reproduce, and distribute this      #
# software. Permission is granted to the public to copy and use this software #
# without charge, provided that this Notice and any statement of authorship   #
# are reproduced on all copies.                                               #
#                                                                             #
# Neither the Government nor the Los Alamos National Security, LLC., makes    #
# any warranty, express or implied, or assumes any liability or               #
# responsibility for the use of this software.                                #
#                                                                             #
###############################################################################
'''

# change the ending of the -1.noarch and -1.noarch.deb strings to
# -red-1.noarch and -red-1.noarch.deb if packaging for the red network
sourcedir = os.path.dirname(os.path.realpath(__file__)) + "/src/"
builddir = '/stonix-' + str(stonixversion) + '-1.noarch'
pkgname = 'stonix-' + str(stonixversion) + '-1.noarch.deb'
debiandir = builddir + '/DEBIAN/'
bindir = os.path.join(builddir, 'usr/bin/')
etcdir = os.path.join(builddir, 'etc/')

filesneeded = {debiandir + 'control': controltext,
               debiandir + 'changelog': changelogtext,
               debiandir + 'copyright': copyrighttext}

try:

    if os.path.exists(sourcedir + 'stonix_resources/rules'):
        listofdirs = glob.glob(sourcedir + 'stonix_resources/rules/*.py')
        listoffiles = []
        for item in listofdirs:
            listoffiles.append(os.path.basename(item))
        discardfiles = []
        if os.path.exists('/discardfiles'):
            f = open('/discardfiles', 'r')
            contentlines = f.readlines()
            f.close()
            for line in contentlines:
                line = line.strip()
                if line in listoffiles:
                    os.system('rm -f ' + sourcedir +
                              'stonix_resources/rules/' + line)
        else:
            exit
    else:
        exit

    if not os.path.exists(bindir):
        os.makedirs(bindir, 0o755)
        os.chown(os.path.join(builddir, '/usr'), 0, 0)
        os.chown(bindir, 0, 0)
    if not os.path.exists(debiandir):
        os.makedirs(debiandir, 0o755)
        os.chown(debiandir, 0, 0)
    if not os.path.exists(etcdir):
        os.makedirs(etcdir, 0o755)
        os.chown(etcdir, 0, 0)

    if not os.path.exists(sourcedir):
        print "Directory " + sourcedir + " not found"
        exit

    for item in filesneeded:
        if not os.path.exists(item):
            f = open(item, 'w')
            f.write(filesneeded[item])
            f.close()
            os.chmod(item, 0o644)
        else:
            f = open(item, 'r')
            contents = f.read()
            f.close()
            if not re.search(filesneeded[item], contents):
                f = open(item, 'w')
                f.write(filesneeded[item])
                f.close()
                os.chmod(item, 0o644)

    f = open(etcdir + 'stonix.conf', 'w')
    f.write('')
    f.close()
    os.chmod(etcdir + 'stonix.conf', 0o644)
    os.chown(etcdir + 'stonix.conf', 0, 0)

    if not os.path.exists(bindir + 'stonix_resources'):
        shutil.copytree(sourcedir + 'stonix_resources',
                        bindir + 'stonix_resources')

    if not os.path.exists(builddir + 'usr/share/man/man8/stonix.8'):
        shutil.copytree(sourcedir + 'usr/share', builddir + '/usr/share')
        os.chmod(builddir + '/usr/share', 0o644)

    for dirName, _, fileList in os.walk(bindir):
        fullDirName = os.path.join(os.path.abspath(bindir), dirName)
        os.chmod(fullDirName, 0o755)
        os.chown(fullDirName, 0, 0)
        for fname in fileList:
            fullFName = os.path.join(os.path.abspath(bindir), dirName, fname)
            if os.path.isfile(fullFName):
                os.chmod(fullFName, 0o644)
                os.chown(fullFName, 0, 0)

    if not os.path.exists(bindir + 'stonix.py'):
        shutil.copy2(sourcedir + 'stonix.py', bindir + 'stonix.py')
    os.chmod(bindir + 'stonix.py', 0o755)

    os.system('ln -s /usr/bin/stonix.py ' + bindir + 'stonix')

    os.system('dpkg-deb -b ' + builddir)

except OSError as err:
    print traceback.format_exc()
