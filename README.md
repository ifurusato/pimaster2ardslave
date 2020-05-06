# Raspberry Pi Master to Arduino Slave (pimaster2ardslave)


This configures an Arduino as a slave to a Raspberry Pi master, configured
to communicate over I2C on address `0x1A`. The Arduino runs this single script,
the Raspberry Pi a Python script.

The pins of the Arduino can be remotely configured from the Pi as `INPUT`,
`INPUT_PULLUP`, or `OUTPUT` (on an Arduino pins are set `INPUT` by default).

Once configured, the value of input pins can be read from using a two byte 
key as a command; pins configured as output pins can likewise be set via 
command. In the returned data the high order byte is always `0x00`, so this 
script reacts to keys from 0 to 255. The specifics of these keys is 
documented below.

On each call, the `loop()` function performs two steps:

1. reads the set of assigned pins. For each assigned pin this updates the array of values, either by reading the corresponding input pin and assigning its value to the array entry for that pin; or for pins assigned as output pins, it takes the array entry for that pin and writes the value to the corresponding output pin
2. based on the values read by any of the input pins, adjusts the auto-range minimum and maximum values

The `setup()` function establishes the I2C communication and configures
two callback functions, one for when the Arduino receives data, and one
for when it receives a request for data:

* `receiveData()`: when called this pushes each byte into a queue. When the queue is filled (2 bytes) it creates an int value from the two bytes (LSB, MSB) considered together as a "command" to be handled by the handleCommand() function (see the function for further documentation).
* `requestData()`: when called this responds with the current contents of the output queue (2 bytes).

The `requestData()` call empties the queue, so for every `receiveData()` call
there should be a `requestData()` call to receive the corresponding response.
Because of this the Arduino should not be receiving calls from more than one 
master; there is no synchronisation.

This script requires installation of ArduinoQueue by Einar Arnason, see:

* [ArduinoQueue](https://github.com/EinarArnason/ArduinoQueue)

Please note that the documentation in the code will likely be more current
than this README file, so please consult it for the "canonical" information.


## Further Information

This project is part of the New Zealand Personal Robotics (NZPRG) Robot Operating 
System, not to be confused with other "ROS" projects. For more information check out the 
[NZPRG Blog](https://robots.org.nz/) and [NZPRG Wiki](https://service.robots.org.nz/wiki/).


## Copyright & License

This software is Copyright 2020 by Murray Altheim, All Rights Reserved.

Distributed under the MIT License, see LICENSE file included with project.

