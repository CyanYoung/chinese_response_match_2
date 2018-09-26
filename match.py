import pickle as pk

import re

import numpy as np

from keras.models import Model
from keras.layers import Input

from keras.preprocessing.sequence import pad_sequences

from nn_arch import merge

from encode import load_model

from util import load_word_re, load_type_re, load_word_pair, word_replace, flat_read, map_item


def define_merge(name):
    encode_len = map_item(name, encode_lens)
    input1 = Input(shape=(encode_len,))
    input2 = Input(shape=(encode_len,))
    output = merge(input1, input2)
    model = Model([input1, input2], output)
    return model


def load_merge(name):
    model = define_merge(name)
    model.load_weights(map_item(name, paths), by_name=True)
    return model


def load_cache(path_cache):
    with open(path_cache, 'rb') as f:
        cache = pk.load(f)
    return cache


seq_len = 30

path_stop_word = 'dict/stop_word.txt'
path_type_dir = 'dict/word_type'
path_homo = 'dict/homonym.csv'
path_syno = 'dict/synonym.csv'
stop_word_re = load_word_re(path_stop_word)
word_type_re = load_type_re(path_type_dir)
homo_dict = load_word_pair(path_homo)
syno_dict = load_word_pair(path_syno)

path_train = 'data/train.csv'
path_sent = 'feat/sent_train.pkl'
path_label = 'feat/label_train.pkl'
path_embed = 'feat/embed.pkl'
path_word2ind = 'model/word2ind.pkl'
texts = flat_read(path_train, 'text')
with open(path_sent, 'rb') as f:
    sents = pk.load(f)
with open(path_label, 'rb') as f:
    labels = pk.load(f)
with open(path_embed, 'rb') as f:
    embed_mat = pk.load(f)
with open(path_word2ind, 'rb') as f:
    word2ind = pk.load(f)

paths = {'dnn': 'model/dnn.h5',
         'cnn': 'model/cnn.h5',
         'rnn': 'model/rnn.h5',
         'dnn_cache': 'cache/dnn.pkl',
         'cnn_cache': 'cache/cnn.pkl',
         'rnn_cache': 'cache/rnn.pkl'}

encode_lens = {'dnn': 200,
               'cnn': 192,
               'rnn': 200}

caches = {'dnn': load_cache(map_item('dnn_cache', paths)),
          'cnn': load_cache(map_item('cnn_cache', paths)),
          'rnn': load_cache(map_item('rnn_cache', paths))}

models = {'dnn': load_model('dnn', embed_mat, seq_len),
          'cnn': load_model('cnn', embed_mat, seq_len),
          'rnn': load_model('rnn', embed_mat, seq_len),
          'dnn_merge': load_merge('dnn'),
          'cnn_merge': load_merge('cnn'),
          'rnn_merge': load_merge('rnn')}


def predict(text, name):
    text = re.sub(stop_word_re, '', text.strip())
    for word_type, word_re in word_type_re.items():
        text = re.sub(word_re, word_type, text)
    text = word_replace(text, homo_dict)
    text = word_replace(text, syno_dict)
    cache_sents = map_item(name, caches)
    seq = word2ind.texts_to_sequences([text])[0]
    pad_seq = pad_sequences([seq], maxlen=seq_len)
    model = map_item(name, models)
    encode_seq = model.predict([pad_seq])
    encode_mat = np.repeat(encode_seq, len(cache_sents), axis=0)
    model = map_item(name + '_merge', models)
    probs = model.predict([encode_mat, cache_sents])
    probs = np.reshape(probs, (1, -1))[0]
    max_probs = sorted(probs, reverse=True)[:3]
    max_inds = np.argsort(-probs)[:3]
    max_preds = [labels[ind] for ind in max_inds]
    max_texts = [texts[ind] for ind in max_inds]
    formats = list()
    for pred, prob, text in zip(max_preds, max_probs, max_texts):
        formats.append('{} {:.3f} {}'.format(pred, prob, text))
    return ', '.join(formats)


if __name__ == '__main__':
    while True:
        text = input('text: ')
        print('dnn: %s' % predict(text, 'dnn'))
        print('cnn: %s' % predict(text, 'cnn'))
        print('rnn: %s' % predict(text, 'rnn'))
