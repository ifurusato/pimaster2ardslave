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

from lib.logger import Level
from lib.i2c_master import I2cMaster

# ..............................................................................
def main():

    try:

        _device_id = 0x08  # must match Arduino's SLAVE_I2C_ADDRESS
        _master = I2cMaster(_device_id, Level.INFO)

        if _master is not None: 

            # set it to some very large number if you want it to go on for a long time...
            _loop_count = 10
            _master.test_configuration(_loop_count) # see documentation for hardware configuration

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
