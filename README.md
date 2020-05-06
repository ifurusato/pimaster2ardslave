# Raspberry Pi Master to Arduino Slave (pimaster2ardslave)

This configures an Arduino to act as an I2C slave to a Raspberry Pi master,
configured to work on I2C address 0x08. The Arduino runs a single script,
the Raspberry Pi a Python script.

Any pin can be remotely configured as `INPUT`, `INPUT_PULLUP`, or `OUTPUT`,
and read from the configured pins using single byte key.

On each call, the `loop()` function performs two steps:

1. reads the set of assigned pins. For each assigned pin this updates the array of values, either by reading the corresponding input pin and assigning its value to the array entry for that pin; or for pins assigned as output pins, it takes the array entry and writes that value to the output pin.
2. based on the values read by any of the input pins, adjusts the auto-range minimum and maximum values

The `setup()` function establishes the I2C communication and configures
two callback functions, one for when the Arduino receives data, and one
for a request for data:

* `receiveData()`: when called this captures each byte into a queue. When the queue is filled (2 bytes) it creates an int value from the two bytes (LSB, MSB) which is considered a "command" to be handled by the handleCommand() function (see the function for further documentation).
* `requestData()`: when called this responds simply with the current contents of the output queue (2 bytes).

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

