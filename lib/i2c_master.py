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
        self._handle = self._pi.i2c_open(1, device_id) # open device at address 0x08 on bus 1
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
    def get_input_from_pin(self, pinPlusOffset):
        '''
            Sends a message to the pin (which should already include an offset if
            this is intended to return a non-pin value), returning the result.
        '''
        self.write_i2c_data(pinPlusOffset)
        _received_data  = self.read_i2c_data()
        self._log.debug('received response from pin {:d} of {:>5.2f}.'.format(pinPlusOffset, _received_data))
        return _received_data


    # ..........................................................................
    def set_output_on_pin(self, pin, value):
        '''
            Set the output on the pin as true (HIGH) or false (LOW). The
            corresponding pin must have already been configured as OUTPUT. 
            This returns the response from the Arduino.
        '''
        if value is True:
            self.write_i2c_data(pin + 192)
            self._log.debug('set pin {:d} as HIGH.'.format(pin))
        else:
            self.write_i2c_data(pin + 160)
            self._log.debug('set pin {:d} as LOW.'.format(pin))
        _received_data  = self.read_i2c_data()
        self._log.debug('received response on pin {:d} of {:>5.2f}.'.format(pin, _received_data))
        return _received_data


    # ..........................................................................
    def configure_pin_as_digital_input(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT), which sets the pin as a digital input pin. 

            This configuration treats the output as a digital value, returning a 0 (inactive) or 1 (active).

            32-63:      set the pin (n-32) as an INPUT pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for INPUT...'.format(pin))
        self.write_i2c_data(pin + 32)
        _received_data  = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for INPUT; returned: {:>5.2f}'.format(pin, _received_data))
        else:
            self._log.error('failed to configure pin {:d} for INPUT; returned: {:>5.2f}'.format(pin, _received_data))


    # ..........................................................................
    def configure_pin_as_digital_input_pullup(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT_PULLUP), which sets the pin as a 
            digital input pin with an internal pullup resister.

            This configuration treats the output as a digital value, returning a 0 (active) or 1 (inactive).

            64-95:      set the pin (n-64) as an INPUT_PULLUP pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for INPUT_PULLUP'.format(pin))
        self.write_i2c_data(pin + 64)
        _received_data  = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for INPUT_PULLUP; returned: {:>5.2f}'.format(pin, _received_data))
        else:
            self._log.error('failed to configure pin {:d} for INPUT_PULLUP; returned: {:>5.2f}'.format(pin, _received_data))


    # ..........................................................................
    def configure_pin_as_analog_input(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT);
            which sets the pin as an input pin. 

            This configuration treats the output as an analog value, returning a value from 0 - 255.

            96-127:     set the pin (n-96) as an INPUT_ANALOG pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for OUTPUT...'.format(pin))
        self.write_i2c_data(pin + 96)
        _received_data = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for OUTPUT; returned: {:>5.2f}'.format(pin, _received_data))
        else:
            self._log.error('failed to configure pin {:d} for OUTPUT; returned: {:>5.2f}'.format(pin, _received_data))


    # ..........................................................................
    def configure_pin_as_output(self, pin):
        '''
            Equivalent to calling pinMode(pin, OUTPUT), which sets the pin as an output pin.

            The output from calling this pin returns the current output setting. To set the
            value to 0 or 1 call setOutputForPin().

            128-159:    set the pin (n-128) as an OUTPUT pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for OUTPUT...'.format(pin))
        self.write_i2c_data(pin + 128)
        _received_data = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for OUTPUT; returned: {:>5.2f}'.format(pin, _received_data))
        else:
            self._log.error('failed to configure pin {:d} for OUTPUT; returned: {:>5.2f}'.format(pin, _received_data))


    # ..........................................................................
    def close(self):
        '''
            Doesn't close the I²C device (which isn't necessary) but rather discards the
            existing handle so that the instance of the class can no longer be used.
        '''
        self._log.debug('closing I²C device at handle {}...'.format(self._handle))
        if not self._closed:
            try:
                self._closed = True
#               self._pi.i2c_close(self._handle) # close device
                self._handle = None
                self._log.debug('I²C device at handle {} closed.'.format(self._handle))
            except Exception as e:
                self._log.error('error closing master: {}'.format(e))
        else:
            self._log.debug('I²C device at handle {} closed.'.format(self._handle))


    # tests ====================================================================

    # ..........................................................................
    def test_echo(self):
        '''
            Performs a simple test, sending a series of bytes to the slave, then
            reading the return values. The Arduino slave's 'isEchoTest' boolean
            must be set to true. This does not require any hardware configuration
            save that the Raspberry Pi must be connected to the Arduino via I²C
            and that there is no contention on address 0x08.
        '''
        try:
            self._log.info('starting echo test...')
            _data = [ 0, 1, 2, 4, 32, 63, 64, 127, 128, 228, 254, 255 ]
            for i in range(0,len(_data)):
                _data_to_send = _data[i]
                self.write_i2c_data(_data_to_send)
                _received_data = self.read_i2c_data()
                if _data_to_send != _received_data:
                    self._log.error('echo failed:   {} != {}'.format(_data_to_send, _received_data))
                else:
                    self._log.info('echo succeeded: {} == {}'.format(_data_to_send, _received_data))

            self._pi.i2c_close(self._handle) # close device
            self._log.info('echo test complete.')
        except Exception as e:
            self._log.error('error in echo test: {}'.format(e))
            traceback.print_exc(file=sys.stdout)


    # ..........................................................................
    def test_blink_led(self, blink_count):
        '''
            Blinks an LED connected to pin 5 of the Arduino. If you're using a 5V
            Arduino a 330 ohm resistor should be connected in series with the LED,
            as LEDs cannot directly handle a 5v source.
        '''
        try:

            self._log.info(Fore.CYAN + Style.BRIGHT + 'blink the LED {:d} times...'.format(blink_count))
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'type Ctrl-C to cancel the test.')

            # configure an LED as OUTPUT on pin 5
            _pin = 5;
            self.configure_pin_as_output(_pin)

            # 225: set request count to zero
            request_count = self.get_input_from_pin(225)
            self._log.info('set loop count to zero: {:>5.2f}'.format(request_count))

#           while True: # if you want to blink foreever
            for i in range(blink_count):
                _received_data = self.set_output_on_pin(_pin, True)
                self._log.debug('blink ON  on pin {:d}; returned: {:>5.2f}'.format(_pin, _received_data))
                time.sleep(0.5)

                _received_data = self.set_output_on_pin(_pin, False)
                self._log.debug('blink OFF on pin {:d}; returned: {:>5.2f}'.format(_pin, _received_data))
                time.sleep(0.5)

            # 226: return request count (we expect 2x the blink count plus one for the request count itself
            _expected = blink_count * 2 + 1
            request_count = self.get_input_from_pin(226)
            self._log.info('request count expected: ' + Fore.CYAN + Style.BRIGHT + 'expected: {:d}; actual: {:d}'.format(_expected, request_count))
            assert _expected == request_count

        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in master: {}'.format(e))
            traceback.print_exc(file=sys.stdout)


    # ..........................................................................
    def test_configuration(self, loop_count):
        '''
            Configures each of the pin types. You can see the result of the configuration
            on the Arduino IDE's Serial Monitor (even without any hardware). If you set up
            the hardware to match this configuration you can also see the input and output 
            results on the Serial Monitor. 

            The hardware configuration is as follows:

              *  An LED (and a 330 ohm resistor) connected between pin 5 and ground, configured as OUTPUT.
              *  A pushbutton connected between pin 6 and ground, configured as INPUT_PULLUP.
              *  A digital infrared sensor connected to pin 7, configured as INPUT.
              *  An analog infrared sensor connected to pin 8, configured as INPUT.
              *  A digital infrared sensor connected to pin 9, configured as INPUT_PULLUP.
        '''
        try:

            self._log.info(Fore.CYAN + Style.BRIGHT + 'test configuring the arduino and then reading the results...')
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'type Ctrl-C to cancel the test.')

            # configure some pins, adjust these to suit your own situation...

            # configure an LED as OUTPUT on pin 5
            self.configure_pin_as_output(5)

            # configure a push button as INPUT_PULLUP on pin 6
            self.configure_pin_as_digital_input_pullup(6)

            # configure an IR digital sensor as INPUT on pin 7
            self.configure_pin_as_digital_input(7)

            # configure an IR analog sensor as INPUT on pin 8
            self.configure_pin_as_analog_input(8)

            # configure an IR digital sensor as INPUT_PULLUP on pin 9
            self.configure_pin_as_digital_input_pullup(9)

            self._log.info('configured. starting loop to repeat {:d} times...\n'.format(loop_count))

            # let's repeatedly check some values...
            data_array = [ 0, 5, 6, 7, 8, 9, 224, 226, 228, 230, 231 ]
#           while True:
            for x in range(loop_count):
                _count = next(self._counter)
                for i in range(0,len(data_array)):
                    # write data to Arduino ..................................
                    _data_to_send = data_array[i];
                    n = _data_to_send
                    self.write_i2c_data(_data_to_send)
                    # read data from Arduino .................................
                    _received_data = self.read_i2c_data()
                    # display results ........................................
                    self._log.debug(Fore.BLACK + '[{:d}] sent:\t{:02d};\treceived: {:02d}'.format(_count, _data_to_send, _received_data))
                    if n == 0:
                        self._log.info('[{:04d}] UNCONFIGURED (0):       \t{:02d}'.format(_count, _received_data) + Style.DIM + '\t(expected 250/PIN_UNASSIGNED)')
                    elif n == 5:
                        self._log.info('[{:04d}] LED (5):                \t'.format(_count) + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(expected 251/PIN_ASSIGNED_AS_OUTPUT)')
                    elif n == 6:
                        self._log.info('[{:04d}] BUTTON (6):             \t'.format(_count) + Fore.GREEN + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(displays button value 0|1)')
                    elif n == 7:
                        self._log.info('[{:04d}] DIGITAL IR (7):         \t'.format(_count) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) + Style.DIM + '\t(displays digital IR sensor value 0|1)') 
                    elif n == 8:
                        self._log.info('[{:04d}] ANALOG IR (8):          \t'.format(_count) + Fore.YELLOW + Style.BRIGHT    + '{:d}'.format(_received_data) + Style.DIM + '\t(displays analog IR sensor value 0-255)') 
                    elif n == 9:
                        self._log.info('[{:04d}] DIGITAL IR (9):         \t'.format(_count) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) + Style.DIM + '\t(displays digital IR sensor value 0|1)') 
                    elif n == 224: 
                        self._log.info('[{:04d}] ECHO (224):             \t'.format(_count) + Style.BRIGHT + 'sent:\t{:02d};\treceived: {:02d}'.format(_data_to_send, _received_data))
                    elif n == 226:
                        self._log.info('[{:04d}] REQUEST COUNT (226):    \t'.format(_count) + Style.BRIGHT + '{:02d}'.format(_received_data) + Style.DIM + '\t(total requests since starting)')
                    elif n == 228:
                        self._log.info('[{:04d}] LOOP COUNT (228):       \t'.format(_count) + Style.BRIGHT + '{:02d}'.format(_received_data) + Style.DIM + '\t(total loops since starting)')
                        self._loop_count = _received_data
                    elif n == 230:
                        self._log.info('[{:04d}] ANALOG MIN RANGE (230): \t'.format(_count) + Fore.CYAN + Style.BRIGHT    + '{:d}'.format(_received_data) + Style.DIM + '\t(minimum limit of auto-range)')
                    elif n == 231:
                        self._log.info('[{:04d}] ANALOG MAX RANGE (230): \t'.format(_count) + Fore.CYAN + Style.BRIGHT    + '{:d}'.format(_received_data) + Style.DIM + '\t(maximum limit of auto-range)')
                    else:
                        self._log.warning('[{:04d}] ELSE:            \tsent:\t{:02d};\treceived: {:02d}'.format(_count, _data_to_send, _received_data))

                print('')
                time.sleep(1.0)

            # we never get here if using 'while True:'
            self._log.info('test complete.')
    
        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in master: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
#       finally:
#           self.close()
#           self._log.info('complete.')


#EOF
