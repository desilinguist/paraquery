# Useful WordNet-related functions for paraquery
# Author: Lili Kotlerman, lili.dav@gmail.com, June 2012

from nltk.corpus import wordnet as wn

# define a hash that maps relation names to IDs and another one that maps IDs to names
_relation_names = ['not in WN', 'derivation', 'synonym', 'antonym', 'hypernym', 'hyponym', 'co-hyponym', 'undefined relation', 'pertainym', 'holonym', 'meronym']
_relation_ids_to_names = dict(enumerate(_relation_names))
_relation_names_to_ids = dict([(name, idx) for (idx, name) in enumerate(_relation_names)])


def internal_form(word):
    return word.replace(' ', '_').lower()

def external_form(word):
    return word.replace('_', ' ').lower()

def get_path_length(synsetA, synsetB):
    ## taken from http://blog.typeslashcode.com/voxpop/2009/10/returning-wordnet-shortest-path-distance-with-nltk/
    if synsetA == synsetB:
        return 0

    path_distance = -1

    dist_list1 = synsetA.hypernym_distances(0)
    dist_dict1 = {}

    dist_list2 = synsetB.hypernym_distances(0)
    dist_dict2 = {}

    # Transform each distance list into a dictionary. In cases where
    # there are duplicate nodes in the list (due to there being multiple
    # paths to the root) the duplicate with the shortest distance from
    # the original node is entered.

    for (l, d) in [(dist_list1, dist_dict1), (dist_list2, dist_dict2)]:
        for (key, value) in l:
            if key in d:
                if value < d[key]:
                    d[key] = value
                else:
                    d[key] = value

    # For each ancestor synset common to both subject synsets, find the
    # connecting path length. Return the shortest of these.

    for synset1 in dist_dict1.keys():
        for synset2 in dist_dict2.keys():
            if synset1 == synset2:
                new_distance = dist_dict1[synset1] + dist_dict2[synset2]
                if path_distance < 0 or new_distance < path_distance:
                    path_distance = new_distance

    return path_distance


def get_shortest_path(word_a, word_b):
    path_distance = -1
    word_a = internal_form(word_a)
    word_b = internal_form(word_b)
    if (is_pair_included(word_a, word_b)):
        for x in wn.synsets(word_a):
            for y in wn.synsets(word_b):
                dist = get_path_length(x, y)
                if (dist > 0):
                    if (path_distance < 0 or dist < path_distance):
                        path_distance = dist
    return path_distance

def get_phrase_lemma(words):
    a_lemma = ""
    for word in words:
        lemmas = get_lemmas(word)
        if (len(lemmas) > 0):
            #take the 1st lemma from the list
            a_lemma += lemmas[0] + ' '
        else:
            #use the word as is, just convert to the external_form
            a_lemma += external_form(word) + ' '
    return a_lemma.strip()


def get_lemmas(word):
    word = internal_form(word)
    lemmas = []
    if (is_word_included(word)):
        for x in wn.synsets(word):
            lemmatized_word = lemmatize(word, x.pos)
            if (lemmatized_word not in lemmas):
                lemmas.append(lemmatized_word)
    else:
        # if word is not in WN
        words = word.split('_')
        if (len(words) > 1):
            lemmas.append(get_phrase_lemma(words))
        else:
            lemmas.append(word)
    return lemmas


def lemmatize(word, pos):
    word = internal_form(word)
    if (pos == 's'):
        #change ADJ_SAT to ADJ for wn.morphy()
        pos = 'a'
    lemma = wn.morphy(word, pos)
    if not lemma:
        lemma = word
    return external_form(lemma)


def is_word_included(word):
    word = internal_form(word)
    return len(wn.synsets(word)) > 0


def is_pair_included(word_a, word_b):
    return (is_word_included(word_a) and is_word_included(word_b))


def is_same_pos(word_a, word_b):
    # if the 2 words have a common possible pos - then true
    if not is_pair_included(word_a, word_b):
        return -1
    return int(len(get_common_pos(word_a, word_b)) > 0)


def get_common_pos(word_a, word_b):
    a_pos = set()
    b_pos = set()
    common_pos = set()
    for x in wn.synsets(word_a):
        a_pos.add(x.pos)
    for x in wn.synsets(word_b):
        b_pos.add(x.pos)
    common_pos = a_pos.intersection(b_pos)
    return common_pos


def get_derivations(word):
# get all the derivations of the word
    ders = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for lemma in x.lemmas:
                # check whether the current lemma is the word's lemma (discard lemmas of other words in the synset)
                if external_form(lemma.name) != lemmatize(word, x.pos):
                    continue
                for der in lemma.derivationally_related_forms():
                    ders.add(external_form(der.name))
             #  # add pertainyms of the word's lemma as it's derivations
             #  for per in lemma.pertainyms():
             #     ders.add(external_form(per.name))
    return ders


def get_pertainyms(word):
    # get all the derivations of the word
    pers = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for lemma in x.lemmas:
                # add pertainyms of the word and its synonyms
                for per in lemma.pertainyms():
                    pers.add(external_form(per.name))
    return pers


def get_synonyms(word):
    # get all the synonyms + synonyms' derivations
    syns = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for lemma in x.lemmas:
                # exclude self lemma from the list of synonyms
                if external_form(lemma.name) == lemmatize(word, x.pos):
                    continue
                syns.add(external_form(lemma.name))
                #add derivations of a synonym as synonyms
                for der in lemma.derivationally_related_forms():
                    syns.add(external_form(der.name))
                # add pertainyms of a synonym as synonyms
                # for per in lemma.pertainyms():
                #     syns.add(external_form(per.name))
    return syns


def get_hypernyms(word):
    # get all the hypernyms + their derivations
    hyps = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for hyp in x.hypernyms():
                for hlemma in hyp.lemmas:
                    hyps.add(external_form(hlemma.name))
                    #add derivations
                    for der in hlemma.derivationally_related_forms():
                        hyps.add(external_form(der.name))
                    # for per in hlemma.pertainyms():
                    #   hyps.add(per.name.replace('_',' '))
    return hyps


def get_hyponyms(word):
    # get all the hyponyms + their derivations
    hyps = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for hyp in x.hyponyms():
                for hlemma in hyp.lemmas:
                    hyps.add(external_form(hlemma.name))
                    #add derivations
                    for der in hlemma.derivationally_related_forms():
                        hyps.add(external_form(der.name))
                    # for per in hlemma.pertainyms():
                    #   hyps.add(per.name.replace('_',' '))
    return hyps


def get_holonyms(word):
    # get all the hypernyms + their derivations
    holo = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for hol in x.member_holonyms():
                for hlemma in hol.lemmas:
                    holo.add(external_form(hlemma.name))
                    # #add derivations
                    # for der in hlemma.derivationally_related_forms():
                    #   holo.add(external_form(der.name))
            for hol in x.substance_holonyms():
                for hlemma in hol.lemmas:
                    holo.add(external_form(hlemma.name))
                    # #add derivations
                    # for der in hlemma.derivationally_related_forms():
                    #    holo.add(external_form(der.name))
            for hol in x.part_holonyms():
                for hlemma in hol.lemmas:
                    holo.add(external_form(hlemma.name))
                    # #add derivations
                    # for der in hlemma.derivationally_related_forms():
                    #   holo.add(external_form(der.name))
    return holo


def get_meronyms(word):
    # get all the hypernyms + their derivations
    mers = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for mer in x.member_meronyms():
                for mlemma in mer.lemmas:
                    mers.add(external_form(mlemma.name))
                    # #add derivations
                    # for der in mlemma.derivationally_related_forms():
                    #   mers.add(external_form(der.name))
            for mer in x.substance_meronyms():
                for mlemma in mer.lemmas:
                    mers.add(external_form(mlemma.name))
                    # #add derivations
                    # for der in mlemma.derivationally_related_forms():
                    #   mers.add(external_form(der.name))
            for mer in x.part_meronyms():
                for mlemma in mer.lemmas:
                    mers.add(external_form(mlemma.name))
                    # #add derivations
                    # for der in mlemma.derivationally_related_forms():
                    #   mers.add(external_form(der.name))
    return mers


def get_hyp(word):
    # get all the hypo/hypernyms + their derivations
    return get_hypernyms(word).union(get_hyponyms(word))


def get_antonyms(word):
    # get antonyms of (the word + all its synonyms) + derivations of each antonym
    self_derivations = get_derivations(word)
    ants = set()
    word = internal_form(word)
    if (is_word_included(word)):
        for x in wn.synsets(word):
            for l in x.lemmas:
                for ant in l.antonyms():
                    ants.add(external_form(ant.name))
                    #add derivations
                    for der in ant.derivationally_related_forms():
                        derivation = external_form(der.name)
                        # don't include derivations of the word to the list of antonyms. E.g. 'employer' and 'employee' are antonyms,
                        # but have the same derivationally related form 'employ'
                        if (derivation not in self_derivations):
                            ants.add(derivation)
                    # for per in ant.pertainyms():
                    #     ants.add(per.name.replace('_',' '))
    return ants


def is_derivation(word_a, word_b):
    word_a = internal_form(word_a)
    word_b = internal_form(word_b)
    # if the 2 words have the same lemmas - return true
    for a_syn in wn.synsets(word_a):
        for bSyn in wn.synsets(word_b):
            if (lemmatize(word_a, a_syn.pos) == lemmatize(word_b, bSyn.pos)):
                return True
    if (is_pair_included(word_a, word_b)):
        # if word_b's lemma is among word_a's derivations - return True
        aDers = get_derivations(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in aDers):
                return True
        # if word_a's lemma is among word_b's synonyms - return True
        # e.g. get_derivations('amendment') returns set(['amend']), while get_derivations('amending') returns set(['amendment', 'amendable', 'amendatory'])
        bDers = get_derivations(word_b)
        for syn in wn.synsets(word_a):
            aLemma = lemmatize(word_a, syn.pos)
            if (aLemma in bDers):
                return True
    return False


def is_synonym(word_a, word_b):
    word_a = internal_form(word_a)
    word_b = internal_form(word_b)
    if (is_pair_included(word_a, word_b)):
        # if word_b's lemma is among word_a's synonyms - return True
        a_syns = get_synonyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_syns):
                return True
        # if word_a's lemma is among word_b's synonyms - return True (e.g. 'good' is among the synonyms of 'better', but not vice versa)
        b_syns = get_synonyms(word_b)
        for syn in wn.synsets(word_a):
            aLemma = lemmatize(word_a, syn.pos)
            if (aLemma in b_syns):
                return True
    return False


def is_antonym(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's antonyms - return True
        aAnts = get_antonyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in aAnts):
                return True
        # if word_a's lemma is among word_b's antonyms - return True (doing the same as for is_synonym() and is_derivation(), although encountered no examples)
        bAnts = get_antonyms(word_b)
        for syn in wn.synsets(word_a):
            aLemma = lemmatize(word_a, syn.pos)
            if (aLemma in bAnts):
                return True
    return False


def is_pertainym(word_a, word_b):
    word_a = internal_form(word_a)
    word_b = internal_form(word_b)
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's pertainyms - return True
        a_pers = get_pertainyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_pers):
                return True
        # if word_a's lemma is among word_b's pertainyms - return True (doing the same as for is_synonym() and is_derivation(), although encountered no examples)
        bPers = get_pertainyms(word_b)
        for syn in wn.synsets(word_a):
            aLemma = lemmatize(word_a, syn.pos)
            if (aLemma in bPers):
                return True
    return False


def is_hyponym(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's hyponyms - return True
        a_hypo = get_hyponyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_hypo):
                return True
    return False


def is_hypernym(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's hypernyms - return True
        a_hyper = get_hypernyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_hyper):
                return True
    return False


def is_hyp(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's hypernyms or among word_a's hyponyms  - return True
        a_hyp = get_hypernyms(word_a).union(get_hyponyms(word_a))
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_hyp):
                return True
    return False


def is_cohyponym(word_a, word_b):
    if is_derivation(word_a, word_b):
        return False
    if is_synonym(word_a, word_b):
        return False
    common_hypernyms = set(get_hypernyms(word_a)).intersection(get_hypernyms(word_b))
    return len(common_hypernyms) > 0


def is_holonym(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's hyponyms - return True
        a_holo = get_holonyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_holo):
                return True
    return False


def is_meronym(word_a, word_b):
    if is_pair_included(word_a, word_b):
        # if word_b's lemma is among word_a's hyponyms - return True
        a_mero = get_meronyms(word_a)
        for syn in wn.synsets(word_b):
            b_lemma = lemmatize(word_b, syn.pos)
            if (b_lemma in a_mero):
                return True
    return False


def get_relation_id(rel):
    """
    0 - Pair not found in WN. Can add "relation > 0" condition to queries in order to retrieve only pairs, found in WN (i.e. both src and tgt are in WN)
    1 - Derivation
    2 - Synonym
    3 - Antonym
    4 - Hypernym (tgt is a hypernym of src)
    5 - Hyponym (tgt is a hyponym of src)
    6 - Co-hyponym (tgt and src share a common hypernym)
    8 - Pertainym
    9 - Holonym
   10 - Meronym
    7 - Undefined relation, i.e. both words are found in WN, but their relation is not among the above
    """
    return _relation_names_to_ids[rel]

def get_relation_name(rel):
    """
    0 - Pair not found in WN. Can add "relation > 0" condition to queries in order to retrieve only pairs, found in WN (i.e. both src and tgt are in WN)
    1 - Derivation
    2 - Synonym
    3 - Antonym
    4 - Hypernym (tgt is a hypernym of src)
    5 - Hyponym (tgt is a hyponym of src)
    6 - Co-hyponym (tgt and src share a common hypernym)
    8 - Pertainym
    9 - Holonym
   10 - Meronym
    7 - Undefined relation, i.e. both words are found in WN, but their relation is not among the above
    """
    return _relation_ids_to_names[rel] if rel in _relation_ids_to_names else ''

def get_wordnet_relation(word_a, word_b):
    rel = 'not in WN'
    if is_pair_included(word_a, word_b):
        if is_derivation(word_a, word_b):
            rel = 'derivation'
        elif is_synonym(word_a, word_b):
            rel = 'synonym'
        elif is_antonym(word_a, word_b):
            rel = 'antonym'
        elif is_hypernym(word_a, word_b):
            rel = 'hypernym'
        elif is_hyponym(word_a, word_b):
            rel = 'hyponym'
        elif is_pertainym(word_a, word_b):
            rel = 'pertainym'
        elif is_holonym(word_a, word_b):
            rel = 'holonym'
        elif is_meronym(word_a, word_b):
            rel = 'meronym'
        elif is_cohyponym(word_a, word_b):
            rel = 'co-hyponym'
        else:
            rel = 'undefined relation'
    return (rel, get_relation_id(rel))

