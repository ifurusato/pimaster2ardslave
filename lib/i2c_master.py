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

from lib.logger import Logger, Level

# ..............................................................................
class I2cMaster():
    '''
        A Raspberry Pi Master for a corresponding Arduino Slave.

        Parameters:
          device_id:  the I²C address over which the master and slave communicate
          level:      the log level, e.g., Level.INFO
    '''
    def __init__(self, device_id, level):
        super().__init__()
        self._log = Logger('i²cmaster-0x{:02x}'.format(device_id), level)
        self._device_id = device_id
        self._log.debug('initialising to communicate over I²C address 0x{:02X}...'.format(device_id))
        try:
            import pigpio
            self._pi = pigpio.pi()
            self._log.debug('imported pigpio.')
        except ImportError as ie:
            self._log.error('failed to import pigpio: {}. You may need to install it via:\n\n  % sudo pip3 install pigpio\n'.format(ie))
            sys.exit(1)
        except Exception as e:
            self._log.error('failed to instantiate pi: {}'.format(ie))
            sys.exit(2)
        self._handle = self._pi.i2c_open(1, device_id) # open device at address 0x1A on bus 1
        self._log.debug('pigpio configured successfully for I²C device at address 0x{:02X} with handle {:d}.'.format(device_id, self._handle))
        self._counter = itertools.count()
        self._loop_count = 0  # currently only used in testing
        self._closed = False
        self._log.info('ready.')


    # ..............................................................................
    def read_i2c_data(self):
        '''
            Read two bytes (LSB, MSB) from the I²C device at the specified handle, returning the value as an int.
        '''
        ( byte_count, byte_array) = self._pi.i2c_read_device(self._handle, 2)
        low_byte  = byte_array[0]
        high_byte = byte_array[1]
        _data = low_byte
        _data += ( high_byte << 8 )
        self._log.debug(Fore.BLUE + 'read {:d} bytes: hi: {:08b};\t lo: {:08b};\t read data: {}'.format(byte_count, high_byte, low_byte, _data))
        return _data


    # ..........................................................................
    def write_i2c_data(self, data):
        '''
            Write an int as two bytes (LSB, MSB) to the I²C device at the specified handle.
        '''
        byteArray = [ data, ( data >> 8 ) ]
        self._pi.i2c_write_byte(self._handle, byteArray[0])
        self._pi.i2c_write_byte(self._handle, byteArray[1])
        self._log.debug(Fore.BLACK + 'sent 2 bytes: hi: {:08b};\t lo: {:08b};\t sent data: {}'.format(byteArray[1], byteArray[0], data))


    # ..........................................................................
    def close(self):
        '''
           Close the I²C device at the specified handle.
        '''
        self._log.debug('closing I²C device at handle {}...'.format(self._handle))
        if not self._closed:
            try:
                self._closed = True
                self._pi.i2c_close(self._handle) # close device
                self._log.debug('I²C device at handle {} closed.'.format(self._handle))
            except Exception as e:
                self._log.error('error closing master: {}'.format(e))
        else:
            self._log.debug('I²C device at handle {} closed.'.format(self._handle))


    # ..........................................................................
    def echo_test(self):
        '''
            Performs a simple test, sending a series of bytes to teh slave, then
            reading the return values. The Arduino slave's 'isEchoTest' boolean
            must be set to true.
        '''
        try:
            self._log.info('starting echo test...')
            _data = [ 0, 1, 2, 4, 32, 63, 64, 127, 128, 254, 255 ]
            for i in range(0,len(_data)):
                data_to_send = _data[i]
                self.write_i2c_data(data_to_send)
                received_data = self.read_i2c_data()
                if data_to_send != received_data:
                    self._log.warning('echo failed: {} != {}'.format(data_to_send, received_data))
                else:
                    self._log.info('echo okay: {} == {}'.format(data_to_send, received_data))

            self._pi.i2c_close(self._handle) # close device
            self._log.info('echo test complete.')
        except Exception as e:
            self._log.error('error in echo test: {}'.format(e))
            traceback.print_exc(file=sys.stdout)


    # ..........................................................................
    def test(self):
        try:
    
            AUTORANGE_DISABLE = 232
            AUTORANGE_ENABLE  = 233
    
            # configure some pins...
            # pinMode(7, INPUT);  // set the IR digital pin as INPUT
            self.write_i2c_data(7+32)
            # pinMode(8, INPUT);  // set the IR analog pin as INPUT
            self.write_i2c_data(8+32)
            # pinMode(6, INPUT);  // set the button pin as INPUT_PULLUP
            self.write_i2c_data(6+64)
            # pinMode(5, OUTPUT);    // set the LED pin as OUTPUT
            self.write_i2c_data(5+96)
    
        #   data_array = [ 0, 1, 2, 5, 6, 7, 8, 192, 201, 223, 224, 230, 231, 254, 255 ]
            data_array = [ 0, 1, 2, 5, 6, 7, 8, 192, 201, 223 ]
            while True:
                count = next(self._counter)
                for i in range(0,len(data_array)):
    
                    # write data to Arduino ..................................
                    data_to_send = data_array[i];
                    self.write_i2c_data(data_to_send)
    
                    # read data from Arduino .................................
                    received_data = self.read_i2c_data()
    
        #           if i == -1:
        #               self._log.info('FIXED(-1):       \t{:02d}'.format(received_data))
                    if i == 0:
                        self._log.info('FIXED(0):        \t{:02d}'.format(received_data))
                    elif i == 1:
                        self._log.info('FIXED(1):        \t{:02d}'.format(received_data))
                    elif i == 2:
                        self._log.info('FIXED(2):        \t{:02d}'.format(received_data))
    
                    elif i == 5:
                        self._log.info('LED(5):          \t' + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(received_data))
                    elif i == 6:
                        self._log.info('BUTTON(6):       \t' + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(received_data))
                    elif i == 7:
                        self._log.info('DIGITAL IR(7):   \t' + Fore.YELLOW + Style.BRIGHT  + '{:d}'.format(received_data))
                    elif i == 8:
                        self._log.info('ANALOG IR(8):    \t' + Fore.CYAN + Style.BRIGHT    + '{:d}'.format(received_data))
    
                    elif i == 224:
                        self._log.info('LOOP COUNT(224): \t{:02d}'.format(received_data))
                        self._loop_count = received_data
                    elif i == 230:
                        self._log.info('IR_MIN(230):     \t{:02d}'.format(received_data))
                    elif i == 231:
                        self._log.info('IR_MAX(231):     \t{:02d}'.format(received_data))
                    elif i == 232: # turn on auto-ranging .................................
                        self._log.info('AUTORANGE ON:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                    elif i == 233: # turn off auto-ranging .................................
                        self._log.info('AUTORANGE OFF:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
    
                    elif i == 192: # echo .................................
                        self._log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                    elif i == 201: # echo .................................
                        self._log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                    elif i == 223: # echo .................................
                        self._log.info('ECHO:\tsent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
    
    
                    else:
                        self._log.error('data sent:\t{:02d};\treceived: {:02d}'.format(data_to_send, received_data))
                        if received_data == data_to_send:
                            self._log.info(Fore.YELLOW+'success! sent: {:02d}; received: {:02d}'.format(data_to_send, received_data))
                        else:
                            self._log.error('fail! sent: {:02d}; received: {:02d}'.format(data_to_send, received_data))
    
                if ( self._loop_count % 1000 ) == 0:
                    self._log.info('reset auto-ranging.')
        #           _p1.i2c_write_device(self._handle, AUTORANGE_DISABLE);
                    self.write_i2c_data(AUTORANGE_DISABLE)
        #           wip.wiringPiI2CWrite(fd, AUTORANGE_DISABLE);
                    time.sleep(0.1)
                    self.write_i2c_data(AUTORANGE_ENABLE)
        #           self._pi.i2c_write_device(self._handle, AUTORANGE_ENABLE);
        #           wip.wiringPiI2CWrite(fd, AUTORANGE_ENABLE);
    
                self._log.info(Fore.BLACK + Style.DIM + 'processed: {:04d}\n'.format(count))
        #       time.sleep(0.25)
                time.sleep(2.0)
    
        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in master: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
#       finally:
#           self.close()
#           self._log.info('complete.')


#EOF
