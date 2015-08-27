# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# mdsynthesis

"""
MDSynthesis --- a persistence engine for molecular dynamics data
================================================================

MDSynthesis is designed to address the logistical aspects of molecular dynamics
trajectory analysis. Whereas MDAnalysis gives the computational tools to
dissect trajectories, MDSynthesis provides a framework for automatically
organizing the results. This allows you (the scientist) to focus on your
science, letting the computer handle the lower-level logistical details.

.. SeeAlso:: :class:`mdsynthesis.treants.Sim`
             :class:`mdsynthesis.treants.Group`


"""
# Bring some often used objects into the current namespace
from mdsynthesis.treants import Sim
from datreant import Group
from datreant.collections import Bundle
from datreant.manipulators import *
import datreant
import mdsynthesis.persistence

__all__ = ['Sim', 'Group', 'Coordinator', 'Bundle']
__version__ = "0.5.1"  # NOTE: keep in sync with RELEASE in setup.py

datreant._treants['Sim'] = Sim
datreant._treantfiles['Sim'] = mdsynthesis.persistence.SimFile
