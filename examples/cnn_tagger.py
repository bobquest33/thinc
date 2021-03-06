from thinc.neural.id2vec import Embed
from thinc.neural.vec2vec import Model, ReLu, Softmax
from thinc.neural.vecs2vecs import ExtractWindow
from thinc.neural._classes.batchnorm import BatchNormalization, ScaleShift

from thinc.neural.util import score_model
from thinc.neural.optimizers import linear_decay
from thinc.neural.ops import NumpyOps
from thinc.loss import categorical_crossentropy

from thinc.api import layerize

from thinc.extra.datasets import ancora_pos_tags

import plac

try:
    import cytoolz as toolz
except ImportError:
    import toolz


@toolz.curry
def flatten(ops, X, dropout=0.0):
    def finish_update(grad, *args, **kwargs):
        return grad
    return ops.flatten(X), finish_update

_i = 0
@toolz.curry
def health_check(name, X, **kwargs):
    global _i
    if _i and _i % 500 == 0:
        print(X.mean(axis=0).mean(), X.var(axis=0).mean())
    _i += 1
    return X, lambda grad, *args, **kwargs: grad


class Tagger(Model):
    def __init__(self, nr_tag, width, vector_length, vectors=None):
        vectors = {} if vectors is None else vectors
        self.width = width
        self.vector_length = vector_length
        layers = [
            layerize(flatten(NumpyOps())),
            Embed(vector_length, vector_length, vectors=vectors, ops=NumpyOps(),
                name='embed'),
            BatchNormalization(),
            ExtractWindow(n=2),
            ReLu(width, width*5, ops=NumpyOps(), name='relu1'),
            ExtractWindow(n=3),
            BatchNormalization(),
            ScaleShift(width * 7, name='scaleshift1'),
            ReLu(width*3, width*7, ops=NumpyOps(), name='relu2'),
            BatchNormalization(),
            ScaleShift(width * 3, name='scaleshift2'),
            ReLu(width*2, width*3, ops=NumpyOps(), name='relu3'),
            BatchNormalization(),
            ScaleShift(width * 2, name='scaleshift3'),
            ReLu(width, width*2, ops=NumpyOps(), name='relu4'),
            BatchNormalization(),
            ScaleShift(width, name='scaleshift4'),
            Softmax(nr_tag, width, ops=NumpyOps(), name='softmax')
        ]
        Model.__init__(self, *layers, ops=NumpyOps())


def main():
    train_data, check_data, nr_class = ancora_pos_tags()
    model = Tagger(nr_class, 32, 32, vectors={})

    dev_X, dev_Y = zip(*check_data)
    dev_Y = model.ops.flatten(dev_Y)
    with model.begin_training(train_data) as (trainer, optimizer):
        trainer.batch_size = 8
        trainer.nb_epoch = 10
        trainer.dropout = 0.25
        trainer.dropout_decay = 0.
        for examples, truth in trainer.iterate(model, train_data, dev_X, dev_Y,
                                               nb_epoch=trainer.nb_epoch):
            truth = model.ops.flatten(truth)
            guess, finish_update = model.begin_update(examples,
                                        dropout=trainer.dropout)

            gradient, loss = categorical_crossentropy(guess, truth)
            optimizer.set_loss(loss)
            finish_update(gradient, optimizer)
            trainer._loss += loss / len(truth)
    with model.use_params(optimizer.averages):
        print('Avg dev.: %.3f' % score_model(model, dev_X, dev_Y))
 

if __name__ == '__main__':
    if 1:
        plac.call(main)
    else:
        import cProfile
        import pstats
        cProfile.run("plac.call(main)", "Profile.prof")
        s = pstats.Stats("Profile.prof")
        s.strip_dirs().sort_stats("time", "cumulative").print_stats(100)
        s.strip_dirs().sort_stats('ncalls').print_callers()
