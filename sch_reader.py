#!/usr/bin/env python3

"""
    Read schematics and parse out the LCSC part numbers,
    unique ID and Reference

"""
import os
import collections
import sys
try:
    import sexpdata
except ImportError:
    from . import sexpdata

SchematicPart = collections.namedtuple('SchematicPart',
    ['uid', 'reference', 'value', 'footprint', 'lcsc']
    )

def _find_sexp_kids(l, symname):
    # Return a list of all children of l which have symname
    return list(
        filter(lambda f: f[0] == sexpdata.Symbol(symname), l)
        )

def _read_schematic_sexp(f):
    f.seek(0)
    sd = sexpdata.load(f)
    symbols = _find_sexp_kids(sd, 'symbol')
    parts = []
    for symbol in symbols:
        uuid_element = _find_sexp_kids(symbol, 'uuid')        
        id = uuid_element[0][1]
        props = _find_sexp_kids(symbol, 'property')
        propsdict = {}
        for prop in props:
            propsdict[prop[1].lower()] = prop[2]
        
        if 'lcsc' in propsdict:
            parts.append(
                SchematicPart(
                    id,
                    propsdict['reference'],
                    propsdict['value'],
                    propsdict['footprint'],
                    propsdict['lcsc']
                    ))                    
    return parts

def read_schematic(fn):
    last_ref = ''
    last_uid = ''
    last_lcsc = False
    last_value = ''
    last_footprint = ''
    parts = []
    with open(fn, 'rt') as f:
        firstline = f.readline()
        # New format:
        if firstline.startswith('(kicad_sch'):
            parts = _read_schematic_sexp(f)
        else:
            # Old format.
            for line in f:
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
        
