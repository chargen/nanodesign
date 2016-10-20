#!/usr/bin/env python
"""
This module is used to write caDNAno design JSON files.
"""
import json
import logging
from cadnano.common import CadnanoLatticeName,CadnanoLatticeType

try:
    import os.path
    import sys
    base_path = os.path.abspath( os.path.dirname(__file__) + '/../../../' )
    sys.path.append( base_path )
    from nanodesign_transition.parameters import DnaParameters
    sys.path = sys.path[:-1]
except ImportError as i:
    print "Could not get nanodesign_transition module"
    raise i

class CadnanoWriter(object):
    """ The CadnanoWriter class is used to write out a caDNAno design JSON file.
    """
    def __init__(self, dna_structure):
        self.dna_structure = dna_structure
        self._logging_level = logging.INFO
        self._setup_logging()

    def _setup_logging(self):
        """ Set up logging."""
        self._logger = logging.getLogger(__name__)
        #self._logger = logging.getLogger('viewer:writer')
        self._logger.setLevel(self._logging_level)

        # Create console handler and set format.
        console_handler = logging.StreamHandler()
        #formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s')
        formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    def write(self,file_name):
        """ Write a caDNAno design JSON file.

        Args:
            file_name (string): The name of a caDNAno JSON file to write.
        """
        self._logger.info("Writing caDNAno design JSON file: %s " % file_name)
        dna_structure = self.dna_structure
        dna_structure.compute_aux_data()
        vstrand_info = self._get_vstrand_info(dna_structure)

        design = { 'name'    : os.path.basename(file_name),
                   'vstrands': vstrand_info
                 }

        with open(file_name, 'w') as outfile:
            json.dump(design, outfile, indent=4, separators=(',', ': '))

    def _get_vstrand_info(self, dna_structure):
        """ Get virtual helix information for the design. 

            In caDNAno all the virtual helices are the same size (i.e. the same number of base positions).
            The lists of helix bases for staple and scaffold strands may contain fewer bases than the 
            virtual helix size so we create an array of empty helix positions ([-1,-1,-1,-1]) for the caDNAno 
            virtual helix size and fill from the base lists. 
        """
        self._logger.info("Number of helices %d " % len(dna_structure.structure_helices_map))
        vstrands_info = []

        # Create a map of helix nums to the list of strands that start in that helix.
        # Used for writing color information.
        helix_strands_map = {}
        for strand in dna_structure.strands:
            if strand.is_scaffold: 
                continue
            base = strand.tour[0]
            if base.h not in helix_strands_map: 
                helix_strands_map[base.h] = []
            helix_strands_map[base.h].append(strand)
        #__for strand in dna_structure.strands

        # Create a map of the helices by ID so we can reproduce the order in which 
        # they were read in from the original caDNAno file.
        helix_map = {}
        for helix in dna_structure.structure_helices_map.itervalues():
            helix_map[helix.count] = helix 

        # Get the base connectivity, loops and skips for the staple and scaffold strands.
        for count in sorted(helix_map):
            helix = helix_map[count] 
            scaffold_base_list = helix.scaffold_base_list
            staple_base_list = helix.staple_base_list
            helix_size = helix.lattice_max_vhelix_size 
            row = helix.lattice_row 
            col = helix.lattice_col
            num = helix.lattice_num
            self._logger.info("Helix count %d  num %d  row %d  col %d" % (count, num, row, col)) 

            # Set the arrays for the virtual helix base information.
            scaf_info = self._get_base_info(helix_size, scaffold_base_list)
            stap_info = self._get_base_info(helix_size, staple_base_list)
            loop_info = self._get_loop_info(helix_size, staple_base_list)
            skip_info = self._get_skip_info(helix_size, staple_base_list)
            staple_colors = self._get_staple_colors(helix_strands_map[num])

            vstrand = { "row": row,
                        "col": col,
                        "num": num,
                        "scaf": scaf_info,
                        "stap": stap_info,
                        "loop": loop_info,
                        "skip": skip_info,
                        "stap_colors": staple_colors
                      }

            vstrands_info.append( vstrand )
        #__for count in sorted(helix_map)

        return vstrands_info
    #__def _get_vstrand_info

    def _get_staple_colors(self, strands):
        """ Get the array of staple colors for the strands originating in a given helix.
   
            Arguments:
                strands (List[DnaStrand]): The list of strands originating in a given helix.

            Returns the list of staple colors, staple_colors[].

            In caDNAno staple colors are defined as an array of two-entry elements containing
            the staple starting position in the virtual helix and an integer color.
        """
        staple_colors = []
        for strand in strands:
            pos = strand.tour[0].p # Strand starting position.
            color = int(255*strand.color[0])<<16 | int(255*strand.color[1])<<8 | int(255*strand.color[2])
            staple_colors.append([pos,color])
        #__for strand in strands
        return staple_colors
    #__def _get_staple_colors

    def _get_base_info(self, helix_size, base_list):
        """ Get the array defining caDNAno base information from the list of bases. 

            Arguments:
                helix_size (int): The size of caDNAno virtual helix.
                base_list (DnaBase): The list of bases for a helix. 

            Create an array of empty helix positions ([-1,-1,-1,-1]) for the caDNAno virtual helix
            and fill it in at the positions given by the bases in the base list (DnaBase.p).
        """
        base_info = [[-1,-1,-1,-1]]*helix_size
        for base in base_list:
            if base.up == None:
                up_pos = -1
                up_vh = -1
            else:
                up_pos = base.up.p
                up_vh = base.up.h
            if base.down == None:
                down_pos = -1
                down_vh = -1
            else:
                down_pos = base.down.p
                down_vh = base.down.h
            base_info[base.p] = [up_vh, up_pos, down_vh, down_pos]
        #__for base in base_list
        return base_info 

    def _get_loop_info(self, helix_size, base_list):
        """ Get the loop (insert) information for each base. 

            Arguments:
                helix_size (int): The size of caDNAno virtual helix.
                base_list (DnaBase): The list of bases for a helix. 
        """
        loop_info = [0]*helix_size
        for base in base_list:
            loop_info[base.p] = base.num_insertions
        return loop_info
    #__def _get_loop_info

    def _get_skip_info(self, helix_size, base_list):
        """ Get the skip (deletion) information for each base.

            Arguments:
                helix_size (int): The size of caDNAno virtual helix.
                base_list (DnaBase): The list of bases for a helix. 
        """
        skip_info = [0]*helix_size
        for base in base_list:
            skip_info[base.p] = base.num_deletions
        return skip_info
    #__def _get_skip_info

