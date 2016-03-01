#! /usr/bin/python

'''
Created on Dec 14, 2011

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

@author: dkennel
@change: 2015-02-26 - Reformatted to work with stonixtest
'''
import os
import unittest
import src.stonix_resources.environment as environment
import src.stonix_resources.conffile as conffile
import src.tests.lib.logdispatcher_lite as logdispatcher


class zzzTestFrameworkconffile(unittest.TestCase):

    def setUp(self):
        # create sample test files
        env = environment.Environment()
        logger = logdispatcher.LogDispatcher(env)
        tdsource = {'key1': 'val1', 'key2': 'val2', 'key3': 'val3'}
        self.td2source = {'key1': 'val1', 'key2': 'val2', 'key3': 'val6'}
        tcopeneq = open('test1.conf', 'a')
        tcclosedeq = open('test2.conf', 'a')
        tcspace = open('test3.conf', 'a')
        for key in tdsource:
            line1 = key + ' = ' + tdsource[key] + '\n'
            tcopeneq.write(line1)
            line2 = key + '=' + tdsource[key] + '\n'
            tcclosedeq.write(line2)
            line3 = key + ' ' + tdsource[key] + '\n'
            tcopeneq.write(line1)
            tcclosedeq.write(line2)
            tcspace.write(line3)
        tcopeneq.close()
        tcclosedeq.close()
        tcspace.close()
        self.to_openeq = conffile.ConfFile('test1.conf', 'test1.conf.tmp',
                                           'openeq', tdsource, env, logger)
        self.to_closedeq = conffile.ConfFile('test2.conf', 'test2.conf.tmp',
                                             'closedeq', tdsource, env, logger)
        self.to_space = conffile.ConfFile('test3.conf', 'test3.conf.tmp',
                                          'space', tdsource, env, logger)
    def tearDown(self):
        os.remove('test1.conf')
        os.remove('test2.conf')
        os.remove('test3.conf')

    def testOpenEqIsPresent(self):
        self.failUnless( self.to_openeq.ispresent() )
        
    def testClosedEqIsPresent(self):
        self.failUnless( self.to_closedeq.ispresent() )
        
    def testSpaceIsPresent(self):
        self.failUnless( self.to_space.ispresent() )
        
    def testOpenEqAudit(self):
        self.failUnless( self.to_openeq.audit() )
        
    def testClosedEqAudit(self):
        self.failUnless( self.to_openeq.audit() )
        
    def testSpaceAudit(self):
        self.failUnless( self.to_space.audit() )


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()