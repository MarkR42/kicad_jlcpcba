#
# Create a JLCPCB PCBA set of files to support PCBA, this requires us to
# produce a BOM file and a CPL (component placement file), which will be a
# .pos file.
#
# We do this by reading the associated schematic (mainly for part numbers)
# and then cross-matching the pcb modules.
#

import pcbnew
import os
import re

from . import sch_reader

#
# Setup a few useful globals...
#
global path
global name
global rotdb

#
# Read the rotations.cf config file so we know what rotations to apply
# later.
#
def read_rotdb(filename):
    db = []

    fh = open(filename, "r")
    for line in fh:
        line = line.rstrip()

        line = re.sub('#.*$', '', line)         # remove anything after a comment
        line = re.sub('\s*$', '', line)         # remove all trailing space

        if (line == ""):
            continue

        m = re.match('^([^\s]+)\s+(\d+)$', line)
        if m:
            db.append((m.group(1), int(m.group(2))))

        print(line)
    return db




#
# Given the footprint name, work out what rotation is needed, we support
# matching against the long or short footprint names (if there is a colon
# in the regex)
#
def possible_rotate(footprint):
    fpshort = footprint.split(':')[1]

    for rot in rotdb:
        ex = rot[0]
        delta = rot[1]

        fp = fpshort
        if (re.search(':', ex)):
            fp = footprint

        if(re.search(ex, fp)):
            return delta

    return 0

def read_all_schematics(d):
    """
        Read all schematics in the directory d
        
        returns a list of SchematicPart
    """
    all_parts = []
    for fn in os.listdir(d):
        fn_lower = fn.lower()
        if fn_lower.endswith('.sch') or fn_lower.endswith('.kicad_sch'):
            parts = sch_reader.read_schematic(os.path.join(d, fn))
            all_parts += parts
    return all_parts

used_refs = set()

def deduplicate_reference(ref):
    global used_refs
    
    ref_letters = ''.join(filter(lambda c: not c.isdigit(), ref))
    ref_digits = ''.join(filter(lambda c: c.isdigit(), ref))
    
    if not ref in used_refs:
        used_refs.add(ref)
        return ref
    else:
        # Try +100 etc, until we find an unused ref.
        # Find number in ref
        for n in range(1,10):
            num = int(ref_digits) + (100*n)
            newref = ref_letters + str(num)
            if not newref in used_refs:
                used_refs.add(newref)
                return newref
        
#
# Actually create the PCBA files...
#
def create_pcba():
    global path
    global name
    global rotdb
    global used_refs
    used_refs = set()
    
    board = pcbnew.GetBoard()
    boardfile = board.GetFileName()
    path = os.path.dirname(boardfile)

    # Grab all the schematics
    all_schematic_parts = read_all_schematics(path)
    if len(all_schematic_parts) == 0:
        raise Exception("No JLCPCB parts found in any schematic in current dir")

    name = os.path.splitext(os.path.basename(boardfile))[0]
    
    # Open both layer files...
    posfiles = [] # top and bottom files
    for layer in 'top', 'bottom':
        posfn = os.path.join(path, name + '_' + layer + '_pos.csv')
        f = open(posfn, 'wt')
        print("Designator,Val,Package,Mid X,Mid Y,Rotation,Layer", file=f)
        posfiles.append(f)
        del f
    # Open bom file
    bomfn = os.path.join(path, name + '_bom.csv')
    bomfile = open(bomfn, 'wt')
    print("Comment,Designator,Footprint,LCSC", file=bomfile)

    #
    # Populate the rotation db (do it here so editing and retrying is easy)
    #
    rotdb = read_rotdb(os.path.join(os.path.dirname(__file__), 'rotations.cf'))

    for m in board.GetModules():
        pathstr = m.GetPath().AsString()
        # Gives something like: '/00000000-0000-0000-0000-00005e3c9710'
        uid0 = pathstr.replace('/', '')
        uid = uid0.replace('-', '')
        # Remove leading zeroes
        while uid.startswith('0'):
            uid = uid[1:]
        uid = uid.lower()
        
        smd = ((m.GetAttributes() & pcbnew.MOD_CMS) == pcbnew.MOD_CMS)
        x = m.GetPosition().x/1000000.0
        y = m.GetPosition().y/1000000.0
        rot = m.GetOrientation()/10.0
        layer = m.GetLayerName()
        print("Got module = " + uid + " smd=" + str(smd) + " x=" + str(x) + " y=" + str(y) + " rot=" + str(rot) + "layer="+str(layer))
        if not (smd and (uid != '')):
            # Skip this module, it is not interesting.
            print("  ... Ignoring")
            continue

        # Find the part in the schematic to check its LCSC part number
        # we should match reference, uid and value
        # (in case someone panelised 2 variants of the same pcb with different resistor or capacitor...)
        reference = m.GetReference()
        value =  m.GetValue()
        print("Finding part, uid={} reference={} value={}".format(uid, reference, value)) 
        # TODO
        found_parts = []
        for p in all_schematic_parts:
            if p.uid.lower() in (uid.lower(), uid0.lower()):
                if (p.reference, p.value) == (reference, value):
                    # Found
                    found_parts.append(p)
        if len(found_parts) == 0:
            # If part is not found, we will skip it.
            print(" ... not found")
            continue
        if len(found_parts) > 1:
            raise Exception("Duplicate part found for {}".format(reference))
        found_part = found_parts[0]
        print("Found part in schematic, part {} footprint {}".format(found_part.lcsc, found_part.footprint))
        
        newref = deduplicate_reference(reference)
        print(".. renamed reference to {}".format(newref))
        
        footprint = found_part.footprint

        # Now do the rotation needed...
        rot = (rot + possible_rotate(footprint)) % 360

        # Now write to the top and bottom file respectively
        fpshort = footprint.split(':')[1]
        fh = posfiles[0]
        lname = "top"
        y = y * -1                  # y is negative always???
        if (smd):
            if (layer == "B.Cu"):   
                fh = posfiles[1]
                lname = "bottom"

            print('"{}","{}","{}",{},{},{},{}'.format(
                newref, value, fpshort, x, y, rot, lname),
                file=fh)
            del fh
            
            # comment, reference, footprint, lcsc
            print('"{}","{}","{}","{}"'.format(
                value, newref, fpshort, found_part.lcsc),
                file=bomfile)

    for f in posfiles:
        f.close()
    bomfile.close()

#create()
