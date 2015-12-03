#!/usr/bin/env python
'''
Created on Sep 18, 2015
Boot security program to turn off wifi, bluetooth, cameras and microphones.
This is most likely called from a job scheduled by the stonix program.

@author: dkennel
@version: 1.0
'''

import subprocess
import os
import networksetup
from CommandHelper import CommandHelper
from logdispatcher import LogDispatcher
from environment import Environment


class logmock:
    '''
    This is a mock class to deal with the fact that the networksetup object
    expects the logdispatcher at instantiation.
    '''

    def log(self, prio, message):
        pass

    def reporterr(self, errmsg, prefix):
        pass


def main():
    enviro = Environment()
    logger = LogDispatcher(enviro)
    if os.path.exists('/usr/bin/osascript'):
        setlevels = "/usr/bin/osascript -e 'set volume input volume 0'"

    if setlevels != None:
        try:
            proc = subprocess.Popen(setlevels, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, shell=True)
        except Exception:
            pass
    # Network Setup handles the Bluetooth and Wifi
    mocklog = logmock()
    netsetup = networksetup.networksetup(mocklog)
    netsetup.startup()

    # Try to corral the camera
    # This block commented out because the camera does not come back when these
    # kexts are reloaded. We're still working a good way to toggle the camera
    # on and off for the Mac. We want to be able to toggle it as video
    # conferencing is a common use case.
    isight = 'Apple_iSight.kext'
    camerainterface = 'AppleCameraInterface.kext'
    unload = '/sbin/kextunload'

    if os.path.exists(unload):
        try:
            ch = CommandHelper(logger)
            cmd = [unload, isight]
            ch.executeCommand(cmd)
            cmd = [unload, camerainterface]
            ch.executeCommand(cmd)
        except Exception:
            pass

if __name__ == '__main__':
    main()
