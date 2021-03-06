#include <Wire.h>
#include <stdio.h>        // required for function sprintf
#include <ArduinoQueue.h> // see below for installation

/*
    Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
    the Raspberry Pi Master to Arduino Slave (pimaster2ardslave) project and is
    released under the MIT License. Please see the LICENSE file included as part
    of this package.

      author:   Murray Altheim
      created:  2020-04-30
      modified: 2020-05-08

    This configures an Arduino as a slave to a Raspberry Pi master, configured
    to communicate over I²C on address 0x08. The Arduino runs this single script,
    the Raspberry Pi a Python script.

    The pins of the Arduino can be remotely configured from the Pi as INPUT,
    INPUT_PULLUP, or OUTPUT (on an Arduino pins are set INPUT by default).

    Once configured, the value of input pins can be read from using a two
    byte key as a command; pins configured as output pins can likewise be
    set via command. In the returned data the high order byte is always 0x00,
    so this script reacts to keys from 0 to 255. The specifics of these keys
    is documented below.

    On each call, the loop() function performs two steps:

      1. reads the set of assigned pins. For each assigned pin this updates
         the array of values, either by reading the corresponding input pin
         and assigning its value to the array entry for that pin; or for
         pins assigned as output pins, it takes the array entry for that pin
         and writes the value to the corresponding output pin.
      2. based on the values read by any of the input pins, adjusts the
         auto-range minimum and maximum values

    The setup() function establishes the I²C communication and configures
    two callback functions, one for when the Arduino receives data, and one
    for when it receives a request for data:

      receiveData(): when called this pushes each byte into a queue.
          When the queue is filled (2 bytes) it creates an int value
          from the two bytes (LSB, MSB) considered together as a "command"
          to be handled by the handleCommand() function (see the function
          for further documentation).
      requestData(): when called this responds with the current contents
          of the output queue (2 bytes).

    The `requestData()` call empties the queue, so for every receiveData()
    call there should be a requestData() call to receive the corresponding
    response. Because of this the Arduino should not be receiving calls
    from more than one master; there is no synchronisation.

    This script requires installation of ArduinoQueue by Einar Arnason,
    see: https://github.com/EinarArnason/ArduinoQueue
*/

#define SLAVE_I2C_ADDRESS         0x08
#define LOOP_DELAY_MS             1000

// errors ........................................
#define UNDEFINED_ERROR            255   // returned on error
#define UNRECOGNISED_COMMAND       254   // returned on communications error
#define TOO_MUCH_DATA              253   // returned on communications error
#define PIN_ASSIGNED_AS_INPUT      252   // configuration error
#define PIN_ASSIGNED_AS_OUTPUT     251   // configuration error
#define PIN_UNASSIGNED             250   // configuration error
#define EMPTY_QUEUE                249   // returned on error
#define INIT_VALUE                   0   // initial pin value; may be error

// pin types .....................................
const int PIN_INPUT_DIGITAL        = 2;  // default
const int PIN_OUTPUT               = 3;
const int PIN_INPUT_DIGITAL_PULLUP = 4;  // inverted: low(0) is on
const int PIN_INPUT_ANALOG         = 5;
const int PIN_UNUSED               = 6;

// commands ......................................
const int CMD_ECHO_INPUT           = 224;
const int CMD_CLEAR_REQUEST_COUNT  = 225;
const int CMD_RETURN_REQUEST_COUNT = 226;
const int CMD_CLEAR_LOOP_COUNT     = 227;
const int CMD_RETURN_LOOP_COUNT    = 228;
const int CMD_CLEAR_QUEUES         = 229;
const int CMD_RETURN_ANALOG_MIN_RANGE = 230;
const int CMD_RETURN_ANALOG_MAX_RANGE = 231;
const int CMD_DISABLE_AUTORANGE    = 232;
const int CMD_ENABLE_AUTORANGE     = 233;

// constants .....................................
int pinsAssigned = 10;                   // we support up to 32 IO pins (D0-D31, A0-A31)

// flags/configuration ...........................
boolean isVerbose = true;                // write verbose messages to serial console if true
boolean isEchoTest = false;              // test: when true just echo input to output (default false)
boolean isAutoRange  = false;            // if true automatically adjust range (default false)
boolean isConstrainAnalogValue = true;   // use constraints to limit the analog value?
float analogMinDefault = 70.0;           // default minimum of the analog range
float analogMin = analogMinDefault;      // the minimum expected value from the analog sensor (28 observed on IR)
float analogMaxDefault = 600.0;          // default minimum of the analog range
float analogMax = analogMaxDefault;      // the maximum expected value from the analog sensor (685 observed on IR)

// variables .....................................
ArduinoQueue<byte> inputQueue(2);
ArduinoQueue<byte> outputQueue(2);
int pinAssignments[32] = {};             // how the pin is assigned
int pinValues[32] = {};                  // the value of the pin (if it's an input pin)
long loopCount      = 0;                 // number of times loop() has been called
long requestCount   = 0;                 // number of times request has been called (actually, when queue is emptied)
char buf[100];                           // used by sprintf

// functions ...................................................................

/**
    Required setup function.
*/
void setup() {
    resetPinAssignments();
    resetPinValues();

    Wire.begin(SLAVE_I2C_ADDRESS);
    Wire.onReceive(receiveData);
    Wire.onRequest(requestData);

    ready_blink();
    sprintf(buf, "ready.");
    Serial.println(buf);
}

/**
    Required loop function.
*/
void loop() {
    readPinAssignments();
    if ( isVerbose ) {
        // displayPinAssignments();
    }
    delay(LOOP_DELAY_MS);
    loopCount += 1;
}

/**
    Sends the contents of the queue byte-by-byte (LSB, MSB) over
    the Wire until the output queue is empty. If the output queue
    is empty, sends EMPTY_QUEUE as an error message.
*/
void requestData() {
    if ( outputQueue.isEmpty() ) {
        queueForOutput(EMPTY_QUEUE);
    }
    while ( !outputQueue.isEmpty() ) {
        Wire.write(outputQueue.dequeue());
    }
}

/**
    Receives notification that data is available over the Wire,
    pushing each byte onto the data queue. This function is
    called repeatedly but doesn't cause the incoming data to be
    interpreted until the input cache is full (2 bytes).
*/
void receiveData(int byteCount) {
    for (int i = 0; i < byteCount; i++) {
        byte b = Wire.read();
        inputQueue.enqueue(b);
        outputQueue.enqueue(b);
    }
    if ( inputQueue.item_count() == 2 ) { // cache is full so prepare output data
        requestCount += 1;
        byte loByte = inputQueue.dequeue();
        byte hiByte = inputQueue.dequeue();
        int inputData = loByte | ( hiByte << 8 );
        int outputData;
        if ( isEchoTest ) {
            outputData = inputData;
        } else {
            outputData = handleCommand(inputData);
        }
        clearOutputQueue();
        queueForOutput(outputData);
    }
}

/**
    Set the stored values for each assigned pin. For input pins
    this reads the pins and stores their values, for output pins
    this takes the set value and writes it to the pin.
*/
void readPinAssignments() {
    if ( isVerbose ) {
        sprintf(buf, "\n[%05ld] read assignments for %2d pins...", loopCount, pinsAssigned );
        Serial.println(buf);
    }
    for ( int pin = 0; pin < pinsAssigned; pin++ ) {
        int pinType = pinAssignments[pin];
        if  (pinType ==  PIN_INPUT_DIGITAL ) {
            int digitalValue = digitalRead(pin);
            pinValues[pin] = digitalValue;
            sprintf(buf, "pin %2d : INPUT;       \tvalue: %4d", pin, digitalValue);
        } else if (pinType ==  PIN_INPUT_ANALOG ) {
            int analogValue = analogRead(pin);
            adjustAutoRange(analogValue);
            pinValues[pin] = analogValue;
            sprintf(buf, "pin %2d : INPUT_ANALOG;\tvalue: %4d", pin, analogValue);
        } else if (pinType ==  PIN_INPUT_DIGITAL_PULLUP ) {
            int digitalValue = !digitalRead(pin);
            pinValues[pin] = digitalValue;
            sprintf(buf, "pin %2d : INPUT_PULLUP;\tvalue: %4d", pin, digitalValue);
        } else if (pinType ==  PIN_OUTPUT ) {
            int outputValue =  pinValues[pin];
            if ( outputValue == 0 ) {
                digitalWrite(pin, LOW);
            } else {
                digitalWrite(pin, HIGH);
            }
            sprintf(buf, "pin %2d : OUTPUT;      \tvalue: %4d", pin, outputValue);
        } else if (pinType ==  PIN_UNUSED ) {
            sprintf(buf, "pin %2d : UNUSED", pin);
        } else {
            sprintf(buf, "pin %2d : DEFAULT", pin);
        }
        if ( isVerbose ) {
            Serial.println(buf);
        }
    }
}

/**
    Display the configured types for each pin.
*/
void displayPinAssignments() {
    sprintf(buf, "\n[%05ld] display pin assignments...", loopCount);
    Serial.println(buf);
    for ( int pin = 0; pin < pinsAssigned; pin++ ) {
        int pinType = pinAssignments[pin];
        switch (pinType) {
            case PIN_INPUT_DIGITAL:
                sprintf(buf, "pin %2d : INPUT", pin);
                break;
            case PIN_INPUT_DIGITAL_PULLUP:
                sprintf(buf, "pin %2d : INPUT_PULLUP", pin);
                break;
            case PIN_INPUT_ANALOG:
                sprintf(buf, "pin %2d : INPUT_ANALOG", pin);
                break;
            case PIN_OUTPUT:
                sprintf(buf, "pin %2d : OUTPUT", pin);
                break;
            case PIN_UNUSED:
                sprintf(buf, "pin %2d : UNUSED", pin);
        }
        Serial.println(buf);
    }
}

/**
    Interprets the data as a command. If the data value is smaller than or
    equal to the pin count the stored value for that pin is returned.

    If the data value is larger than the pin count the offset indicates
    its interpretation:

      0-31:       return the output data for that pin assignment, -1 if the pin is not assigned
      32-63:      set the pin (n-32) as an INPUT pin, return pin number
      64-95:      set the pin (n-64) as an INPUT_PULLUP pin, return pin number
      96-127:     set the pin (n-96) as an INPUT_ANALOG pin, return pin number
      128-159:    set the pin (n-128) as an OUTPUT pin, return pin number
      160-191:    write output for pin (n-160) to LOW, return 0
      192-223:    write output for pin (n-192) to HIGH, return 1
      224:        echo input
      225:        set request count to zero
      226:        return request count
      227:        set loop count to zero
      228:        return loop count
      229:        clear queues, return 0
      230:        return IR analog minimum range
      231:        return IR analog maximum range
      232:        disable auto-ranging, return 0
      233:        enable auto-ranging, return 1
      240-255:    error values
*/
int handleCommand( int data ) {
    if ( data >= 0 && data < 32 ) { // 0-31:  return the output data for that pin assignment, -1 if the pin is not assigned
        return getValueOf(data);
    } else if ( inRange(data, 32, 64) ) { //              32-63:  set the pin (n-32) as an PIN_INPUT_DIGITAL pin, return pin number
        int pin = data - 32;
        setPinAssignment(pin, PIN_INPUT_DIGITAL);
        return pin;
    } else if ( inRange(data, 64, 96) ) { //              64-95:  set the pin (n-64) as an PIN_INPUT_DIGITAL_PULLUP pin, return pin number
        int pin = data - 64;
        setPinAssignment(pin, PIN_INPUT_DIGITAL_PULLUP);
        return pin;
    } else if ( inRange(data, 96, 128) ) { //             64-95:  set the pin (n-64) as an PIN_INPUT_ANALOG pin, return pin number
        int pin = data - 96;
        setPinAssignment(pin, PIN_INPUT_ANALOG);
        return pin;
    } else if ( inRange(data, 128, 160)  ) { //         128-159:  set the pin (n-96) as an OUTPUT pin, return pin number
        int pin = data - 128;
        setPinAssignment(pin, PIN_OUTPUT);
        return pin;
    } else if ( inRange(data, 160, 192) ) { //          160-191:  write output for pin (n-160) to LOW, return 0
        int pin = data - 160;
        digitalWrite(pin, LOW);
        return 0;
    } else if ( inRange(data, 192, 224) ) { //          192-223:  write output for pin (n-192) to HIGH, return 1
        int pin = data - 192;
        digitalWrite(pin, HIGH);
        return 1;
    } else if ( data == CMD_ECHO_INPUT ) { //           224:      echo input
        return data;
    } else if ( data == CMD_CLEAR_REQUEST_COUNT ) { //  225:      clear request count, return 0
        requestCount = 0;
        return requestCount;
    } else if ( data == CMD_RETURN_REQUEST_COUNT ) { // 226:      return request count
        return requestCount;
    } else if ( data == CMD_CLEAR_LOOP_COUNT ) { //     227:      clear loop count, return 0
        loopCount = 0;
        return loopCount;
    } else if ( data == CMD_RETURN_LOOP_COUNT ) { //    228:      return loop count
        return loopCount;
    } else if ( data == CMD_CLEAR_QUEUES ) { //         229:      clear queues, return 0
        clearInputQueue();
        clearOutputQueue();
        return 0;
    } else if ( data == CMD_RETURN_ANALOG_MIN_RANGE ) { //  230:  return analog minimum range
        return analogMin;
    } else if ( data == CMD_RETURN_ANALOG_MAX_RANGE ) { //  231:  return analog maximum range
        return analogMax;
    } else if ( data == CMD_DISABLE_AUTORANGE ) { //    232:      disable auto-ranging, return 0
        isAutoRange  = false;
        resetRange();
        return 0;
    } else if ( data == CMD_ENABLE_AUTORANGE ) { //     233:      enable auto-ranging, return 1
        isAutoRange  = true;
        resetRange();
        return 1;
    } else if ( data >= 240 ) { //                  240-255:      error values
        return data;
    } else { //                                        else:      unrecognised command error
        return UNRECOGNISED_COMMAND;
    }
}

/*
    If the pin is any kind of input pin, return its value, otherwise PIN_ASSIGNED_AS_OUTPUT
    (an error value).

    If the pin is assigned as an analog pin its value may exceed the one byte limit. If the
    isConstrainAnalogValue flag is true its value will be either fixed-range or auto-range
    constrained to fit within 0 and 255.
*/
int getValueOf( int pin ) {
    if ( pinAssignments[pin] == PIN_INPUT_DIGITAL
            || pinAssignments[pin] == PIN_INPUT_DIGITAL_PULLUP ) {
        return pinValues[pin]; // return the output data for the pin
    } else if ( pinAssignments[pin] == PIN_INPUT_ANALOG ) {
        if ( isConstrainAnalogValue ) {
            // constrain values (which go up to about 685 on a Sharp IR sensor) within a 0-255 range
            return constrainAnalogValue(pinValues[pin]);
        } else {
            return pinValues[pin];
        }
    } else if ( pinAssignments[pin] == PIN_UNUSED ) {
        return PIN_UNASSIGNED;
    } else {
        return PIN_ASSIGNED_AS_OUTPUT;
    }
}

/**
    Set the assignment for the specified pin to PIN_UNUSED, PIN_INPUT, PIN_INPUT_PULLUP, or PIN_OUTPUT.
*/
void setPinAssignment(int pin, int assignment) {
    // keep record of assignment
    pinAssignments[pin] = assignment;
    // now assign Arduino pin accordingly
    switch ( assignment ) {
        case PIN_INPUT_ANALOG:
            pinMode(pin, INPUT);
            sprintf(buf, "set pin %d assignment as INPUT_ANALOG.", pin);
            break;
        case PIN_INPUT_DIGITAL:
            pinMode(pin, INPUT);
            sprintf(buf, "set pin %d assignment as INPUT_DIGITAL.", pin);
            break;
        case PIN_INPUT_DIGITAL_PULLUP:
            pinMode(pin, INPUT_PULLUP);
            sprintf(buf, "set pin %d assignment as INPUT_DIGITAL_PULLUP.", pin);
            break;
        case PIN_OUTPUT:
            pinMode(pin, OUTPUT);
            sprintf(buf, "set pin %d assignment as OUTPUT.", pin);
            break;
        case PIN_UNUSED:
            pinMode(pin, INPUT); // there is no disable pinMode()
            sprintf(buf, "set pin %d assignment as UNUSED.", pin);
            break;
    }
    if ( isVerbose ) {
        Serial.println(buf);
    }
}

/**
    Sets the pin assignments for all to -1 (unused).
*/
void resetPinAssignments() {
    for ( int i = 0; i < pinsAssigned; i++ ) {
        pinAssignments[i] = PIN_UNUSED;
    }
}

/**
    Sets the pin state values for all to -2 (error value).
*/
void resetPinValues() {
    for ( int i = 0; i < pinsAssigned; i++ ) {
        pinValues[i] = INIT_VALUE;
    }
}

/**
    Enqueues the int value to the output queue.
*/
void queueForOutput( int data ) {
    outputQueue.enqueue(lowByte(data));
    outputQueue.enqueue(highByte(data));
}


/**
    Clears the contents of the input queue.
*/
void clearInputQueue() {
    while ( !inputQueue.isEmpty() ) {
        inputQueue.dequeue();
    }
}

/**
    Clears the contents of the output queue.
*/
void clearOutputQueue() {
    while ( !outputQueue.isEmpty() ) {
        outputQueue.dequeue();
    }
}

/**
    Constrains the analog value between 0 and 255.
    This uses either a manually set range or auto-ranging if enabled.
*/
int constrainAnalogValue( int value ) {
    return constrain( (( value - analogMin ) / ( analogMax )) * 255.0 , 0, 255 );
}

/**
    The minimum and maximum values are either fixed (when 'isAutoRange' is
    false) or dynamically adjusted based on observed values. Fixing the
    values will necessarily also limit the range of the returned values,
    reflecting limitations in, for example, the measured physical distance.

    But auto-ranging can also be problematic, in that glitches in the min/max
    range can set their values to extremes that causes a flattening of the
    scale. For example, if the minimum value "accidentally" gets set too low
    the maximum value (255) for the closest range will never get returned,
    so the robot will think it's further away from an obstacle than it
    actually is ("objects in mirror are closer than they appear").
*/
void adjustAutoRange( int rawAnalogValue ) {
    if ( isAutoRange ) { // then auto-adjust range
        analogMin = min(analogMin, rawAnalogValue);
        analogMax = max(analogMax, rawAnalogValue);
    }
}

/**
    Reset the auto-range values to their defaults.
*/
void resetRange() {
    analogMin = analogMinDefault;
    analogMax = analogMaxDefault;
}

/**
    Returns true if the value is within the range minimum < value < maximum.
    Note this is inclusive of the minimum, exclusive of the maximum.
*/
boolean inRange(int value, int minimum, int maximum) {
    return ((minimum <= value) && (value < maximum));
}

// status displays .............................................................

/**
    A distinctive blink pattern indicating the Arduino is ready.
*/
void ready_blink() {
    for ( int i = 67; i > 0; i -= 5 )  {
        digitalWrite(LED_BUILTIN_TX, HIGH);
        delay(i);
        digitalWrite(LED_BUILTIN_TX, LOW);
        delay(i);
        digitalWrite(LED_BUILTIN_RX, HIGH);
        delay(i);
        digitalWrite(LED_BUILTIN_RX, LOW);
        delay(i);
    }
    digitalWrite(LED_BUILTIN_TX, HIGH);
    digitalWrite(LED_BUILTIN_RX, HIGH);
    delay(667);
    digitalWrite(LED_BUILTIN_TX, LOW);
    digitalWrite(LED_BUILTIN_RX, LOW);
}

//       1         2         3         4         5         6         7         8
//345678901234567890123456789012345678901234567890123456789012345678901234567890
