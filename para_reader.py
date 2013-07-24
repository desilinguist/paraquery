# This module contains the ParaReader class which reads the paraphrase grammar file
# and returns the following fields for use in the parpahrase query shell. This file
# should be modified for any different paraphrase grammar file format. The default
# format that is the following:
#    head ||| source ||| target ||| features
#
# This class should return the following fields:
#   source (text), target (text), identity (integer), srclen (integer), tgtlen (integer), lendiff [=tgtlen-srclen] (integer), pe2e1 (float), number of pivots (integer), pivots (list)

# The class takes in a gzipped file as the only input.

import gzip


class ParaReader:
    def __init__(self, parafilename):
        self._parafh = gzip.GzipFile(parafilename)

    def __iter__(self):
        for line in self._parafh:
            head, src, tgt, features, pivots = line.split(' ||| ')
            src = src.decode('utf-8')
            tgt = tgt.decode('utf-8')
            pivots = pivots.decode('utf-8')
            src, tgt = map(unicode, [src, tgt])
            features = features.split()
            identity = int(float(features[2]))
            pe2e1 = float(features[3])
            srclen = int(float(features[7]))
            tgtlen = int(float(features[8]))
            lendiff = int(float(features[9]))
            num_pivots = len(pivots.replace('["', '').replace('"]', '').replace('\n', '').split('", "'))
            t = (src, tgt, identity, srclen, tgtlen, lendiff, pe2e1, num_pivots, pivots)
            yield t
