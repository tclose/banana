"""
banana

Copyright (c) 2012-2018 Thomas G. Close, Monash Biomedical Imaging,
Monash University, Melbourne, Australia

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from .__about__ import __version__, __authors__
import os

# Should be set explicitly in all FSL interfaces, but this squashes the warning
os.environ['FSLOUTPUTTYPE'] = 'NIFTI_GZ'

# Import all objects from Arcana used to design and apply Banana studies
from arcana import (  # @IgnorePep8
    SubStudySpec, Parameter, ParamSpec, SwitchSpec, FileFormat, Fileset,
    FilesetSpec, InputFileset, InputFilesetSpec, FilesetCollection, Field,
    FieldSpec, InputField, InputFieldSpec, FieldCollection, SingleProc,
    MultiProc, SlurmProc, StaticEnv,
    ModulesEnv, BasicRepo, XnatRepo)

from .bids import BidsRepo  # @IgnorePep8


# Import all Study classes into package root
from .study.base import (  # @IgnorePep8
    Study, StudyMetaClass, MultiStudy, MultiStudyMetaClass)
