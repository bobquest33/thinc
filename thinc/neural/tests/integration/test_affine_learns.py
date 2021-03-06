from __future__ import division, print_function

import pytest
import pickle
import io
import numpy as np
import random
from numpy.testing import assert_allclose

from ...vec2vec import Model
from ...optimizers import SGD
from ...ops import NumpyOps
from ... import vec2vec

np.random.seed(2)
random.seed(0)


@pytest.fixture
def model():
    model = vec2vec.Affine(2, 2, ops=NumpyOps())
    model.initialize_params(add_gradient=True)
    return model


def test_init(model):
    assert model.nr_out == 2 
    assert model.nr_in == 2
    assert model.W is not None
    assert model.b is not None


def test_predict_bias(model):
    input_ = model.ops.allocate((1, model.nr_in,))
    target_scores = model.ops.allocate((1, model.nr_out))
    scores = model(input_)
    assert_allclose(scores[0], target_scores[0])

    # Set bias for class 0
    model.b[0] = 2.
    target_scores[0, 0] = 2.
    scores = model(input_)
    assert_allclose(scores, target_scores)

    # Set bias for class 1
    model.b[1] = 5.
    target_scores[0, 1] = 5.
    scores = model(input_)
    assert_allclose(scores, target_scores)


@pytest.mark.parametrize(
    'X,expected', [
        (np.asarray([0,0]), [0., 0.]),
        (np.asarray([1,0]), [1., 0.]),
        (np.asarray([0,1]), [0., 1.]),
        (np.asarray([1,1]), [1., 1.])
    ])
def test_predict_weights(X, expected):
    W = np.asarray([1.,0.,0.,1.]).reshape((2, 2))
    bias = np.asarray([0.,0.])

    model = vec2vec.Affine(W.shape[0], W.shape[1], ops=NumpyOps())
    model.initialize_params(add_gradient=True)
    model.W[:] = W
    model.b[:] = bias

    scores = model.predict_one(X)
    assert_allclose(scores, expected)



def test_update():
    W = np.asarray([1.,0.,0.,1.]).reshape((2, 2))
    bias = np.asarray([0.,0.])

    model = vec2vec.Affine(2, 2, ops=NumpyOps())
    model.initialize_params(add_gradient=True)
    model.W[:] = W
    model.b[:] = bias
    sgd = SGD(model.ops, 1.0)
    
    ff = np.asarray([[0,0]])
    tf = np.asarray([[1,0]])
    ft = np.asarray([[0,1]])
    tt = np.asarray([[1,1]])

    # ff, i.e. 0, 0
    scores, finish_update = model.begin_update(ff)
    assert_allclose(scores[0,0], scores[0,1])
    # Tell it the answer was 'f'
    gradient = np.asarray([[-1., 0.]])
    finish_update(gradient, sgd)

    assert model.b[0] == 1.
    assert model.b[1] == 0.
    # Unchanged -- input was zeros, so can't get gradient for weights.
    assert model.W[0, 0] == 1.
    assert model.W[0, 1] == 0.
    assert model.W[1, 0] == 0.
    assert model.W[1, 1] == 1.

    # tf, i.e. 1, 0
    scores, finish_update = model.begin_update(tf)
    # Tell it the answer was 'T'
    gradient = np.asarray([[0., -1.]])
    finish_update(gradient, sgd)

    assert model.b[0] == 1.
    assert model.b[1] == 1.
    # Gradient for weights should have been outer(gradient, input)
    # so outer([0, -1.], [1., 0.])
    # =  [[0., 0.], [-1., 0.]]
    assert model.W[0, 0] == 1. - 0.
    assert model.W[0, 1] == 0. - 0.
    assert model.W[1, 0] == 0. - -1.
    assert model.W[1, 1] == 1. - 0.
