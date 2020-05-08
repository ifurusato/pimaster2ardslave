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
# This tests that the Raspberry Pi and Arduino can talk to each other, and
# doesn't require any sensors or additional hardware other than the I²C
# between the two boards. Communication is over address 0x08, so be sure
# that is not being used by another device. For the test to function be sure
# to set the 'isEchoTest' flag on the Arduino's i2cSlave.ino sketch to true,
# otherwise it won't echo the requests but rather respond to them.
#
# This requires installation of pigpio, e.g.:
#
#   % sudo pip3 install pigpio
#

from lib.logger import Level
from lib.i2c_master import I2cMaster

# ..............................................................................
def main():

    try:

        _device_id = 0x08  # must match Arduino's SLAVE_I2C_ADDRESS
        _master = I2cMaster(_device_id, Level.INFO)

        if _master is not None:

            _master.test_echo() # requires 'isEchoTest' on Arduino to be set true

        else:
            raise Exception('unable to establish contact with Arduino on address 0x{:02X}'.format(_device_id))

    except KeyboardInterrupt:
        self._log.warning('Ctrl-C caught; exiting...')
    finally:
        if _master:
            _master.close()


if __name__== "__main__":
    main()

#EOF
