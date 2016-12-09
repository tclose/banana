from itertools import chain
from copy import copy
from nipype.pipeline import engine as pe
# from nipype.interfaces.freesurfer.preprocess import ReconAll
from nianalysis.interfaces.utils import DummyReconAll as ReconAll
from nianalysis.requirements import freesurfer_req
from nianalysis.citations import freesurfer_cites
from nianalysis.data_formats import freesurfer_recon_all_format
from nianalysis.study.base import set_dataset_specs
from nianalysis.dataset import DatasetSpec
from nianalysis.interfaces.utils import ZipDir, JoinPath
from ..base import MRStudy


class T1Study(MRStudy):

    def brain_mask_pipeline(self, robust=False, threshold=0.1,
                            reduce_bias=True, **kwargs):
        return super(T1Study, self).brain_mask_pipeline(
            robust=robust, threshold=threshold, reduce_bias=reduce_bias,
            **kwargs)

    def freesurfer_pipeline(self, num_processes=16, **kwargs):  # @UnusedVariable @IgnorePep8
        """
        Segments grey matter, white matter and CSF from T1 images using
        SPM "NewSegment" function.

        NB: Default values come from the W2MHS toolbox
        """
        pipeline = self._create_pipeline(
            name='segmentation',
            inputs=['acquired'],
            outputs=['fs_recon_all'],
            description="Segment white/grey matter and csf",
            options={},
            requirements=[freesurfer_req],
            citations=copy(freesurfer_cites),
            approx_runtime=500)
        # FS ReconAll node
        recon_all = pe.Node(interface=ReconAll(), name='recon_all')
        recon_all.inputs.directive = 'all'
        recon_all.inputs.openmp = num_processes
        # Wrapper around os.path.join
        join = pe.Node(interface=JoinPath(), name='join')
        pipeline.connect(recon_all, 'subjects_dir', join, 'dirname')
        pipeline.connect(recon_all, 'subject_id', join, 'filename')
        # Zip directory before returning
        zip_dir = pe.Node(interface=ZipDir(), name='zip_dir')
        zip_dir.inputs.extension = '.fs'
        pipeline.connect(join, 'path', zip_dir, 'dirname')
        # Connect inputs/outputs
        pipeline.connect_input('t1', recon_all, 'T1_files')
        pipeline.connect_output('fs_recon_all', zip_dir, 'zipped')
        pipeline.assert_connected()
        return pipeline

    _dataset_specs = set_dataset_specs(
        DatasetSpec('fs_recon_all', freesurfer_recon_all_format,
                    freesurfer_pipeline),
        inherit_from=chain(MRStudy.dataset_specs()))