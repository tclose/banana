import os.path as op
import os.path
from nipype.interfaces.base import (
    TraitedSpec, BaseInterface, File, Directory, traits, isdefined,
    CommandLineInputSpec, CommandLine)
import pydicom
import nibabel as nib
from arcana.utils import split_extension
import re
from arcana.exceptions import ArcanaError
import numpy as np
from nipype.utils.filemanip import split_filename
from .matlab import BaseMatlab, BaseMatlabInputSpec


class Dcm2niixInputSpec(CommandLineInputSpec):
    input_dir = Directory(mandatory=True, desc='directory name', argstr='"%s"',
                          position=-1)
    compression = traits.Str(argstr='-z %s', desc='type of compression')
    filename = File(genfile=True, argstr='-f %s', desc='output file name')
    out_dir = Directory(genfile=True, argstr='-o %s', desc="output directory")
    multifile_concat = traits.Bool(default=False, desc="concatenate multiple "
                                   "echoes into one file")


class Dcm2niixOutputSpec(TraitedSpec):
    converted = File(exists=True, desc="The converted file")


class Dcm2niix(CommandLine):
    """Convert a DICOM folder to a nifti_gz file"""

    _cmd = 'dcm2niix'
    input_spec = Dcm2niixInputSpec
    output_spec = Dcm2niixOutputSpec

    def _list_outputs(self):
        if (not isdefined(self.inputs.compression)
                or (self.inputs.compression == 'y'
                    or self.inputs.compression == 'i')):
            im_ext = '.nii.gz'
        else:
            im_ext = '.nii'
        outputs = self._outputs().get()
        # As Dcm2niix sometimes prepends a prefix onto the filenames to avoid
        # name clashes with multiple echos, we need to check the output folder
        # for all filenames that end with the "generated filename".
        out_dir = self._gen_filename('out_dir')
        fname = self._gen_filename('filename') + im_ext
        base, ext = split_extension(fname)
        match_re = re.compile(r'(_e\d+)?{}(_(?:e|c)\d+)?{}'
                              .format(base, ext if ext is not None else ''))
        products = [os.path.join(out_dir, f) for f in os.listdir(out_dir)
                    if match_re.match(f) is not None]
        if len(products) == 1:
            converted = products[0]
        elif len(products) > 1 and self.inputs.multifile_concat:
            ex_file = nib.load(products[0])
            data = ex_file.get_data()
            merged_file = np.zeros((data.shape[0], data.shape[1],
                                    data.shape[2], len(products)))
            for i, el in enumerate(products):
                f = nib.load(el)
                merged_file[:, :, :, i] = f.get_data()
            im2save = nib.Nifti1Image(merged_file, ex_file.affine)
            nib.save(im2save, out_dir + fname)
            converted = out_dir + fname
        elif len(products) > 1 and not self.inputs.multifile_concat:
            converted = products[-1]
        else:
            raise ArcanaError("No products produced by dcm2niix ({})"
                              .format(', '.join(os.listdir(out_dir))))
        outputs['converted'] = converted
        return outputs

    def _gen_filename(self, name):
        if name == 'out_dir':
            fname = self._gen_outdirname()
        elif name == 'filename':
            fname = self._gen_outfilename()
        else:
            assert False
        return fname

    def _gen_outdirname(self):
        if isdefined(self.inputs.out_dir):
            out_name = self.inputs.out_dir
        else:
            out_name = os.path.join(os.getcwd())
        return out_name

    def _gen_outfilename(self):
        if isdefined(self.inputs.filename):
            out_name = self.inputs.filename
        else:
            out_name = os.path.basename(self.inputs.input_dir)
        return out_name


class Nii2DicomInputSpec(TraitedSpec):
    in_file = File(mandatory=True, desc='input nifti file')
    reference_dicom = traits.List(mandatory=True, desc='original umap')
#     out_file = Directory(genfile=True, desc='the output dicom file')


class Nii2DicomOutputSpec(TraitedSpec):
    out_file = Directory(exists=True, desc='the output dicom file')


class Nii2Dicom(BaseInterface):
    """
    Creates two umaps in dicom format

    fully compatible with the UTE study:

    Attenuation Correction pipeline

    """

    input_spec = Nii2DicomInputSpec
    output_spec = Nii2DicomOutputSpec

    def _run_interface(self, runtime):
        dcms = self.inputs.reference_dicom
        to_remove = [x for x in dcms if '.dcm' not in x]
        if to_remove:
            for f in to_remove:
                dcms.remove(f)
#         dcms = glob.glob(self.inputs.reference_dicom+'/*.dcm')
#         if not dcms:
#             dcms = glob.glob(self.inputs.reference_dicom+'/*.IMA')
#         if not dcms:
#             raise Exception('No DICOM files found in {}'
#                             .format(self.inputs.reference_dicom))
        nifti_image = nib.load(self.inputs.in_file)
        nii_data = nifti_image.get_data()
        if len(dcms) != nii_data.shape[2]:
            raise Exception('Different number of nifti and dicom files '
                            'provided. Dicom to nifti conversion require the '
                            'same number of files in order to run. Please '
                            'check.')
        os.mkdir('nifti2dicom')
        _, basename, _ = split_filename(self.inputs.in_file)
        for i in range(nii_data.shape[2]):
            dcm = pydicom.read_file(dcms[i])
            nifti = nii_data[:, :, i]
            nifti = nifti.astype('uint16')
            dcm.pixel_array.setflags(write=True)
            dcm.pixel_array.flat[:] = nifti.flat[:]
            dcm.PixelData = dcm.pixel_array.T.tostring()
            dcm.save_as('nifti2dicom/{0}_vol{1}.dcm'
                        .format(basename, str(i).zfill(4)))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_file'] = (
            os.getcwd() + '/nifti2dicom')
        return outputs

    def _gen_filename(self, name):
        if name == 'out_file':
            fname = self._gen_outfilename()
        else:
            assert False
        return fname

    def _gen_outfilename(self):
        if isdefined(self.inputs.out_file):
            fpath = self.inputs.out_file
        else:
            fname = (
                split_extension(os.path.basename(self.inputs.in_file))[0]
                + '_dicom')
            fpath = os.path.join(os.getcwd(), fname)
        return fpath


class TwixReaderInputSpec(BaseMatlabInputSpec):
    in_file = File(exists=True, mandatory=True)


class TwixReader(BaseMatlab):
    """
    Reads a Siemens TWIX (multi-channel k-space) file and saves it in a Matlab
    file in 'matlab_kspace' format (see banana.file_format for details)
    """

    input_spec = TwixReaderInputSpec

    def script(self, **inputs):
        """
        Generate script to load Siemens format k-space and save as Matlab
        arrays
        """
        script = """
            % Read Twix file
            data_obj = mapVBVD({in_file},'removeOS');
            % Pick largest data object in file
            if length(data_obj)>1
                multi_obj = data_obj;
                acq_length = cellfun(@(x) x.image.NAcq, multi_obj);
                [~,ind] = max(acq_length);
                data_obj = data_obj{{ind}};
            end
            header = data_obj.hdr

            % Get data arrays
            calib_scan = permute(data_obj.refscan{{''}}, [2, 1, 3, 4, 5]);
            data_scan = permute(data_obj.image{{''}}, [2, 1, 3, 4, 5]);

            % Get full dimensions from header
            num_freq = data_obj.hdr.Config.NImageCols;
            num_phase = data_obj.hdr.Config.NPeFTLen;
            num_partitions = data_obj.hdr.Config.NImagePar;
            dims = [num_freq, num_phase, num_partitions]

            % Get channel and echo information from header
            if isfield(header.Config,'RawCha') &&...
               ~isempty(header.Config.RawCha)
                num_channels = header.Config.RawCha;
            else
                num_channels = size(data_scan, 1);
            end
            if isfield(header.Meas,'RawEcho')
                num_echos = header.Meas.RawEcho;
            elseif isfield(header.MeasYaps,'lContrasts')
                num_echos = header.MeasYaps.lContrasts;
            else
                num_echos = size(data_scan, 5);
            end

            % Get Voxel size
            voxel_size = [0, 0, 0];
            slice_array = header.Phoenix.sSliceArray.asSlice{{1}}
            voxel_size(1) = slice_array.dReadoutFOV / num_freq;
            voxel_size(2) = slice_array.dPhaseFOV / num_phase;
            voxel_size(3) = slice_array.dThickness / num_partitions;

            % Get other parameters
            if isfield(header.Meas,'alTE')
                TE = header.Meas.alTE(1:num_echos) * 1E-6;
            elseif isfield(header.MeasYaps,'alTE')
                TE = [header.MeasYaps.alTE{{1:num_echos}}] * 1E-6;
            else
                disp('No header field for echo times');
                TE = NaN
            end
            B0_strength = header.Dicom.flMagneticFieldStrength;
            B0_dir = [0 0 1];
            larmor_freq = header.Dicom.lFrequency; % (Hz)

            save({out_file}, calib_scan, data_scan, dims, voxel_size,...
                 num_channels, num_echos, TE, B0_strength, B0_dir,...
                 larmor_freq);
            """.format(in_file=self.inputs.in_file,
                       out_file=self.inputs.out_file)
        return script
