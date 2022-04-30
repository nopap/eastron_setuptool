#!/usr/bin/env python3

import minimalmodbus
import serial
import argparse

__author__ = "Nick Ma updated by EO"


def parseCmdLineArguments():
    parser = argparse.ArgumentParser(description='Eastron SDM120 setup tool')

    # prepare valid argc/argv arguments
    parser.add_argument('--port', default="/dev/ttyUSB_SDM120_house",
                        help='port where the serial RS485 dongle is connected')
    parser.add_argument('--serialBaudRate', default=2400, type=int, choices={1200, 2400, 4800, 9600})
    parser.add_argument('--meterID', default=1, type=int)

    # setter options
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--setMeterID', type=int, choices=range(1, 248))
    group.add_argument('--setBaudrate', type=int, choices={0, 1, 2, 5},
                        help="0:2400bps(default), 1:4800bps, 2:9600bps, 5:1200bps")
    group.add_argument('--setCT1', type=int, choices={5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60},
                        help="5:5Amps(default), 10:10Amps, ...60:60Amps")
    return parser.parse_args()


class SDM120(minimalmodbus.Instrument):
    """Instrument class for nilan heat pump. 
    communication via RS485 
    """
    # input registers
    REG_VOLTAGE      = 0x0000
    REG_ACTIVE_POWER = 0x000C
    # holding registers
    HOLDING_METER_ID     = 0x0014
    HOLDING_METER_BAUDRATE = 0x001C
    HOLDING_CT1 = 0x0032
    
    def __init__(self, portname, slaveaddress=1, baudrate=2400):
        minimalmodbus.Instrument.__init__(self, portname, slaveaddress)

        # setup the serial connection
        self.serial.baudrate = baudrate
        self.serial.parity = serial.PARITY_NONE
        self.serial.timeout = 1.0  # timeout to 1000ms because I discovered roundtrip times as high as 898.5 ms

        self.mode = minimalmodbus.MODE_RTU

    def is_device_sane(self):
        self.debug = True
        voltage = self.read_float(self.REG_VOLTAGE, functioncode=4)
        self.debug = False

        voltage_sane = 100 < voltage < 250
        print("received voltage of %d, which is %s sane" % (voltage, "NOT" if not voltage_sane else ""))
        return voltage_sane

    @property
    def power(self):
        """2 Read Input Registers
           2.1 MODBUS Protocol code 04 reads the contents of the 3X registers
           [SDM120-Modbus_protocol_V2.1.pdf]"""
        return self.read_float(self.REG_ACTIVE_POWER, functioncode=4)

    def read_holding(self, reg):
        """2.2 Read Holding Registers
            MODBUS Protocol code 03 reads the contents of the 4X registers
           2.3 Write Holding Registers
            MODBUS Protocol code 10 (16 decimal) writes the contents of the 4X registers
            [SDM120-Modbus_protocol_V2.1.pdf]"""
        return self.read_float(reg, functioncode=3)

    def write_holding(self, reg, value):
        self.write_float(reg, value)


if __name__ == '__main__':
    args = parseCmdLineArguments()

    n = SDM120(args.port, slaveaddress=args.meterID, baudrate=args.serialBaudRate)
    print('TESTING sdm Connection on port: %s' % args.port)
    if not n.is_device_sane():
        print("Instance not sane, bye")
        exit(42)
    print('power: %d' % n.power)

    # process args
    if args.setBaudrate is not None:
        current_baudrate = n.read_holding(n.HOLDING_METER_BAUDRATE)
        print("OLD baudrate is: %d, setting it to: %d" % (current_baudrate, args.setBaudrate))
        n.write_holding(n.HOLDING_METER_BAUDRATE, args.setBaudrate)
        # TODO set n.serial.baudrate=args.setBaudrate *after* the successful write,
        #  as the meter changes its value immediately
    if args.setMeterID is not None:
        current_meter_id = n.read_holding(n.HOLDING_METER_ID)
        print("OLD device id: %d, setting it to: %d" % (current_meter_id, args.setMeterID))
        n.write_holding(n.HOLDING_METER_ID, args.setMeterID)
        # TODO set n.address=args.setMeterID *after* the successful write
    if args.setCT1 is not None:
        current_amps = n.read_holding(n.HOLDING_CT1)
        if args.setCT1 == 60:
            new_amps = 0x42700000
        if new_amps:
            print("OLD device CT1 Amps: %d, setting it to: %d" % (current_amps, new_amps))
            n.write_holding(n.HOLDING_CT1, new_amps)
        else:
            print("OLD device CT1 Amps: %d" % (current_amps))
            print("No proper new_amps value")
