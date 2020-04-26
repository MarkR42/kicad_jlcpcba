#!/usr/bin/env python3

"""
    Read schematics and parse out the LCSC part numbers,
    unique ID and Reference

"""
import os
import collections
import sys

SchematicPart = collections.namedtuple('SchematicPart',
    ['uid', 'reference', 'value', 'footprint', 'lcsc']
    )

def read_schematic(fn):
    last_ref = ''
    last_uid = ''
    last_lcsc = False
    last_value = ''
    last_footprint = ''
    parts = []
    for line in open(fn, 'rt'):
        line = line.strip()
        # Check for lines like this:
        # L malenki-nano-rescue:LED-Device D1
        if line.startswith('L'):
            last_ref = line.split()[-1]
        # Check for lines like this:
        # U 1 1 5CDD2ED4
        if line.startswith('U 1'):
            last_uid = line.split()[-1]
        # check for lines like:
        # F 4 "C2293" H 5150 6150 50  0001 C CNN "LCSC"
        if line.startswith('F'):
            bits = line.split()
            if 'LCSC' in bits[-1]:
                # That looks about correct.
                # parse out the part num
                last_lcsc = line.split('"')[1] 
        if line.startswith('F 1 '):
            # Value.
            last_value = line.split('"')[1]
        if line.startswith('F 2 '):
            # Footprint.
            last_footprint = line.split('"')[1]
        if line == '$EndComp':
            if last_lcsc:
                parts.append(SchematicPart(last_uid, last_ref, last_value, last_footprint, last_lcsc))
                last_lcsc = False
                last_footprint = ''
    return parts

if __name__ == '__main__':
    for item in read_schematic(sys.argv[1]):
        print(repr(item))
        
