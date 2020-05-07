#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-04
#
# This requires installation of pigpio, e.g.:
#
#   % sudo pip3 install pigpio
#

import sys, time, traceback, itertools
from colorama import init, Fore, Style
init()

from lib.logger import Level
from lib.i2c_master import I2cMaster

# ..............................................................................
def main():

    try:

        _device_id = 0x08  # must match Arduino's SLAVE_I2C_ADDRESS
        _master = I2cMaster(_device_id, Level.DEBUG)
        _master.testConfiguration()
#       _master.echo_test()

    except KeyboardInterrupt:
        self._log.warning('Ctrl-C caught; exiting...')
    finally:
        _master.close()


if __name__== "__main__":
    main()

#EOF
