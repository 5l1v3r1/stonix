#!/usr/bin/env python3 -u
"""
Test of the Linux tmpfs ramdisk

@author: Roy Nielsen
"""

#--- Native python libraries
import re
import os
import sys
import time
import unittest
import tempfile
import ctypes as C
from datetime import datetime

#--- non-native python libraries in this source tree
from tests.genericRamdiskTest import GenericRamdiskTest
from lib.loggers import CyLogger
from lib.loggers import LogPriority as lp
from lib.libHelperExceptions import NotValidForThisOS

#####
# Load OS specific Ramdisks
if sys.platform.startswith("darwin"):
    #####
    # For Mac
    from macRamdisk import RamDisk, detach
elif sys.platform.startswith("linux"):
    #####
    # For Linux
    from linuxTmpfsRamdisk import RamDisk, unmount

@unittest.skipUnless(sys.platform.startswith("linux"), "This test is not valid on this OS")
class test_linuxTmpfsRamdisk(GenericRamdiskTest):
    '''Test for the Linux tmpfs Ramdisk interface
    
    @author: Roy Nielsen


    '''

    @classmethod
    def setUpInstanceSpecifics(self):
        '''Initializer'''
        # Start timer in miliseconds
        self.test_start_time = datetime.now()

        self.logger = CyLogger()

        #####
        # Initialize the helper class
        self.initializeHelper = False

    def setUp(self):
        '''This method runs before each test run.
        
        @author: Roy Nielsen


        '''
        pass


###############################################################################
##### Helper Classes

    def format_ramdisk(self):
        '''Format Ramdisk'''
        self.my_ramdisk._format()

###############################################################################
##### Method Tests

    def test_linuxTmpfsRamdiskFirstTest(self):
        ''' '''
        pass

    ##################################

    def test_linuxTmpfsRamdiskSecondTest(self):
        ''' '''
        pass


###############################################################################
##### unittest Tear down
    @classmethod
    def tearDownClass(self):
        '''disconnect ramdisk'''
        pass

###############################################################################

