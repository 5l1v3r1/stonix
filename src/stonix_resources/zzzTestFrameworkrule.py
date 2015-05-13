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

Test suite for the rule.py base class.
@change: 09/24/2010 dkennel Original Implementation
@change: 03/19/2014 pep8 compliance
@change: 2015/01/13 dkennel refactor of isApplicable() and associated test
@author: dkennel

'''
import unittest
import re
import rule
import environment
import logdispatcher
import StateChgLogger
import configuration


class zzzTestFramework(unittest.TestCase):

    def setUp(self):
        myenv = environment.Environment()
        config = configuration.Configuration(myenv)
        logger = logdispatcher.LogDispatcher(myenv)
        state = StateChgLogger.StateChgLogger(logger, myenv)
        self.to = rule.Rule(config, myenv, logger, state)

    def tearDown(self):
        pass

    def testgetrulenum(self):
        '''GetRuleNum, Test that a valid rule number is returned '''
        self.failUnless(re.search('[0-9]', str(self.to.getrulenum())))

    def testgetrulename(self):
        '''GetRuleName, Test that a valid rule name was returned'''
        self.failUnless(re.search('[A-Za-z]', self.to.getrulename()))

    def testgetmandatory(self):
        '''GetMandatory, Test that a bool is returned'''
        self.failIf(self.to.getmandatory() not in [True, False])

    def testiscompliant(self):
        '''iscompliant, test that a valid bool is returned'''
        self.failIf(self.to.iscompliant() not in [True, False])

    def testgetisrootrequired(self):
        '''getisrootrequired, Test that a valid bool is returned'''
        self.failIf(self.to.getisrootrequired() not in [True, False])

    def testgethelptext(self):
        '''gethelptext, test to see that the prototype help string is
        returned'''
        self.failUnless(re.search('This is the default help text',
                                  self.to.gethelptext()))

    def testgetdetailedresults(self):
        '''getdetailedresults, should return the prototype text.'''
        self.failUnless(re.search('This is the default detailed results text',
                                  self.to.getdetailedresults()))

    def testgetrulesuccess(self):
        '''getrulesuccess, in concrete rules this returns a bool. '''
        self.failIf(self.to.getrulesuccess() not in [True, False])

    def testcheckconfigopts(self):
        '''checkconfigopts, in the base class this always returns true'''
        self.failUnlessEqual(self.to.checkconfigopts(), True)

    def testisdatabaserule(self):
        '''isdatabaserule, should return a bool indicating whether or not
        the rule is a db rule. The base class should return False'''
        self.failUnlessEqual(self.to.isdatabaserule(), False)

    def testisapplicable(self):
        '''isapplicable, in concrete rules should return a bool indicating
        whether or not the rule applies to the current platform. In the base
        class it always returns True.'''
        self.failUnlessEqual(self.to.isapplicable(), True)
        environ = environment.Environment()
        myfamily = environ.getosfamily()
        myostype = environ.getostype()
        myver = environ.getosver()
        if re.search('Red Hat Enterprise Linux', myostype):
            self.to.applicable = {'type': 'black', 'family': 'linux'}
            self.failUnlessEqual(self.to.isapplicable(), False)
            self.to.applicable = {'type': 'white', 'family': 'linux'}
            self.failUnlessEqual(self.to.isapplicable(), True)
            # FIXME Assertion error testing commented out. Unittest fails
            # to recognize the raised error correctly. This may be due to
            # differing import paths.
            #self.to.applicable = {'type': 'brown', 'family': 'linux'}
            #self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Red Hat Enterprise Linux': ['6.0', '+']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Red Hat Enterprise Linux': ['6.0', '+']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Red Hat Enterprise Linux': ['6.0', '+', '7.0']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Red Hat Enterprise Linux': ['7.0', '-']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Red Hat Enterprise Linux': ['7.0', '-']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Red Hat Enterprise Linux': ['7.0', '-', '6.0']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Red Hat Enterprise Linux': ['7.0', 'r', '5.0']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Red Hat Enterprise Linux': ['7.0', 'r', '5.0']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Red Hat Enterprise Linux': ['7.0', 'r']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            if myver == '7.0':
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0', '6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0', '6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
            if myver == '6.0':
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0', '6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0', '6.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Red Hat Enterprise Linux': ['7.0']}}
                self.failUnlessEqual(self.to.isapplicable(), True)

        if re.search('Mac OS X', myostype):
            self.to.applicable = {'type': 'black', 'family': 'darwin'}
            self.failUnlessEqual(self.to.isapplicable(), False)
            self.to.applicable = {'type': 'white', 'family': 'darwin'}
            self.failUnlessEqual(self.to.isapplicable(), True)
            #self.to.applicable = {'type': 'brown', 'family': 'linux'}
            #self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Mac OS X': ['10.9', '+']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Mac OS X': ['10.9', '+']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Mac OS X': ['10.9', '+', '7.0']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Mac OS X': ['10.10.10', '-']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Mac OS X': ['10.10.10', '-']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Mac OS X': ['7.0', '-', '10.9']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            self.to.applicable = {'type': 'white',
                                  'os' :{'Mac OS X': ['10.10.10', 'r', '10.8']}}
            self.failUnlessEqual(self.to.isapplicable(), True)
            self.to.applicable = {'type': 'black',
                                  'os' :{'Mac OS X': ['10.10.10', 'r', '10.8']}}
            self.failUnlessEqual(self.to.isapplicable(), False)
#             self.to.applicable = {'type': 'white',
#                                   'os' :{'Mac OS X': ['7.0', 'r']}}
#             self.assertRaises(AssertionError, self.to.isapplicable())
            if myver == '10.10.3':
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.10.3']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.10.3']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.10.3', '10.9']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.10.3', '10.9']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.9']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.9']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
            if myver == '10.9.5':
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.9.5']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.9.5']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.10.3', '10.9.5']}}
                self.failUnlessEqual(self.to.isapplicable(), True)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.10.3', '10.9.5']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'white',
                                      'os' :{'Mac OS X': ['10.10.3']}}
                self.failUnlessEqual(self.to.isapplicable(), False)
                self.to.applicable = {'type': 'black',
                                      'os' :{'Mac OS X': ['10.10.3']}}
                self.failUnlessEqual(self.to.isapplicable(), True)

    def testgetcurrstate(self):
        '''getcurrstate in concrete rules is not valid until report() has been
        called. In the base class it always returns notconfigured.'''
        self.failUnlessEqual(self.to.getcurrstate(), 'notconfigured')

    def testgettargetstate(self):
        '''gettargetstate should return "configured" unless it has been set
        otherwise.'''
        self.failUnlessEqual(self.to.gettargetstate(), 'configured')

    def testsettargetstate(self):
        '''To test the set target state function we call the setter and then
        read back the new value with the getter.'''
        self.to.settargetstate('notconfigured')
        self.failUnlessEqual(self.to.gettargetstate(), 'notconfigured')

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
