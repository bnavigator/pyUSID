# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 15:07:16 2017

@author: Suhas Somnath
"""
from __future__ import division, print_function, unicode_literals, absolute_import
import unittest
import os
import sys
import h5py
import numpy as np
import dask.array as da


sys.path.append("../../pyUSID/")
from pyUSID.io import USIDataset, hdf_utils

from . import data_utils

if sys.version_info.major == 3:
    unicode = str

test_h5_file_path = data_utils.std_beps_path


class TestUSIDataset(unittest.TestCase):

    def setUp(self):
        self.rev_spec = False
        data_utils.make_beps_file(rev_spec=self.rev_spec)
        self.orig_labels_order = ['X', 'Y', 'Cycle', 'Bias'] if self.rev_spec else ['X', 'Y', 'Bias', 'Cycle']

    def tearDown(self):
        os.remove(test_h5_file_path)

    def get_expected_n_dim(self, h5_f):
        nd_slow_to_fast = h5_f['/Raw_Measurement/n_dim_form'][()]
        nd_fast_to_slow = nd_slow_to_fast.transpose(1, 0, 3, 2)
        if self.rev_spec:
            nd_fast_to_slow = nd_fast_to_slow.transpose(0, 1, 3, 2)
        return nd_slow_to_fast, nd_fast_to_slow

    def test_string_representation(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            usi_dset = USIDataset(h5_main)
            actual = usi_dset.__repr__()
            actual = [line.strip() for line in actual.split("\n")]
            actual = [actual[line_ind] for line_ind in [0, 2, 4, 7, 8, 10, 11]]

            expected = list()
            expected.append(h5_main.__repr__())
            expected.append(h5_main.name)
            expected.append(hdf_utils.get_attr(h5_main, "quantity") + " (" + hdf_utils.get_attr(h5_main, "units") + ")")
            for h5_inds in [usi_dset.h5_pos_inds, usi_dset.h5_spec_inds]:
                for dim_name, dim_size in zip(hdf_utils.get_attr(h5_inds, "labels"),
                                              hdf_utils.get_dimensionality(h5_inds)):
                    expected.append(dim_name + ' - size: ' + str(dim_size))
            self.assertTrue(np.all([x == y for x, y in zip(actual, expected)]))


class TestEquality(TestUSIDataset):

    def test_correct_USIDataset(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected = USIDataset(h5_main)
            self.assertTrue(expected == expected)

    def test_correct_h5_dataset(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected = USIDataset(h5_main)
            self.assertTrue(expected == h5_main)

    def test_incorrect_USIDataset(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected = USIDataset(h5_main)
            incorrect = USIDataset(h5_f['/Raw_Measurement/source_main-Fitter_000/results_main'])
            self.assertFalse(expected == incorrect)

    def test_incorrect_h5_dataset(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected = USIDataset(h5_main)
            incorrect = h5_f['/Raw_Measurement/source_main-Fitter_000/Spectroscopic_Indices']
            self.assertFalse(expected == incorrect)

    def test_incorrect_object(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            h5_main = h5_f['/Raw_Measurement/source_main']
            expected = USIDataset(h5_main)
            incorrect = np.zeros(shape=(1, 2, 3, 4))
            self.assertFalse(expected == incorrect)


class TestGetNDimFormExists(TestUSIDataset):

    def test_sorted_and_unsorted(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_dset = USIDataset(h5_f['/Raw_Measurement/source_main'])
            nd_slow_to_fast, nd_fast_to_slow = self.get_expected_n_dim(h5_f)
            actual_f2s = usi_dset.get_n_dim_form(lazy=False)
            self.assertTrue(np.allclose(nd_fast_to_slow, actual_f2s))

            nd_form, success = hdf_utils.reshape_to_n_dims(usi_dset, sort_dims=True)
            print(nd_form.shape)

            usi_dset.toggle_sorting()
            actual_s2f = usi_dset.get_n_dim_form(lazy=False)
            self.assertTrue(np.allclose(nd_slow_to_fast, actual_s2f))


class TestPosSpecSlices(TestUSIDataset):

    def test_empty_dict(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({})
            self.assertTrue(np.allclose(np.expand_dims(np.arange(14), axis=1), actual_spec))
            self.assertTrue(np.allclose(np.expand_dims(np.arange(15), axis=1), actual_pos))

    def test_non_existent_dim(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(KeyError):
                _ = usi_main._get_pos_spec_slices({'blah': 4, 'X': 3, 'Y': 1})

    def test_incorrect_type(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(TypeError):
                _ = usi_main._get_pos_spec_slices({'X': 'fdfd', 'Y': 1})

    def test_negative_index(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(ValueError):
                _ = usi_main._get_pos_spec_slices({'X': -4, 'Y': 1})

    def test_out_of_bounds(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(IndexError):
                _ = usi_main._get_pos_spec_slices({'X': 15, 'Y': 1})

    def test_one_pos_dim_removed(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            # orig_pos = np.vstack([np.tile(np.arange(5), 3), np.repeat(np.arange(3), 5)]).T
            # orig_spec = np.vstack([np.tile(np.arange(7), 2), np.repeat(np.arange(2), 7)])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': 3})
            # we want every fifth position starting from 3
            expected_pos = np.expand_dims(np.arange(3, 15, 5), axis=1)
            expected_spec = np.expand_dims(np.arange(14), axis=1)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))

    def test_one_pos_dim_sliced(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': slice(1, 5, 2)})
            # we want every fifth position starting from 3
            positions = []
            for row_ind in range(3):
                for col_ind in range(1, 5, 2):
                    positions.append(5 * row_ind + col_ind)
            expected_pos = np.expand_dims(positions, axis=1)
            expected_spec = np.expand_dims(np.arange(14), axis=1)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))

    def test_two_pos_dim_sliced(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': slice(1, 5, 2), 'Y': 1})
            # we want every fifth position starting from 3
            positions = []
            for row_ind in range(1, 2):
                for col_ind in range(1, 5, 2):
                    positions.append(5 * row_ind + col_ind)
            expected_pos = np.expand_dims(positions, axis=1)
            expected_spec = np.expand_dims(np.arange(14), axis=1)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))

    def test_two_pos_dim_sliced_list(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': [1, 2, 4], 'Y': 1})
            # we want every fifth position starting from 3
            positions = []
            for row_ind in range(1, 2):
                for col_ind in [1, 2, 4]:
                    positions.append(5 * row_ind + col_ind)
            expected_pos = np.expand_dims(positions, axis=1)
            expected_spec = np.expand_dims(np.arange(14), axis=1)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))

    def test_both_pos_removed(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': 3, 'Y': 1})
            # we want every fifth position starting from 3
            expected_pos = np.expand_dims([1 * 5 + 3], axis=1)
            expected_spec = np.expand_dims(np.arange(14), axis=1)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))

    def test_pos_and_spec_sliced_list(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            h5_pos_inds = usi_main.h5_pos_inds
            h5_spec_inds = usi_main.h5_spec_inds
            actual_pos, actual_spec = usi_main._get_pos_spec_slices({'X': [1, 2, 4], 'Bias': slice(1, 7, 3)})
            # we want every fifth position starting from 3
            positions = []
            for col_ind in [1, 2, 4]:
                positions += np.argwhere(h5_pos_inds[h5_pos_inds.attrs['X']] == col_ind)[:, 0].tolist()
            specs = []
            for bias_ind in range(1, 7, 3):
                specs += np.argwhere(h5_spec_inds[h5_spec_inds.attrs['Bias']] == bias_ind)[:, 1].tolist()
            expected_pos = np.expand_dims(positions, axis=1)
            expected_spec = np.expand_dims(specs, axis=1)
            expected_pos.sort(axis=0)
            expected_spec.sort(axis=0)
            self.assertTrue(np.allclose(expected_spec, actual_spec))
            self.assertTrue(np.allclose(expected_pos, actual_pos))


class TestGetUnitValues(TestUSIDataset):

    def test_get_pos_values(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            for dim_name in ['X', 'Y']:
                expected = h5_f['/Raw_Measurement/' + dim_name][()]
                actual = usi_main.get_pos_values(dim_name)
                self.assertTrue(np.allclose(expected, actual))

    def test_get_pos_values_illegal(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(KeyError):
                _ = usi_main.get_pos_values('blah')
            with self.assertRaises(TypeError):
                _ = usi_main.get_pos_values(np.array(5))

    def test_get_spec_values(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            for dim_name in ['Bias', 'Cycle']:
                expected = h5_f['/Raw_Measurement/' + dim_name][()]
                actual = usi_main.get_spec_values(dim_name)
                self.assertTrue(np.allclose(expected, actual))

    def test_get_spec_values_illegal(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(KeyError):
                _ = usi_main.get_spec_values('blah')
            with self.assertRaises(TypeError):
                _ = usi_main.get_spec_values(np.array(5))


class TestSlice(TestUSIDataset):

    def test_non_existent_dim(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(KeyError):
                _ = usi_main.slice({'blah': 4, 'X': 3, 'Y': 1})

    def test_incorrect_type(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(TypeError):
                _ = usi_main.slice({'X': 'fdfd', 'Y': 1})

    def test_out_of_bounds(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(IndexError):
                _ = usi_main.slice({'X': 15, 'Y': 1})

    def base(self, slice_dict, f2s_slice_list, result_as_nd, lazy_result,
             verbose=False):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            actual, success = usi_main.slice(slice_dict,
                                             ndim_form=result_as_nd,
                                             lazy=lazy_result)
            if verbose:
                print('Status: {}, actual.shape: {}, actual.dtype: {}, '
                      'type(actual): {}'.format(success, actual.shape,
                                                actual.dtype, type(actual)))

            self.assertTrue(success)
            n_dim_s2f, n_dim_f2s = self.get_expected_n_dim(h5_f)

            if result_as_nd:
                expected = n_dim_f2s[f2s_slice_list]
                expected = expected.squeeze()
            else:
                s2f_slice_list = f2s_slice_list[:2][::-1] + \
                                 f2s_slice_list[2:][::-1]
                if verbose:
                    print('Slice list converted from: {} to {}'
                          ''.format(f2s_slice_list, s2f_slice_list))

                expected = n_dim_s2f[s2f_slice_list]
                if verbose:
                    print('Expected in N-dim form: {}'.format(expected.shape))

                expected = expected.reshape(np.prod(expected.shape[:2]),
                                            np.prod(expected.shape[2:]))
                if verbose:
                    print('Expected after flattening of shape: {}'
                          ''.format(expected.shape))

            if lazy_result:
                self.assertIsInstance(actual, da.core.Array)
                actual = actual.compute()

            self.assertTrue(np.allclose(expected, actual))

    def test_empty_2d_numpy(self):
        self.base(None, [slice(None) for _ in range(4)], False, False)

    def test_empty_nd_numpy(self):
        self.base(None, [slice(None) for _ in range(4)], True, False)

    def test_empty_nd_dask(self):
        self.base(None, [slice(None) for _ in range(4)], True, True)

    def test_empty_2d_dask(self):
        self.base(None, [slice(None) for _ in range(4)], False, True)

    def test_negative_index_nd_numpy(self):
        self.base({'X': -2, 'Y': 1},
                  [slice(-2, -1), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, False)

    def test_negative_index_nd_dask(self):
        self.base({'X': -2, 'Y': 1},
                  [slice(-2, -1), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, True)

    def test_negative_index_2d_numpy(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            with self.assertRaises(ValueError):
                _ = usi_main.slice({'X': -2, 'Y': 1}, ndim_form=False)

    def test_one_pos_dim_removed_nd_numpy(self):
        self.base({'X': 3},
                  [3] + [slice(None) for _ in range(3)], True, False)

    def test_one_pos_dim_removed_nd_dask(self):
        self.base({'X': 3},
                  [3] + [slice(None) for _ in range(3)], True, True)

    def test_one_pos_dim_removed_2d_numpy(self):
        self.base({'X': 3},
                  [slice(3, 4)] + [slice(None) for _ in range(3)],
                  False, False)

    def test_one_pos_dim_removed_2d_dask(self):
        self.base({'X': 3},
                  [slice(3, 4)] + [slice(None) for _ in range(3)],
                  False, True)

    def test_one_pos_dim_sliced_nd_numpy(self):
        self.base({'X': slice(1, 5, 2)},
                  [slice(1, 5, 2)] + [slice(None) for _ in range(3)],
                  True, False)

    def test_one_pos_dim_sliced_nd_dask(self):
        self.base({'X': slice(1, 5, 2)},
                  [slice(1, 5, 2)] + [slice(None) for _ in range(3)],
                  True, True)

    def test_one_pos_dim_sliced_2d_numpy(self):
        self.base({'X': slice(1, 5, 2)},
                  [slice(1, 5, 2)] + [slice(None) for _ in range(3)],
                  False, False)

    def test_one_pos_dim_sliced_2d_dask(self):
        self.base({'X': slice(1, 5, 2)},
                  [slice(1, 5, 2)] + [slice(None) for _ in range(3)],
                  False, True)

    def test_two_pos_dim_sliced_nd_numpy(self):
        self.base({'X': slice(1, 5, 2), 'Y': 1},
                  [slice(1, 5, 2), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, False)

    def test_two_pos_dim_sliced_nd_dask(self):
        self.base({'X': slice(1, 5, 2), 'Y': 1},
                  [slice(1, 5, 2), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, True)

    def test_two_pos_dim_sliced_2d_numpy(self):
        self.base({'X': slice(1, 5, 2), 'Y': 1},
                  [slice(1, 5, 2), slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, False)

    def test_two_pos_dim_sliced_2d_dask(self):
        self.base({'X': slice(1, 5, 2), 'Y': 1},
                  [slice(1, 5, 2), slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, True)

    def test_two_pos_dim_sliced_list_nd_numpy(self):
        self.base({'X': [1, 2, 4], 'Y': 1},
                  [[1, 2, 4], slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, False)

    def test_two_pos_dim_sliced_list_nd_dask(self):
        self.base({'X': [1, 2, 4], 'Y': 1},
                  [[1, 2, 4], slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, True)

    def test_two_pos_dim_sliced_list_2d_numpy(self):
        self.base({'X': [1, 2, 4], 'Y': 1},
                  [[1, 2, 4], slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, False)

    def test_two_pos_dim_sliced_list_2d_dask(self):
        self.base({'X': [1, 2, 4], 'Y': 1},
                  [[1, 2, 4], slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, True)

    def test_both_pos_removed_nd_numpy(self):
        self.base({'X': 3, 'Y': 1},
                  [slice(3, 4), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, False)

    def test_both_pos_removed_nd_dask(self):
        self.base({'X': 3, 'Y': 1},
                  [slice(3, 4), slice(1, 2)] + [slice(None) for _ in range(2)],
                  True, True)

    def test_both_pos_removed_2d_numpy(self):
        self.base({'X': 3, 'Y': 1},
                  [slice(3, 4), slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, False)

    def test_both_pos_removed_2d_dask(self):
        self.base({'X': 3, 'Y': 1},
                  [slice(3, 4), slice(1, 2)] + [slice(None) for _ in range(2)],
                  False, True)

    def test_pos_and_spec_sliced_list_nd_numpy(self):
        self.base({'X': [1, 2, 4], 'Bias': slice(1, 7, 3)},
                  [[1, 2, 4], slice(None), slice(1, 7, 3), slice(None)],
                  True, False)

    def test_pos_and_spec_sliced_list_nd_dask(self):
        self.base({'X': [1, 2, 4], 'Bias': slice(1, 7, 3)},
                  [[1, 2, 4], slice(None), slice(1, 7, 3), slice(None)],
                  True, True)

    def test_pos_and_spec_sliced_list_2d_numpy(self):
        self.base({'X': [1, 2, 4], 'Bias': slice(1, 7, 3)},
                  [[1, 2, 4], slice(None), slice(1, 7, 3), slice(None)],
                  False, False)

    def test_pos_and_spec_sliced_list_2d_dask(self):
        self.base({'X': [1, 2, 4], 'Bias': slice(1, 7, 3)},
                  [[1, 2, 4], slice(None), slice(1, 7, 3), slice(None)],
                  False, True)

    def test_all_dims_sliced_nd_numpy(self):
        self.base({'X': [1, 2, 4], 'Y': 2, 'Bias': slice(1, 7, 3), 'Cycle': 1},
                  [[1, 2, 4], slice(2, 3), slice(1, 7, 3), slice(1, 2)],
                  True, False)

    def test_all_dims_sliced_nd_dask(self):
        self.base({'X': [1, 2, 4], 'Y': 2, 'Bias': slice(1, 7, 3), 'Cycle': 1},
                  [[1, 2, 4], slice(2, 3), slice(1, 7, 3), slice(1, 2)],
                  True, True)

    def test_all_dims_sliced_2d_numpy(self):
        self.base({'X': [1, 2, 4], 'Y': 2, 'Bias': slice(1, 7, 3), 'Cycle': 1},
                  [[1, 2, 4], slice(2, 3), slice(1, 7, 3), slice(1, 2)],
                  False, False)

    def test_all_dims_sliced_2d_dask(self):
        self.base({'X': [1, 2, 4], 'Y': 2, 'Bias': slice(1, 7, 3), 'Cycle': 1},
                  [[1, 2, 4], slice(2, 3), slice(1, 7, 3), slice(1, 2)],
                  False, True)


class TestSorting(TestUSIDataset):

    def test_toggle_sorting(self):
        # Need to change data file so that sorting actually does something
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])

            self.assertEqual(usi_main.n_dim_labels, self.orig_labels_order)

            usi_main.toggle_sorting()

            self.assertEqual(usi_main.n_dim_labels, ['Y', 'X', 'Cycle', 'Bias'])

            usi_main.toggle_sorting()

            self.assertEqual(usi_main.n_dim_labels, self.orig_labels_order)

    def test_get_current_sorting(self):
        with h5py.File(test_h5_file_path, mode='r') as h5_f:
            usi_main = USIDataset(h5_f['/Raw_Measurement/source_main'])
            unsorted_str = 'Data dimensions are in the order they occur in the file.\n'
            sorted_str = 'Data dimensions are sorted in order from fastest changing dimension to slowest.\n'
            # Initial state should be unsorted
            self.assertFalse(usi_main._USIDataset__sort_dims)
            with data_utils.capture_stdout() as get_value:
                usi_main.get_current_sorting()
                test_str = get_value()
            self.assertTrue(test_str == unsorted_str)
            # Toggle sorting.  Sorting should now be true.
            usi_main.toggle_sorting()
            self.assertTrue(usi_main._USIDataset__sort_dims)
            with data_utils.capture_stdout() as get_value:
                usi_main.get_current_sorting()
                test_str = get_value()
            self.assertTrue(test_str == sorted_str)


if __name__ == '__main__':
    unittest.main()
