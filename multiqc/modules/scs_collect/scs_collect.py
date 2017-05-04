#!/usr/bin/env python

""" MultiQC module to parse output from SCS-Collect """

from __future__ import print_function
from collections import OrderedDict
import logging
import yaml

from multiqc import config
from multiqc.plots import bargraph, table
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        self.data = {
            'genome_types': {},
            'composition': {}
        }

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='SCS-Collect',
        anchor='scs_collect', target='SCS-Collect')

        parsed_data = None
        for f in self.find_log_files('scs_collect', filehandles=True):
            self.s_name = f['s_name']
            try:
                parsed_data = self.parse_input_file(f)
                pass
            except UserWarning:
                continue

            if parsed_data['gt'] is not None and parsed_data['c'] is not None:
                self.data['genome_types'][self.s_name] = parsed_data['gt']
                self.data['composition'][self.s_name] = parsed_data['c']

        count = len(self.data['genome_types']) + len(self.data['composition'])
        if count == 0:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(count))

        self.plot_genome_types()
        self.plot_rna_composition()

    def parse_input_file(self, input_file):
        parsed_data = yaml.load(input_file['f'])

        genome_types = dict()
        composition_data = None

        # separate data
        for key, value in parsed_data.items():
            if type(key) is int:
                genome_types[key] = value
            elif key == 'rnacomposition':
                composition_data = value
            else:
                pass

        result = dict()
        gt_data = self.prepare_gt(genome_types)

        if gt_data:
            result['gt'] = gt_data

        result['c'] = composition_data

        return result

    def prepare_gt(self, data):
        result = OrderedDict()

        for key, data_set in data.items():
            title = data_set['type']

            for type, value in data_set['values'].items():
                result['%s_%s' % (title, type)] = int(value)

        return result

    def plot_genome_types(self):
        pconfig = {
            'title': 'genome types',
            'id': 'gt_plot',
            'ylab': '# Reads',
            'hide_zero_cats': False,
            'cpswitch_counts_label': 'Number of Reads',
        }

        self.add_section(
            name='genome types and proportions',
            anchor='genome_types_plot',
            description='',
            plot=bargraph.plot(self.data['genome_types'], pconfig=pconfig)
        )

    def plot_rna_composition(self):
        self.add_section(
            name='rna composition',
            anchor='rna_composition_plot',
            description='',
            plot=bargraph.plot(self.data['composition'])
        )