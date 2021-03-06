# Raspberry Pi Master to Arduino Slave (pimaster2ardslave)

This configures an Arduino as a slave to a Raspberry Pi master, configured to communicate over I²C on address `0x1A`. The Arduino runs the provided sketch, the Raspberry Pi a Python script.

![Raspberry Pi to Arduino aboard a robot](https://service.robots.org.nz/wiki/attach/RaspberryPiToArduinoOverI2C/pimaster2ardslave-0542-550x504.jpg)

_The above image shows an Arduino Micro connected to a Raspberry Pi using Pimoroni's Breakout Garden._

The pins of the Arduino can be remotely configured from the Pi as `INPUT`, `INPUT_PULLUP`, or `OUTPUT` (on an Arduino pins are set `INPUT` by default).

Once configured, the value of input pins can be read from using a two byte key as a command; pins configured as output pins can likewise be set via command. In the returned data the high order byte is always `0x00`, so the sketch reacts to keys from 0 to 255. The specifics of these keys is documented below.

On each call, the `loop()` function performs two steps:

1. reads the set of assigned pins. For each assigned pin this updates the array of values, either by reading the corresponding input pin and assigning its value to the array entry for that pin; or for pins assigned as output pins, it takes the array entry for that pin and writes the value to the corresponding output pin
2. based on the values read by any of the input pins, adjusts the auto-range minimum and maximum values

The `setup()` function establishes the I²C communication and configures two callback functions, one for when the Arduino receives data, and one for when it receives a request for data:

* `receiveData()`: when called this pushes each byte into a queue. When the queue is filled (2 bytes) it creates an int value from the two bytes (LSB, MSB) considered together as a "command" to be handled by the handleCommand() function (see the function for further documentation).
* `requestData()`: when called this responds with the current contents of the output queue (2 bytes).

The `requestData()` call empties the queue, so for every `receiveData()` call there should be a `requestData()` call to receive the corresponding response.  Because of this the Arduino should not be receiving calls from more than one master; there is no synchronisation.


## Status

At the time of this writing the project is less than a week old, and is largely functional, with the basic communication between the Raspberry Pi and Arduino working. The repository currently includes three tests that function and interact with hardware in expected ways.

* `test_echo.py`:   this tests that the Raspberry Pi and Arduino can talk to each other, and doesn't require any sensors or additional hardware other than the I²C between the two boards. Communication is over address 0x08, so be sure that is not being used by another device. For the test to function be sure to set the 'isEchoTest' flag on the Arduino's i2cSlave.ino sketch to true, otherwise it won't echo the requests but rather respond to them.
* `test_blink.py`:  this test blinks an LED connected to pin 5 of the Arduino. This requires a Raspberry Pi connected to an Arduino over I²C on address 0x08. Because an LED cannot directly handle a 5 volt supply you should connect the LED to ground through a resistor of about 330 ohms. The exact value will depend on the dropping voltage of the LED (which varies) and how bright you want it to appear.  
* `test_config.py`: this tests a hardware configuration of one button, one LED, two digital and one analog infrared sensors, first configuring the Arduino and then performing a communications loop.


The project is being exposed publicly so that those interested can follow its progress. When things stabilise we'll update this status section.


## Quick Start

Try out the various tests, which will interact with hardware. More to come on this subject...


## Installation

The Raspberry Pi will require support for Python 3 and pip3. Additionally, you will need to install the [pigpio library](http://abyz.me.uk/rpi/pigpio/), e.g., 

    % sudo pip3 install pigpio 

Once pigpio is installed you can run the test_i2c_master.py and try experimenting with various alternative settings.

On the Arduino, install the i2c_slave.ino file via the Arduino IDE (or whatever method you generally use to upload sketches to your Arduino). Once the sketch is loaded the Arduino is ready to receive configuration and calls from the Raspberry Pi. What you want to do with the Pi script is rather up to you. As a first exercise you might set the `isEchoTest` boolean value in the i2c_slave.ino file to true and execute the echo_test() method in I2cMaster.

The Arduino sketch requires installation of ArduinoQueue by Einar Arnason, see:

* [ArduinoQueue](https://github.com/EinarArnason/ArduinoQueue)



## Support & Liability

This project comes with no promise of support or liability. Use at your own risk.

There are a number of gotchas when using I²C to connect a Raspberry Pi (which uses 3.3 volts for its logic) and various models of the Arduino board, some that use 5 volt logic, some that use 3.3 volts. You can burn out or damage your hardware if you don't do it right. It is beyond the scope of this project to help you connect your hardware.

To remove some of the hazard I highly recommend one of the 3.3 volt Arduinos, (e.g., the Arduino Nano IoT or Nano BLE **but not** the Nano, Micro or Uno).  


## Further Information

This project is part of the _New Zealand Personal Robotics (NZPRG)_ "Robot Operating System", not to be confused with other "ROS" projects. For more information check out the [NZPRG Blog](https://robots.org.nz/) and [NZPRG Wiki](https://service.robots.org.nz/wiki/).

Please note that the documentation in the code will likely be more current than this README file, so please consult it for the "canonical" information. Also note that this project will eventually be folded into the NZPRG Robot Operating System project, once it has gotten to a stage where it can be posted publicly.


## Copyright & License

This software is Copyright 2020 by Murray Altheim, All Rights Reserved.

Distributed under the MIT License, see LICENSE file included with project.

