import os.path
from nipype import config
config.enable_debug_mode()
import subprocess as sp  # @IgnorePep8
from nianalysis.dataset import Dataset, DatasetSpec  # @IgnorePep8
from nianalysis.data_formats import nifti_gz_format, mrtrix_format, text_format  # @IgnorePep8
from nianalysis.requirements import mrtrix3_req  # @IgnorePep8
from nipype.interfaces.utility import Merge
from nianalysis.study.base import Study, set_dataset_specs  # @IgnorePep8
from nianalysis.interfaces.mrtrix import MRConvert, MRCat, MRMath, MRCalc  # @IgnorePep8
from nianalysis.testing import BaseTestCase, BaseMultiSubjectTestCase  # @IgnorePep8
from nianalysis.nodes import NiAnalysisNodeMixin  # @IgnorePep8
from nianalysis.exceptions import NiAnalysisModulesNotInstalledException  # @IgnorePep8
import logging  # @IgnorePep8
from nipype.interfaces.base import (  # @IgnorePep8
    BaseInterface, File, TraitedSpec, traits, isdefined)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("workflow").setLevel(logging.INFO)

logger = logging.getLogger('NiAnalysis')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class DummyStudy(Study):

    def pipeline1(self, **options):
        pipeline = self.create_pipeline(
            name='pipeline1',
            inputs=[DatasetSpec('start', nifti_gz_format)],
            outputs=[DatasetSpec('pipeline1_1', nifti_gz_format),
                     DatasetSpec('pipeline1_2', nifti_gz_format)],
            description="A dummy pipeline used to test 'run_pipeline' method",
            default_options={'pipeline1_option': False},
            version=1,
            citations=[],
            options=options)
        if not pipeline.option('pipeline1_option'):
            raise Exception("Pipeline 1 option was not cascaded down")
        mrconvert = pipeline.create_node(MRConvert(), name="convert1",
                                         requirements=[mrtrix3_req])
        mrconvert2 = pipeline.create_node(MRConvert(), name="convert2",
                                          requirements=[mrtrix3_req])
        # Connect inputs
        pipeline.connect_input('start', mrconvert, 'in_file')
        pipeline.connect_input('start', mrconvert2, 'in_file')
        # Connect outputs
        pipeline.connect_output('pipeline1_1', mrconvert, 'out_file')
        pipeline.connect_output('pipeline1_2', mrconvert2, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def pipeline2(self, **options):
        pipeline = self.create_pipeline(
            name='pipeline2',
            inputs=[DatasetSpec('start', nifti_gz_format),
                    DatasetSpec('pipeline1_1', nifti_gz_format)],
            outputs=[DatasetSpec('pipeline2', nifti_gz_format)],
            description="A dummy pipeline used to test 'run_pipeline' method",
            default_options={},
            version=1,
            citations=[],
            options=options)
        mrmath = pipeline.create_node(MRCat(), name="mrcat",
                                      requirements=[mrtrix3_req])
        mrmath.inputs.axis = 0
        # Connect inputs
        pipeline.connect_input('start', mrmath, 'first_scan')
        pipeline.connect_input('pipeline1_1', mrmath, 'second_scan')
        # Connect outputs
        pipeline.connect_output('pipeline2', mrmath, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def pipeline3(self, **options):
        pipeline = self.create_pipeline(
            name='pipeline3',
            inputs=[DatasetSpec('pipeline2', nifti_gz_format)],
            outputs=[DatasetSpec('pipeline3', nifti_gz_format)],
            description="A dummy pipeline used to test 'run_pipeline' method",
            default_options={},
            version=1,
            citations=[],
            options=options)
        mrconvert = pipeline.create_node(MRConvert(), name="convert")
        # Connect inputs
        pipeline.connect_input('pipeline2', mrconvert, 'in_file')
        # Connect outputs
        pipeline.connect_output('pipeline3', mrconvert, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def pipeline4(self, **options):
        pipeline = self.create_pipeline(
            name='pipeline4',
            inputs=[DatasetSpec('pipeline1_2', nifti_gz_format),
                    DatasetSpec('pipeline3', nifti_gz_format)],
            outputs=[DatasetSpec('pipeline4', nifti_gz_format)],
            description="A dummy pipeline used to test 'run_pipeline' method",
            default_options={},
            version=1,
            citations=[],
            options=options)
        mrmath = pipeline.create_node(MRCat(), name="mrcat",
                                      requirements=[mrtrix3_req])
        mrmath.inputs.axis = 0
        # Connect inputs
        pipeline.connect_input('pipeline1_2', mrmath, 'first_scan')
        pipeline.connect_input('pipeline3', mrmath, 'second_scan')
        # Connect outputs
        pipeline.connect_output('pipeline4', mrmath, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def visit_ids_access_pipeline(self):
        pipeline = self.create_pipeline(
            name='visit_ids_access',
            inputs=[],
            outputs=[DatasetSpec('visit_ids', text_format)],
            description=(
                "A dummy pipeline used to test access to 'session' IDs"),
            default_options={},
            version=1,
            citations=[])
        sessions_to_file = pipeline.create_join_visits_node(
            IteratorToFile(), name='sessions_to_file', joinfield='ids')
        pipeline.connect_visit_id(sessions_to_file, 'ids')
        pipeline.connect_output('visit_ids', sessions_to_file, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def subject_ids_access_pipeline(self):
        pipeline = self.create_pipeline(
            name='subject_ids_access',
            inputs=[],
            outputs=[DatasetSpec('subject_ids', text_format)],
            description=(
                "A dummy pipeline used to test access to 'subject' IDs"),
            default_options={},
            version=1,
            citations=[])
        subjects_to_file = pipeline.create_join_subjects_node(
            IteratorToFile(), name='subjects_to_file', joinfield='ids')
        pipeline.connect_subject_id(subjects_to_file, 'ids')
        pipeline.connect_output('subject_ids', subjects_to_file, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def subject_summary_pipeline(self):
        pipeline = self.create_pipeline(
            name="subject_summary",
            inputs=[DatasetSpec('ones_slice', mrtrix_format)],
            outputs=[DatasetSpec('subject_summary', mrtrix_format)],
            description=("Test of project summary variables"),
            default_options={},
            version=1,
            citations=[],)
        mrmath = pipeline.create_join_visits_node(
            MRMath(), 'in_files', 'mrmath', requirements=[mrtrix3_req])
        mrmath.inputs.operation = 'sum'
        # Connect inputs
        pipeline.connect_input('ones_slice', mrmath, 'in_files')
        # Connect outputs
        pipeline.connect_output('subject_summary', mrmath, 'out_file')
        pipeline.assert_connected()
        return pipeline

    def visit_summary_pipeline(self):
        pipeline = self.create_pipeline(
            name="visit_summary",
            inputs=[DatasetSpec('ones_slice', mrtrix_format)],
            outputs=[DatasetSpec('visit_summary', mrtrix_format)],
            description=("Test of project summary variables"),
            default_options={},
            version=1,
            citations=[],)
        mrmath = pipeline.create_join_visits_node(
            MRMath(), 'in_files', 'mrmath', requirements=[mrtrix3_req])
        mrmath.inputs.operation = 'sum'
        # Connect inputs
        pipeline.connect_input('ones_slice', mrmath, 'in_files')
        # Connect outputs
        pipeline.connect_output('visit_summary', mrmath, 'out_file')
        pipeline.assert_connected()
        return pipeline

    def project_summary_pipeline(self):
        pipeline = self.create_pipeline(
            name="project_summary",
            inputs=[DatasetSpec('ones_slice', mrtrix_format)],
            outputs=[DatasetSpec('project_summary', mrtrix_format)],
            description=("Test of project summary variables"),
            default_options={},
            version=1,
            citations=[],)
        mrmath1 = pipeline.create_join_visits_node(
            MRMath(), 'in_files', 'mrmath1', requirements=[mrtrix3_req])
        mrmath2 = pipeline.create_join_subjects_node(
            MRMath(), 'in_files', 'mrmath2', requirements=[mrtrix3_req])
        mrmath1.inputs.operation = 'sum'
        mrmath2.inputs.operation = 'sum'
        # Connect inputs
        pipeline.connect_input('ones_slice', mrmath1, 'in_files')
        pipeline.connect(mrmath1, 'out_file', mrmath2, 'in_files')
        # Connect outputs
        pipeline.connect_output('project_summary', mrmath2, 'out_file')
        pipeline.assert_connected()
        return pipeline

    _dataset_specs = set_dataset_specs(
        DatasetSpec('start', nifti_gz_format),
        DatasetSpec('ones_slice', mrtrix_format),
        DatasetSpec('pipeline1_1', nifti_gz_format, pipeline1),
        DatasetSpec('pipeline1_2', nifti_gz_format, pipeline1),
        DatasetSpec('pipeline2', nifti_gz_format, pipeline2),
        DatasetSpec('pipeline3', nifti_gz_format, pipeline3),
        DatasetSpec('pipeline4', nifti_gz_format, pipeline4),
        DatasetSpec('subject_summary', mrtrix_format, subject_summary_pipeline,
                    multiplicity='per_subject'),
        DatasetSpec('visit_summary', mrtrix_format,
                    visit_summary_pipeline,
                    multiplicity='per_visit'),
        DatasetSpec('project_summary', mrtrix_format, project_summary_pipeline,
                    multiplicity='per_project'),
        DatasetSpec('subject_ids', text_format, subject_ids_access_pipeline,
                    multiplicity='per_visit'),
        DatasetSpec('visit_ids', text_format, visit_ids_access_pipeline,
                    multiplicity='per_subject'))


class IteratorToFileInputSpec(TraitedSpec):
    ids = traits.List(traits.Str(), desc="ID of the iterable")
    out_file = File(genfile=True, desc="The name of the generated file")


class IteratorToFileOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output file containing iterables")


class IteratorToFile(BaseInterface):

    input_spec = IteratorToFileInputSpec
    output_spec = IteratorToFileOutputSpec

    def _run_interface(self, runtime):
        with open(self._gen_filename('out_file'), 'w') as f:
            f.write('\n'.join(str(i) for i in self.inputs.ids))
        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = self._gen_filename('out_file')
        return outputs

    def _gen_filename(self, name):
        if name == 'out_file':
            if isdefined(self.inputs.out_file):
                fname = self.inputs.out_file
            else:
                fname = os.path.join(os.getcwd(), 'out.txt')
        else:
            assert False
        return fname


class TestRunPipeline(BaseTestCase):

    SUBJECT_IDS = ['SUBJECTID1', 'SUBJECTID2', 'SUBJECTID3']
    SESSION_IDS = ['SESSIONID1', 'SESSIONID2']

    def setUp(self):
        try:
            NiAnalysisNodeMixin.load_module('mrtrix')
        except NiAnalysisModulesNotInstalledException:
            pass
        self.reset_dirs()
        for subject_id in self.SUBJECT_IDS:
            for visit_id in self.SESSION_IDS:
                self.add_session(self.project_dir, subject_id, visit_id)
        self.study = self.create_study(
            DummyStudy, 'dummy', input_datasets={
                'start': Dataset('start', nifti_gz_format),
                'ones_slice': Dataset('ones_slice', mrtrix_format)})

    def tearDown(self):
        try:
            NiAnalysisNodeMixin.unload_module('mrtrix')
        except NiAnalysisModulesNotInstalledException:
            pass

    def test_pipeline_prerequisites(self):
        pipeline = self.study.pipeline4(pipeline1_option=True)
        pipeline.run(work_dir=self.work_dir)
        for dataset in DummyStudy.dataset_specs():
            if dataset.multiplicity == 'per_session' and dataset.processed:
                for subject_id in self.SUBJECT_IDS:
                    for visit_id in self.SESSION_IDS:
                        self.assertDatasetCreated(
                            dataset.name + dataset.format.extension,
                            self.study.name, subject=subject_id,
                            session=visit_id)

    def test_subject_summary(self):
        self.study.subject_summary_pipeline().run(work_dir=self.work_dir)
        for subject_id in self.SUBJECT_IDS:
            # Get mean value from resultant image (should be the same as the
            # number of sessions as the original image is full of ones and
            # all sessions have been summed together
            mean_val = float(sp.check_output(
                'mrstats {} -output mean'.format(
                    self.output_file_path(
                        'subject_summary.mif', self.study.name,
                        subject=subject_id, multiplicity='per_subject')),
                shell=True))
            self.assertEqual(mean_val, len(self.SESSION_IDS))

    def test_visit_summary(self):
        self.study.visit_summary_pipeline().run(work_dir=self.work_dir)
        for visit_id in self.SESSION_IDS:
            # Get mean value from resultant image (should be the same as the
            # number of sessions as the original image is full of ones and
            # all sessions have been summed together
            mean_val = float(sp.check_output(
                'mrstats {} -output mean'.format(
                    self.output_file_path(
                        'visit_summary.mif', self.study.name,
                        session=visit_id, multiplicity='per_visit')),
                shell=True))
            self.assertEqual(mean_val, len(self.SESSION_IDS))

    def test_project_summary(self):
        self.study.project_summary_pipeline().run(work_dir=self.work_dir)
        # Get mean value from resultant image (should be the same as the
        # number of sessions as the original image is full of ones and
        # all sessions have been summed together
        mean_val = float(sp.check_output(
            'mrstats {} -output mean'.format(self.output_file_path(
                'project_summary.mif', self.study.name,
                multiplicity='per_project')),
            shell=True))
        self.assertEqual(mean_val,
                         len(self.SUBJECT_IDS) * len(self.SESSION_IDS))

    def test_subject_ids_access(self):
        self.study.subject_ids_access_pipeline().run(work_dir=self.work_dir)
        for visit_id in self.SESSION_IDS:
            subject_ids_path = self.output_file_path(
                'subject_ids.txt', self.study.name,
                session=visit_id, multiplicity='per_visit')
            with open(subject_ids_path) as f:
                ids = f.read().split('\n')
            self.assertEqual(sorted(ids), sorted(self.SUBJECT_IDS))

    def test_visit_ids_access(self):
        self.study.visit_ids_access_pipeline().run(work_dir=self.work_dir)
        for subject_id in self.SUBJECT_IDS:
            visit_ids_path = self.output_file_path(
                'visit_ids.txt', self.study.name,
                subject=subject_id, multiplicity='per_subject')
            with open(visit_ids_path) as f:
                ids = f.read().split('\n')
            self.assertEqual(sorted(ids), sorted(self.SESSION_IDS))


class ExistingPrereqStudy(Study):

    def pipeline_factory(self, incr, input, output):  # @ReservedAssignment
        pipeline = self.create_pipeline(
            name=output,
            inputs=[DatasetSpec(input, mrtrix_format)],
            outputs=[DatasetSpec(output, mrtrix_format)],
            description=(
                "A dummy pipeline used to test 'partial-complete' method"),
            default_options={'pipeline1_option': False},
            version=1,
            citations=[],
            options={})
        # Nodes
        operands = pipeline.create_node(Merge(2), name='merge')
        mult = pipeline.create_node(MRCalc(), name="convert1",
                                    requirements=[mrtrix3_req])
        operands.inputs.in2 = incr
        mult.inputs.operation = 'add'
        # Connect inputs
        pipeline.connect_input(input, operands, 'in1')
        # Connect inter-nodes
        pipeline.connect(operands, 'out', mult, 'operands')
        # Connect outputs
        pipeline.connect_output(output, mult, 'out_file')
        # Check inputs/outputs are connected
        pipeline.assert_connected()
        return pipeline

    def tens_pipeline(self):
        return self.pipeline_factory(10, 'ones', 'tens')

    def hundreds_pipeline(self):
        return self.pipeline_factory(100, 'tens', 'hundreds')

    def thousands_pipeline(self):
        return self.pipeline_factory(1000, 'hundreds', 'thousands')

    _dataset_specs = set_dataset_specs(
        DatasetSpec('ones', mrtrix_format),
        DatasetSpec('tens', mrtrix_format, tens_pipeline),
        DatasetSpec('hundreds', mrtrix_format, hundreds_pipeline),
        DatasetSpec('thousands', mrtrix_format, thousands_pipeline))


class TestExistingPrereqs(BaseMultiSubjectTestCase):
    """
    This unittest tests out that partially previously calculated prereqs
    are detected and not rerun unless reprocess==True.

    The structure of the "subjects" and "sessions" stored on the XNAT archive
    is:


    -- subject1 -- visit1 -- ones
     |           |         |
     |           |         - tens
     |           |         |
     |           |         - hundreds
     |           |
     |           - visit2 -- ones
     |           |         |
     |           |         - tens
     |           |
     |           - visit3 -- ones
     |                     |
     |                     - hundreds
     |                     |
     |                     - thousands
     |
     - subject2 -- visit1 -- ones
     |           |         |
     |           |         - tens
     |           |
     |           - visit2 -- ones
     |           |         |
     |           |         - tens
     |           |
     |           - visit3 -- ones
     |                     |
     |                     - tens
     |                     |
     |                     - hundreds
     |                     |
     |                     - thousands
     |
     - subject3 -- visit1 -- ones
     |           |
     |           - visit2 -- ones
     |           |         |
     |           |         - tens
     |           |
     |           - visit3 -- ones
     |                     |
     |                     - tens
     |                     |
     |                     - thousands
     |
     - subject4 -- visit1 -- ones
                 |
                 - visit2 -- ones
                 |         |
                 |         - tens
                 |
                 - visit3 -- ones
                           |
                           - tens
                           |
                           - hundreds
                           |
                           - thousands

    For prexisting sessions the values in the existing images are multiplied by
    5, i.e. preexisting tens actually contains voxels of value 50, hundreds 500
    """

    saved_structure = {
        'subject1': {
            'visit1': ['ones', 'tens', 'hundreds'],
            'visit2': ['ones', 'tens'],
            'visit3': ['ones', 'hundreds', 'thousands']},
        'subject2': {
            'visit1': ['ones', 'tens'],
            'visit2': ['ones', 'tens'],
            'visit3': ['ones', 'tens', 'hundreds', 'thousands']},
        'subject3': {
            'visit1': ['ones'],
            'visit2': ['ones', 'tens'],
            'visit3': ['ones', 'tens', 'thousands']},
        'subject4': {
            'visit1': ['ones'],
            'visit2': ['ones', 'tens'],
            'visit3': ['ones', 'tens', 'hundreds', 'thousands']}}

    study_name = 'existing'

    def test_per_session_prereqs(self):
        study = self.create_study(
            ExistingPrereqStudy, self.study_name, input_datasets={
                'ones': Dataset('ones', mrtrix_format)})
        study.thousands_pipeline().run(work_dir=self.work_dir)
        targets = {
            'subject1': {
                'visit1': 1100,
                'visit2': 1110,
                'visit3': 1000},
            'subject2': {
                'visit1': 1110,
                'visit2': 1110,
                'visit3': 1000},
            'subject3': {
                'visit1': 1111,
                'visit2': 1110,
                'visit3': 1000},
            'subject4': {
                'visit1': 1111,
                'visit2': 1110,
                'visit3': 1000}}
        for subj_id, visits in self.saved_structure.iteritems():
            for visit_id in visits:
                self.assertStatEqual('mean', 'thousands.mif',
                                     targets[subj_id][visit_id],
                                     self.study_name,
                                     subject=subj_id, session=visit_id,
                                     multiplicity='per_session')
