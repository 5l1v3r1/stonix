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

@author bemalmbe
'''

import os
import re
import glob
import shutil

from src.stonix_resources.localize import STONIXVERSION


curruserid = os.geteuid()

if curruserid != 0:
    print "This script must be run as root or with sudo"
    exit

#defaults
stonixversion = STONIXVERSION

controltext = '''Package: stonix
Version: ''' + str(stonixversion) + '''
Architecture: all
Maintainer: Breen Malmberg <bemalmbe@lanl.gov>
Depends: python-appindicator
Section: python
Priority: extra
Description: ''' + str(stonixversion) + ''' release of STONIX hardening tool for Ubuntu
X-Python-Version: = 2.7
'''

changelogtext = str(stonixversion) + ''' ALPHA release notes:
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

sourcedir = '/Dylan/src/'
builddir = '/stonix-' + str(stonixversion) + '-1.noarch'
pkgname = 'stonix-' + str(stonixversion) + '-1.noarch.deb'
debiandir = builddir + '/DEBIAN/'
bindir = os.path.join(builddir, 'usr/bin/')
etcdir = os.path.join(builddir, 'etc/')

filesneeded =  {debiandir + 'control': controltext,
                debiandir + 'changelog': changelogtext,
                debiandir + 'copyright': copyrighttext}

try:

    if os.path.exists('/Dylan/src/stonix_resources/rules'):
        listofdirs = glob.glob('/Dylan/src/stonix_resources/rules/*.py')
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
                    os.system('rm -f ' + '/Dylan/src/stonix_resources/rules/' + line)
        else:
            exit
    else:
        exit

    if not os.path.exists(bindir):
        os.makedirs(bindir,0755)
        os.chown(os.path.join(builddir, '/usr'),0,0)
        os.chown(bindir,0,0)
    if not os.path.exists(debiandir):
        os.makedirs(debiandir,0755)
        os.chown(debiandir,0,0)
    if not os.path.exists(etcdir):
        os.makedirs(etcdir,0755)
        os.chown(etcdir,0,0)
        
    if not os.path.exists(sourcedir):
        print "Source directory not found (/Dylan/src/)"
        exit
        
    for item in filesneeded:
        if not os.path.exists(item):
            f = open(item,'w')
            f.write(filesneeded[item])
            f.close()
            os.chmod(item,0644)
        else:
            f = open(item,'r')
            contents = f.read()
            f.close()
            if not re.search(filesneeded[item],contents):
                f = open(item,'w')
                f.write(filesneeded[item])
                f.close()
                os.chmod(item,0644)
                
    f = open(etcdir + 'stonix.conf','w')
    f.write('')
    f.close()
    #os.chmod(etcdir+'stonix.conf',0644)
    os.chown(etcdir + 'stonix.conf',0,0)

    if not os.path.exists(bindir + 'stonix_resources'):
        shutil.copytree(sourcedir + 'stonix_resources',
                        bindir + 'stonix_resources')

    if not os.path.exists(builddir + 'usr/share/man/man8/stonix.8'):
        shutil.copytree(sourcedir + 'usr/share', builddir + '/usr/share')

    #os.chmod(bindir + 'stonix_resources',0755)
    if not os.path.exists(bindir + 'stonix.py'):
        shutil.copy2(sourcedir + 'stonix.py', bindir + 'stonix.py')
    #os.chmod(bindir + 'stonix.py',0700)

    os.system('ln -s /usr/bin/stonix.py ' + bindir + 'stonix')

    os.system('dpkg-deb -b ' + builddir)
    #if os.path.exists('/' + pkgname):
        #os.chmod('/' + pkgname, 0550)
        #os.system('dpkg -i /' + pkgname)
    #else:
    #    print "Could not find target .deb package to install " + pkgname
    #    exit

except OSError as err:
    print str(err.strerror)
