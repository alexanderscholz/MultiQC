#!/usr/bin/env python

""" MultiQC module to parse output from Adapter Removal """

from __future__ import print_function
from collections import OrderedDict
import logging
import copy

from multiqc import config
from multiqc.plots import bargraph
from multiqc.plots import linegraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Adapter Removal',
        anchor='adapterRemoval', target='Adapter Removal',
        href='https://github.com/MikkelSchubert/adapterremoval',
        info=" rapid adapter trimming, identification, and read merging ")

        self.__read_type = None
        self.__collapsed = None
        self.s_name = None
        self.adapter_removal_data = {
            'single': dict(),
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }

        # variable definition for single- and paired-end reads
        self.arc_mate1 = {
            'single': dict(),
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }
        self.arc_discarged = {
            'single': dict(),
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }
        self.arc_all = {
            'single': dict(),
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }

        # variable definition for paired-end only reads
        self.arc_mate2 = {
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }
        self.arc_singleton = {
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }
        self.arc_collapsed = {
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }
        self.arc_collapsed_truncated = {
            'paired': {
                'collapsed': dict(),
                'noncollapsed': dict(),
            }
        }

        for f in self.find_log_files(config.sp['adapterRemoval'], filehandles=True):
            self.s_name = f['s_name']
            try:
                parsed_data = self.parse_settings_file(f)
            except UserWarning:
                continue
            if parsed_data is not None:
                if self.__read_type == 'single':
                    self.adapter_removal_data[self.__read_type][self.s_name] = parsed_data
                else:
                    if self.__collapsed:
                        self.adapter_removal_data[self.__read_type]['collapsed'][self.s_name] = parsed_data
                    else:
                        self.adapter_removal_data[self.__read_type]['noncollapsed'][self.s_name] = parsed_data

        if len(self.adapter_removal_data['single']) == 0 and len(self.adapter_removal_data['paired']) == 0:
            log.warning("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        elements_count = len(self.adapter_removal_data['single']) + len(self.adapter_removal_data['paired'])
        log.info("Found {} reports".format(elements_count))

        # Write parsed report data to a file
        self.write_data_file(self.adapter_removal_data, 'multiqc_adapter_removal')

        # Start the sections
        self.sections = list()

        self.adapter_removal_counts_chart()
        self.adapter_removal_retained_chart()
        self.adapter_removal_length_dist_plot()

    def parse_settings_file(self, f):

        self.result_data = {
            'total': None,
            'unaligned': None,
            'aligned': None,
            'reads_total': None,
            'retained': None,
            'discarded': None,
        }

        settings_data = {'header': []}

        block_title = None
        for i, line in enumerate(f['f']):

            line = line.rstrip('\n')
            if line == '':
                continue

            if not block_title:
                block_title = 'header'
                settings_data[block_title].append(str(line))
                continue

            if line.startswith('['):
                block_title = str(line.strip('[]'))
                settings_data[block_title] = []
                continue

            settings_data[block_title].append(str(line))

        # set data for further working
        self.set_result_data(settings_data)

        return self.result_data

    def set_result_data(self, settings_data):
        # set read and collapsed type
        self.set_ar_type(settings_data['Length distribution'])

        # set result_data
        self.set_trim_stat(settings_data['Trimming statistics'])
        self.set_len_dist(settings_data['Length distribution'])

    def set_ar_type(self, len_dist_data):
        head_line = len_dist_data[0].rstrip('\n').split('\t')
        self.__read_type = 'paired' if head_line[2] == 'Mate2' else 'single'
        self.__collapsed = True if head_line[-3] == 'CollapsedTruncated' else False

        # biological/technical relevance is not clear -> skip
        if self.__read_type == 'single' and self.__collapsed:
            log.warning("Case single-end and collapse is not " \
                        "implemented -> File %s skipped" % self.s_name)
            raise UserWarning

    def set_trim_stat(self, trim_data):
        data_pattern = {'total': 0,
                        'unaligned': 1,
                        'aligned': 2,
                        'retained': -3}

        for title, key in data_pattern.iteritems():
            tmp = trim_data[key]
            value = tmp.split(': ')[1]
            self.result_data[title] = int(value)

        reads_total = self.result_data['total']
        if self.__read_type == 'paired':
            reads_total = self.result_data['total'] * 2

        self.result_data['reads_total'] = reads_total
        self.result_data['discarded'] = reads_total - self.result_data['retained']

    def set_len_dist(self, len_dist_data):

        for line in len_dist_data[1:]:
            l_data = line.rstrip('\n').split('\t')
            l_data = map(int, l_data)
            if self.__read_type == 'single':
                if not self.__collapsed:
                    if self.s_name not in self.arc_mate1['single']:
                        self.arc_mate1['single'][self.s_name] = dict()
                    self.arc_mate1['single'][self.s_name][l_data[0]] = l_data[1]

                    if self.s_name not in self.arc_discarged['single']:
                        self.arc_discarged['single'][self.s_name] = dict()
                    self.arc_discarged['single'][self.s_name][l_data[0]] = l_data[2]

                    if self.s_name not in self.arc_all['single']:
                        self.arc_all['single'][self.s_name] = dict()
                    self.arc_all['single'][self.s_name][l_data[0]] = l_data[3]
                else:
                    # this case should not be reached (see case at method set_ar_type())
                    pass
            else:
                if not self.__collapsed:
                    if self.s_name not in self.arc_mate1['paired']['noncollapsed']:
                        self.arc_mate1['paired']['noncollapsed'][self.s_name] = dict()
                    self.arc_mate1['paired']['noncollapsed'][self.s_name][l_data[0]] = l_data[1]

                    if self.s_name not in self.arc_mate2['paired']['noncollapsed']:
                        self.arc_mate2['paired']['noncollapsed'][self.s_name] = dict()
                    self.arc_mate2['paired']['noncollapsed'][self.s_name][l_data[0]] = l_data[2]

                    if self.s_name not in self.arc_singleton['paired']['noncollapsed']:
                        self.arc_singleton['paired']['noncollapsed'][self.s_name] = dict()
                    self.arc_singleton['paired']['noncollapsed'][self.s_name][l_data[0]] = l_data[3]

                    if self.s_name not in self.arc_discarged['paired']['noncollapsed']:
                        self.arc_discarged['paired']['noncollapsed'][self.s_name] = dict()
                    self.arc_discarged['paired']['noncollapsed'][self.s_name][l_data[0]] = l_data[4]

                    if self.s_name not in self.arc_all['paired']['noncollapsed']:
                        self.arc_all['paired']['noncollapsed'][self.s_name] = dict()
                    self.arc_all['paired']['noncollapsed'][self.s_name][l_data[0]] = l_data[5]
                else:
                    if self.s_name not in self.arc_mate1['paired']['collapsed']:
                        self.arc_mate1['paired']['collapsed'][self.s_name] = dict()
                    self.arc_mate1['paired']['collapsed'][self.s_name][l_data[0]] = l_data[1]

                    if self.s_name not in self.arc_mate2['paired']['collapsed']:
                        self.arc_mate2['paired']['collapsed'][self.s_name] = dict()
                    self.arc_mate2['paired']['collapsed'][self.s_name][l_data[0]] = l_data[2]

                    if self.s_name not in self.arc_singleton['paired']['collapsed']:
                        self.arc_singleton['paired']['collapsed'][self.s_name] = dict()
                    self.arc_singleton['paired']['collapsed'][self.s_name][l_data[0]] = l_data[3]

                    if self.s_name not in self.arc_collapsed['paired']['collapsed']:
                        self.arc_collapsed['paired']['collapsed'][self.s_name] = dict()
                    self.arc_collapsed['paired']['collapsed'][self.s_name][l_data[0]] = l_data[4]

                    if self.s_name not in self.arc_collapsed_truncated['paired']['collapsed']:
                        self.arc_collapsed_truncated['paired']['collapsed'][self.s_name] = dict()
                    self.arc_collapsed_truncated['paired']['collapsed'][self.s_name][l_data[0]] = l_data[5]

                    if self.s_name not in self.arc_discarged['paired']['collapsed']:
                        self.arc_discarged['paired']['collapsed'][self.s_name] = dict()
                    self.arc_discarged['paired']['collapsed'][self.s_name][l_data[0]] = l_data[6]

                    if self.s_name not in self.arc_all['paired']['collapsed']:
                        self.arc_all['paired']['collapsed'][self.s_name] = dict()
                    self.arc_all['paired']['collapsed'][self.s_name][l_data[0]] = l_data[7]

    def adapter_removal_counts_chart(self):

        cats = OrderedDict()
        cats['aligned'] = {'name': 'with adapter'}
        cats['unaligned'] = {'name': 'without adapter'}
        pconfig = {
            'title': 'Adapter Alignments',
            'ylab': '# Reads',
            'hide_zero_cats': False,
            'cpswitch_counts_label': 'Number of Reads'
        }

        # plot different results if exists
        if self.adapter_removal_data['single']:
            pconfig['id'] = 'ar_alignment_plot_se'
            self.sections.append({
                'name': 'Adapter Alignments Single-End',
                'anchor': 'ar_alignment_se',
                'content': '<p>The proportions of reads with and without adapter.</p>' +
                           bargraph.plot(self.adapter_removal_data['single'], cats, pconfig)
            })

        if self.adapter_removal_data['paired']['noncollapsed']:
            pconfig['id'] = 'ar_alignment_plot_penc'
            self.sections.append({
                'name': 'Adapter Alignments Paired-End Noncollapsed',
                'anchor': 'adapter_removal_alignment_penc',
                'content': '<p>The proportions of reads with and without adapter.</p>' +
                           bargraph.plot(self.adapter_removal_data['paired']['noncollapsed'], cats, pconfig)
            })

        if self.adapter_removal_data['paired']['collapsed']:
            pconfig['id'] = 'ar_alignment_plot_pec'
            self.sections.append({
                'name': 'Adapter Alignments Paired-End Collapsed',
                'anchor': 'adapter_removal_alignment_pec',
                'content': '<p>The proportions of reads with and without adapter.</p>' +
                           bargraph.plot(self.adapter_removal_data['paired']['collapsed'], cats, pconfig)
            })

    def adapter_removal_retained_chart(self):

        cats = OrderedDict()
        cats['retained'] = {'name': 'retained'}
        cats['discarded'] = {'name': 'discarded'}
        pconfig = {
            'title': 'retained and discarded',
            'ylab': '# Reads',
            'hide_zero_cats': False,
            'cpswitch_counts_label': 'Number of Reads'
        }

        # plot different results if exists
        if self.adapter_removal_data['single']:
            pconfig['id'] = 'ar_retained_plot_se'
            self.sections.append({
                'name': 'Retained and Discarded Single-End',
                'anchor': 'adapter_removal_retained_plot_se',
                'content': '<p>The proportions of retained and discarded reads.</p>' +
                           bargraph.plot(self.adapter_removal_data['single'], cats, pconfig)
            })

        if self.adapter_removal_data['paired']['noncollapsed']:
            pconfig['id'] = 'ar_retained_plot_penc'
            self.sections.append({
                'name': 'Retained and Discarded Paired-End Noncollapsed',
                'anchor': 'adapter_removal_retained_plot_penc',
                'content': '<p>The proportions of retained and discarded reads.</p>' +
                           bargraph.plot(self.adapter_removal_data['paired']['noncollapsed'], cats, pconfig)
            })

        if self.adapter_removal_data['paired']['collapsed']:
            pconfig['id'] = 'ar_retained_plot_pec'
            self.sections.append({
                'name': 'Retained and Discarded Paired-End Collapsed',
                'anchor': 'adapter_removal_retained_plot_pec',
                'content': '<p>The proportions of retained and discarded reads.</p>' +
                           bargraph.plot(self.adapter_removal_data['paired']['collapsed'], cats, pconfig)
            })

    def adapter_removal_length_dist_plot(self):

        config_template = {
            'title': 'Length Distribution',
            'ylab': 'Counts',
            'xlab': 'read length',
            'xDecimals': False,
            'ymin': 0,
            'tt_label': '<b>{point.x} bp trimmed</b>: {point.y:.0f}',
            'data_labels': []
        }

        pconfig = {
            'single': copy.deepcopy(config_template),
            'paired': {
                'collapsed': copy.deepcopy(config_template),
                'noncollapsed': copy.deepcopy(config_template),
            }
        }

        dl_mate1 = {'name': 'Mate1', 'ylab': 'Count'}
        dl_mate2 = {'name': 'Mate2', 'ylab': 'Count'}
        dl_singleton = {'name': 'Singleton', 'ylab': 'Count'}
        dl_collapsed = {'name': 'Collapsed', 'ylab': 'Count'}
        dl_collapsed_truncated = {'name': 'Collapsed Truncated', 'ylab': 'Count'}
        dl_discarded = {'name': 'Discarded', 'ylab': 'Count'}
        dl_all = {'name': 'All', 'ylab': 'Count'}

        lineplot_data = {
            'single': None,
            'paired': {
                'collapsed': None,
                'noncollapsed': None,
            }
        }

        if self.adapter_removal_data['single']:
            lineplot_data['single'] = [
                self.arc_mate1['single'],
                self.arc_discarged['single'],
                self.arc_all['single']]
            pconfig['single']['id'] = 'ar_lenght_count_plot_se'
            pconfig['single']['data_labels'].extend([
                dl_mate1,
                dl_discarded,
                dl_all])
            self.sections.append({
                'name': 'Lenght Distribution Single End',
                'anchor': 'ar_lenght_count_se',
                'content': '<p>The lenght distribution of reads after processing adapter alignment.</p>' +
                           linegraph.plot(lineplot_data['single'], pconfig['single'])
            })

        if self.adapter_removal_data['paired']['noncollapsed']:
            lineplot_data['paired']['noncollapsed'] = [
                self.arc_mate1['paired']['noncollapsed'],
                self.arc_mate2['paired']['noncollapsed'],
                self.arc_singleton['paired']['noncollapsed'],
                self.arc_discarged['paired']['noncollapsed'],
                self.arc_all['paired']['noncollapsed']]
            pconfig['paired']['noncollapsed']['id'] = 'ar_lenght_count_plot_penc'
            pconfig['paired']['noncollapsed']['data_labels'].extend([
                dl_mate1,
                dl_mate2,
                dl_singleton,
                dl_discarded,
                dl_all])
            self.sections.append({
                'name': 'Lenght Distribution Paired End Noncollapsed',
                'anchor': 'ar_lenght_count_penc',
                'content': '<p>The lenght distribution of reads after processing adapter alignment.</p>' +
                           linegraph.plot(lineplot_data['paired']['noncollapsed'], pconfig['paired']['noncollapsed'])
            })

        if self.adapter_removal_data['paired']['collapsed']:
            lineplot_data['paired']['collapsed'] = [
                self.arc_mate1['paired']['collapsed'],
                self.arc_mate2['paired']['collapsed'],
                self.arc_singleton['paired']['collapsed'],
                self.arc_collapsed['paired']['collapsed'],
                self.arc_collapsed_truncated['paired']['collapsed'],
                self.arc_discarged['paired']['collapsed'],
                self.arc_all['paired']['collapsed']]
            pconfig['paired']['collapsed']['id'] = 'ar_lenght_count_plot_pec'
            pconfig['paired']['collapsed']['data_labels'].extend([
                dl_mate1,
                dl_mate2,
                dl_singleton,
                dl_collapsed,
                dl_collapsed_truncated,
                dl_discarded,
                dl_all])
            self.sections.append({
                'name': 'Lenght Distribution Paired End Collapsed',
                'anchor': 'ar_lenght_count_pec',
                'content': '<p>The lenght distribution of reads after processing adapter alignment.</p>' +
                           linegraph.plot(lineplot_data['paired']['collapsed'], pconfig['paired']['collapsed'])
            })