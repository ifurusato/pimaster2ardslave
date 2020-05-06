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
from smbus2 import SMBus
from colorama import init, Fore, Style
init()

try:
    import pigpio
    _pi = pigpio.pi()
    print('import            :' + Fore.BLACK + ' INFO  : imported pigpio.' + Style.RESET_ALL)
except Exception as e:
    print('import            :' + Fore.RED + ' ERROR : failed to import pigpio: {}'.format(e) + Style.RESET_ALL)
    sys.exit(1)

from lib.logger import Logger, Level

# ..............................................................................

DEVICE_ID = 0x1A  # must match Arduino's SLAVE_I2C_ADDRESS
ECHO_TEST = False # echo communications test

# ..............................................................................
def write_i2c_data(handle, data):
    '''
        Write an int as two bytes (LSB, MSB) to the I2C device at the specified handle.
    '''
    byteArray = [ data, ( data >> 8 ) ]
    _pi.i2c_write_byte(handle, byteArray[0])
    _pi.i2c_write_byte(handle, byteArray[1])
    print('write_i2c_data    :' + Fore.CYAN + ' DEBUG : ' + Fore.BLACK + 'hi: {:08b};\t lo: {:08b};\t sent data: {}'.format(byteArray[1], byteArray[0], data) + Style.RESET_ALL)


# ..............................................................................
def read_i2c_data(handle):
    '''
        Read two bytes (LSB, MSB) from the I2C device at the specified handle, returning the value as an int.
    '''
    ( byte_count, byte_array) = _pi.i2c_read_device(handle, 2)
    low_byte  = byte_array[0]
    high_byte = byte_array[1]
    _data = low_byte
    _data += ( high_byte << 8 )
    print('read_i2c_data     :' + Fore.CYAN + ' DEBUG : ' + Fore.BLUE + 'read {:d} bytes: hi: {:08b};\t lo: {:08b};\t read data: {}'.format(byte_count, high_byte, low_byte, _data) + Style.RESET_ALL)
    return _data


def test_coms(handle):
    _data = [ 0, 1, 2, 4, 32, 63, 64, 127, 128, 254, 255 ]
    for i in range(0,len(_data)):
        data_to_send = _data[i]
        write_i2c_data(handle, data_to_send)
        received_data = read_i2c_data(handle)
#       assert data_to_send == received_data

# ..............................................................................
def main():
    try:

        _counter = itertools.count()
        _log = Logger("ard", Level.DEBUG)
        _log.info('configuring...')

        _handle = _pi.i2c_open(1, DEVICE_ID) # open device at address 0x1A on bus 1
        _log.info('pigpio configured successfully.')

        AUTORANGE_ON  = 241
        AUTORANGE_OFF = 240
        _loop_count = 0

        # 0-31:     return the output data for that pin assignment, -1 if not assigned
        # 32-63:    set the pin (n-32) as an INPUT pin, return pin number
        # 64-95:    set the pin (n-64) as an INPUT_PULLUP pin, return pin number
        # 96-127:   set the pin (n-96) as an OUTPUT pin, return pin number
        # 128-159:  write output for pin (n-128) to LOW, return 0
        # 160-191:  write output for pin (n-128) to HIGH, return 1
        # 192-223:  echo input
        # 224:      return loop count
        # 230:      return IR analog minimum range
        # 231:      return IR analog maximum range
        # 232:      disable auto-ranging, return SUCCESS_VALUE
        # 233:      enable auto-ranging, return SUCCESS_VALUE
        # 255:      return error value

        # ..................................................
        if ECHO_TEST:
            try:
                _log.info('starting echo test...')
                test_coms(_handle)
                _pi.i2c_close(_handle) # close device
                _log.info('echo test complete; exiting.')
            except Exception as e:
                _log.error('error in echo test: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)
            finally:
                sys.exit(0)
        # ..................................................


        # =============================================

        # pinMode(7, INPUT);  // set the IR digital pin as INPUT
        write_i2c_data(_handle, 7+32)

        # pinMode(8, INPUT);  // set the IR analog pin as INPUT
        write_i2c_data(_handle, 8+32)

        # pinMode(6, INPUT);  // set the button pin as INPUT_PULLUP
        write_i2c_data(_handle, 6+64)

        # pinMode(5, OUTPUT);    // set the LED pin as OUTPUT
        write_i2c_data(_handle, 5+96)

    #   data_array = [ 0, 1, 2, 5, 6, 7, 8, 192, 201, 223, 224, 230, 231, 254, 255 ]
        data_array = [ 0, 1, 2, 5, 6, 7, 8, 192, 201, 223 ]
        while True:
            count = next(_counter)
            for i in range(0,len(data_array)):

                print('')

                # write data to Arduino ..................................
                data_to_send = data_array[i];
                write_i2c_data(_handle, data_to_send)

                # read data from Arduino .................................
                received_data = read_i2c_data(_handle)

    #           if i == -1:
    #               _log.info('FIXED(-1):       \t{:02d}'.format(received_data))
                if i == 0:
                    _log.info('FIXED(0):        \t{:02d}'.format(received_data))
                elif i == 1:
                    _log.info('FIXED(1):        \t{:02d}'.format(received_data))
                elif i == 2:
                    _log.info('FIXED(2):        \t{:02d}'.format(received_data))

                elif i == 5:
                    _log.info('LED(5):          \t' + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(received_data))
                elif i == 6:
                    _log.info('BUTTON(6):       \t' + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(received_data))
                elif i == 7:
                    _log.info('DIGITAL IR(7):   \t' + Fore.YELLOW + Style.BRIGHT  + '{:d}'.format(received_data))
                elif i == 8:
                    _log.info('ANALOG IR(8):    \t' + Fore.CYAN + Style.BRIGHT    + '{:d}'.format(received_data))

                elif i == 224:
                    _log.info('LOOP COUNT(224): \t{:02d}'.format(received_data))
                    _loop_count = received_data
                elif i == 230:
                    _log.info('IR_MIN(230):     \t{:02d}'.format(received_data))
                elif i == 231:
                    _log.info('IR_MAX(231):     \t{:02d}'.format(received_data))
                elif i == 232: # turn on auto-ranging .................................
                    _log.info('AUTORANGE ON:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                elif i == 233: # turn off auto-ranging .................................
                    _log.info('AUTORANGE OFF:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))

                elif i == 192: # echo .................................
                    _log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                elif i == 201: # echo .................................
                    _log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                elif i == 223: # echo .................................
                    _log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))


                else:
                    _log.error('data sent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                    if received_data == data_to_send:
                        _log.info(Fore.YELLOW+'success! sent: {:02d}; received: {:02d}'.format(data_to_send, received_data))
                    else:
                        _log.error('fail! sent: {:02d}; received: {:02d}'.format(data_to_send, received_data))

            if ( _loop_count % 1000 ) == 0:
                _log.info('reset auto-ranging.')
    #           _p1.i2c_write_device(_handle, AUTORANGE_OFF);
                write_i2c_data(_handle, AUTORANGE_OFF)
    #           wip.wiringPiI2CWrite(fd, AUTORANGE_OFF);
                time.sleep(0.1)
                write_i2c_data(_handle, AUTORANGE_ON)
    #           _pi.i2c_write_device(_handle, AUTORANGE_ON);
    #           wip.wiringPiI2CWrite(fd, AUTORANGE_ON);

            _log.info(Fore.BLACK + Style.DIM + 'processed: {:04d}\n'.format(count))
    #       time.sleep(0.25)
            time.sleep(2.0)

            # TEMP
            _pi.i2c_close(_handle) # close device
            sys.exit(1)

        _pi.i2c_close(_handle) # close device
        _log.info('complete.')

    except KeyboardInterrupt:
        _log.warning('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('error communicating via wiring pi: {}'.format(e))
        traceback.print_exc(file=sys.stdout)


if __name__== "__main__":
    main()

#EOF
