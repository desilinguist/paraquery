# Useful analysis functions for paraquery
# Author: Lili Kotlerman, lili.dav@gmail.com, June 2012

import sys
import math
import operator
import random

import nltk
import para_wn as wn
import scipy.stats as stats

#can rename, but must sort in this order
parts = ['top', 'middle', 'bottom']
not_in_wn = 'not in WN'
undefined = 'undefined relation'
whole = 'whole collection'
intervals = 20
pivots = 'pivots'
distances = 'WN distances'
per_source = 'per source side'


# TODO: hacky, may be replace with Decimal?
def feq(a, b):
    #Check whether 2 floats are equal
    return abs(a - b) < 0.00000001


def get_prob(rule):
    return math.exp(-float(rule[2]))


def rules_to_strings(rules):
    srclens = map(len, map(operator.itemgetter(0), rules))
    trglens = map(len, map(operator.itemgetter(1), rules))
    maxsrclen, maxtrglen = max(srclens), max(trglens)
    for rule in rules:
        src = rule[0]
        trg = rule[1]
        pe2e1 = get_prob(rule)
        pe2e1str = '{:>6.4}'.format(pe2e1) if pe2e1 < 0.0001 else '{:0<6.4f}'.format(pe2e1)
        yield '{} => {} [{}]'.format(src.rjust(maxsrclen), trg.ljust(maxtrglen), pe2e1str)


def get_score_distribution(rule_list):
    score_distribution = []
    for rule in rule_list:
        prob = get_prob(rule)
        score_distribution.append(prob)
    return score_distribution


def normalized_histogram_for_print(score_distribution, num_bins, denominator, limits):
    out = []
    if denominator > 0:
        h = stats.histogram(score_distribution, num_bins, limits)
        out.append('[' + str(h[1]) + ' , ' + str(h[2] * num_bins) + '], step = ' + str(round(h[2], 2)) + ' \n\t')
        for x in h[0]:
            out.append(str(round(x * 100.0/denominator, 3)) + '%\t')
        out.append('\n\t')
        for x in range(num_bins):
            out.append('(' + str(round(h[1] + h[2] + x * h[2], 3)) + ')\t')
    out.append('\n')
    return ''.join(out)


def probabilities_at_percentiles_for_print(distribution):
    out = ['\n']
    for n in range(10):
        x = (n * 10.0) + 5
        out.append('Percentile ' + str(x) + ' corresponds to prob = ' + str(round(stats.scoreatpercentile(distribution, x), 8)) + '\n')
    return ''.join(out)


def percentiles_at_probabilities_for_print(distribution):
    out = ['\n']
    for p in range(10):
        x = (p * 10.0/100.0)
        out.append('Probability ' + str(x) + ' corresponds to percentile = ' + str(round(stats.percentileofscore(distribution, x), 8)) + '\n')
    return ''.join(out)


def get_part(score, percentile_scores):
    # percentiles = [20,40,60,80]
    # top rules have scores > 80-th percentile, bottom rules have scores < 20-th percentile, middle rules are between 40 and 60 percentile.

    #'bottom'
    if score <= percentile_scores[0]:
        return parts[2]

    #'top'
    if score >= percentile_scores[3]:
        return parts[0]

    #'middle'
    if (score >= percentile_scores[1]) and (score <= percentile_scores[2]):
        return parts[1]

    return 'none'


def get_part_limits(part, percentile_scores):
    if part == parts[0]:
        #'top'
        return (percentile_scores[3], 1)

    if part == parts[1]:
        #'middle'
        return (percentile_scores[1], percentile_scores[2])

    if part == parts[2]:
        #'bottom'
        return (0, percentile_scores[0])
    return (0, 1)


def get_sorted_rule_list(rule_list):
    res = []
    score_distribution = get_score_distribution(rule_list)
    #sort the scores in desc order (we have -log values here)
    score_distribution.sort()
    while len(score_distribution) > 0:
        curr_score = score_distribution.pop()
        for rule in rule_list:
            prob = get_prob(rule)
            if feq(prob, curr_score):
                res.append(rule)
    return res


def get_rules_sample(rule_list, percentiles, max_sample_len):
    if len(rule_list) <= max_sample_len:
        return rule_list
    score_distribution = get_score_distribution(rule_list)
    percentile_scores = []
    for x in percentiles:
        percentile_scores.append(stats.scoreatpercentile(score_distribution, x))

    rules_by_part = {}
    for part in parts:
        rules_by_part[part] = []
    for rule in rule_list:
        prob = get_prob(rule)
        part = get_part(prob, percentile_scores)
        if part in rules_by_part.keys():
            rules_by_part[part].append(rule)

    #number of rules to sample from each of the parts
    part_sample_len = max_sample_len/len(parts)
    result_set = set([])
    for part in parts:
        if len(rules_by_part[part]) <= part_sample_len:
            result_set = result_set.union(rules_by_part[part])
        else:
            result_set = result_set.union(random.sample(rules_by_part[part], part_sample_len))
    res = []
    for rule in result_set:
        if rule not in res:
            res.append(rule)

    # if we could not get a sample, then just return all the rules
    if not res:
        res = rule_list
    return get_sorted_rule_list(res)


def get_distance(dist):
    if dist < 6:
        return str(dist)
    if dist < 11:
        return '6-10'
    if dist < 21:
        return '11-20'
    return '>20'


def get_percentile_scores(percentiles, score_distribution):
    percentile_scores = []
    for x in percentiles:
        percentile_scores.append(stats.scoreatpercentile(score_distribution, x))
    return percentile_scores


def scores_and_percentiles_display(score_distribution, intervals, db_size, limits):
    out = ['\n' + normalized_histogram_for_print(score_distribution, intervals, db_size, (0, 1))]
    out.append(probabilities_at_percentiles_for_print(score_distribution))
    out.append(percentiles_at_probabilities_for_print(score_distribution))
    return ''.join(out)


def analyze_rules(all_rules, percentile_scores):
    db_size = len(all_rules)
    data = {}
    data[whole] = {}
    data[whole]['sample'] = []
    data[pivots] = {}
    data[pivots][whole] = []
    data[distances] = {}
    data[distances][whole] = {}
    data[distances][whole]['values'] = []
    data[per_source] = {}
    data[per_source][whole] = {}
    data[per_source][whole]['tgtnum'] = []
    for part in parts:
        data[part] = {}
        data[pivots][part] = []
        data[distances][part] = {}
        data[distances][part]['values'] = []
        data[per_source][part] = {}
        data[per_source][part]['tgtnum'] = []

    random_sample_size = max(int(len(all_rules) * 0.03), 1)
    random_sample_size = min(random_sample_size, 25)

    data[whole]['sample'] = get_rules_sample(all_rules, [15, 40, 60, 85], random_sample_size)

    cnt = 0
    ten_percent_len = db_size/10
    w1 = ""
    stats_per_source = {}
    stats_per_source[whole] = {}
    stats_per_source[whole]['tgtnum'] = 0
    for part in parts:
        stats_per_source[part] = {}
        stats_per_source[part]['tgtnum'] = 0
    while len(all_rules) > 0:
        cnt = cnt + 1
        for percent in range(10):
            progress = percent * ten_percent_len
            if progress == cnt:
                sys.stdout.write(str(percent * 10) + "%... ")
                sys.stdout.flush()
                break
        rule = all_rules.pop(0)
        # the results must be sorted by source (rule[0]), if reached new source, save and reset statistics per source
        if w1 != rule[0]:
            # save the current stats_per_source to data
            if w1 != "":
                #parts + whole
                for x in stats_per_source.keys():
                    #relations + tgtnum
                    for y in stats_per_source[x].keys():
                        if y not in data[per_source][x].keys():
                            data[per_source][x][y] = []
                        if stats_per_source[x][y] > 0:
                            data[per_source][x][y].append(stats_per_source[x][y])
            # reset statistics per source
            w1 = rule[0]
            stats_per_source = {}
            stats_per_source[whole] = {}
            stats_per_source[whole]['tgtnum'] = 0
            for part in parts:
                stats_per_source[part] = {}
                stats_per_source[part]['tgtnum'] = 0

        w2 = rule[1]
        prob = get_prob(rule)
        part = get_part(prob, percentile_scores)
        rel = wn.get_relation_name(rule[3])
        pivotnum = int(rule[4])
        dist = get_distance(int(rule[6]))
        if rel not in data[whole].keys():
            data[whole][rel] = 0

        # count how many times each of the relations was observed in the whole collection
        data[whole][rel] = data[whole][rel] + 1
        data[pivots][whole].append(pivotnum)

        # increase the count of targets per current source by 1
        stats_per_source[whole]['tgtnum'] += 1
        if rel not in stats_per_source[whole].keys():
            stats_per_source[whole][rel] = 0
        #increse by 1 the count of current relation per source
        stats_per_source[whole][rel] += 1

        # for undefined relations, save WN distance
        if rel == undefined:
            if dist not in data[distances][whole].keys():
                data[distances][whole][dist] = []
            # save the rule with that distance
            data[distances][whole][dist].append(rule)
            #save the distance itself
            data[distances][whole]['values'].append(int(rule[6]))

        if part in data.keys():
            if rel not in data[part].keys():
                data[part][rel] = []
            data[part][rel].append(rule)
            data[pivots][part].append(pivotnum)
            if rel == undefined:
                #for undefined relations, save WN distance
                if dist not in data[distances][part].keys():
                    data[distances][part][dist] = []
                data[distances][part][dist].append(rule)
                data[distances][part]['values'].append(int(rule[6]))

            # increase the count of targets per current source by 1
            stats_per_source[part]['tgtnum'] += 1
            if rel not in stats_per_source[part].keys():
                stats_per_source[part][rel] = 0
            #increse by 1 the count of current relation per source
            stats_per_source[part][rel] += 1

    print

    # save the last stats_per_source to data
    for x in stats_per_source.keys():
        # parts + whole
        for y in stats_per_source[x].keys():
            # relations + tgtnum
            if y not in data[per_source][x].keys():
                data[per_source][x][y] = []
            if stats_per_source[x][y] > 0:
                data[per_source][x][y].append(stats_per_source[x][y])

    return data


def get_distances_for_print(part, data):
    if len(data[distances][part]['values']) == 0:
        return ""
    out = ['\n   Analysis of WordNet distances for rules corresponding to ' + undefined.upper() + ':\n']
    out.append('      Average distance: ' + str(float(sum(data[distances][part]['values']))/len(data[distances][part]['values'])) + '\n')
    for dist in data[distances][part].keys():
        if dist == 'values':
            continue
        out.append('      Examples when distance is ' + dist + ' (out of ' + str(len(data[distances][part][dist])) + ' rules):\n')
        if len(data[distances][part][dist]) < 4:
            examples = data[distances][part][dist]
        else:
            #sample 3 rules from the current distance
            examples = random.sample(data[distances][part][dist], 3)
        for rule_str in rules_to_strings(get_sorted_rule_list(examples)):
            out.append('\t\t')
            out.append(rule_str + '\n')
        out.append('\n')
    return ''.join(out)


def part_analysis_display(part, data, percentile_scores, percentiles):
    out = ['\n*********************************************************************** Analyzing the ' + part + ' part of the resource.\n']
    limits = get_part_limits(part, percentile_scores)
    out.append('   Scores between: ' + str(limits) + '\n')
    if len(data[pivots][part]) == 0:
        out.append('   Info on number of pivots is not available.\n')
    else:
        out.append('   Average number of pivots: ' + str(float(sum(data[pivots][part]))/len(data[pivots][part])) + '\n')
    part_size = 0
    for rel in data[part].keys():
        part_size += len(data[part][rel])
    out.append('  Number of rules: ' + str(part_size) + '\n')
    if part_size == 0:
        return ''.join(out)

    if not_in_wn not in data[part].keys():
        wn_part_size = part_size
    else:
        wn_part_size = part_size - len(data[part][not_in_wn])

    if wn_part_size == 0:
        out.append(source_target_numbers_display_local(data[per_source][part]['tgtnum']))
        out.append("  WordNet-based analysis is impossible, none of the rules was found in WordNet.\n")
        return ''.join(out)
    out.append('  Results of WordNet analysis based on ' + str(wn_part_size) + ' rules (' + str(round(wn_part_size * 1.0/part_size, 2)) + '% of the ' + part + ' part):\n')
    for rel in data[part].keys():
        if rel == not_in_wn:
            continue
        relSize = len(data[part][rel])
        out.append('      ' + rel.upper() + ': ' + str(relSize) + ' rule(s) (' + str(round(relSize * 100.0/wn_part_size, 2)) + '%):\n')
        out.append('      Score distribution: ')
        distribution = get_score_distribution(data[part][rel])
        out.append(normalized_histogram_for_print(distribution, 10, relSize, limits))
        out.append('      Examples:\n')
        #sample up to 12 rules from the current relation using the values in percentiles to divide the rules into parts
        for rule_str in rules_to_strings(get_rules_sample(data[part][rel], percentiles, 12)):
            out.append('\t')
            out.append(rule_str + '\n')
        out.append('\n')
    out.append(get_distances_for_print(part, data))

    source_num = len(data[per_source][part]['tgtnum'])
    out += source_target_numbers_display_local(data[per_source][part]['tgtnum'])
    # Add the avg number of each WN relation per source side
    for rel in data[per_source][part].keys():
        if rel == 'tgtnum':
            continue
        out.append(source_relation_numbers_display_local(data[per_source][part][rel], rel, source_num))
    return ''.join(out)


def whole_analysis_display(db_size, data):
    out = ['\nRandom rule sample: \n']
    out.append('-' * 20 + '\n')
    rules = data[whole]['sample']
    for rule_str in rules_to_strings(rules):
        out.append(rule_str + '\n')
    out.append('')

    out.append('\nStatistics for the ' + str(db_size) + ' rule(s): \n')
    out.append('-' * 37 + '\n')
    if len(data[pivots][whole]) == 0:
        out.append('  Info on number of pivots is not available.\n')
    else:
        out.append('  Average number of pivots: ' + str(float(sum(data[pivots][whole]))/len(data[pivots][whole])) + '\n\n')

    if not_in_wn not in data[whole].keys():
        wn_part_size = db_size
    else:
        wn_part_size = db_size - data[whole][not_in_wn]

    out.append('  Results of WordNet analysis based on ' + str(wn_part_size) + ' rule(s) (' + str(round(wn_part_size * 100.0/db_size, 2)) + '% of the ' + str(db_size) + ' rule(s)):\n')
    for rel in data[whole].keys():
        if rel == not_in_wn or rel == 'sample':
            continue
        relSize = data[whole][rel]
        out.append('      ' + rel.upper() + ': ' + str(relSize) + ' rule(s) (' + str(round(relSize * 100.0/wn_part_size, 2)) + '%):\n')

    if len(data[distances][whole]['values']) > 0:
        out.append('\n  Average WordNet distance for rules corresponding to ' + undefined.upper() + ': ' + str(float(sum(data[distances][whole]['values']))/len(data[distances][whole]['values'])) + '\n')

    source_num = len(data[per_source][whole]['tgtnum'])
    out.append(source_target_numbers_display_local(data[per_source][whole]['tgtnum']))

    # Add the avg number of each WN relation per source side
    for rel in data[per_source][whole].keys():
        if rel == 'tgtnum':
            continue
        out.append(source_relation_numbers_display_local(data[per_source][whole][rel], rel, source_num))

    return ''.join(out)


def source_target_numbers_display(counts):
    source_num = len(counts)
    if source_num == 0:
        return "  The number of unique source sides is 0."
    out = ["\n  The number of unique source sides is: " + str(source_num) + '\n']
    target_numbers = []
    while len(counts) > 0:
        target_numbers.append(counts.pop(0)[0])
    avg = float(sum(target_numbers)) / source_num
    out.append("\n  The average number of target sides per source is: " + str(avg) + '\n')

    max_n = max(target_numbers)
    min_n = min(target_numbers)
    if max_n - min_n > 100:
        out.append("  The distribution of target sides per source is as follows:\n" + normalized_histogram_for_print(target_numbers, intervals, source_num, (min_n, max_n)))
    return ''.join(out)


def source_target_numbers_display_local(counts):
    source_num = len(counts)
    if source_num == 0:
        return "  The number of unique source sides is 0."
    out = ["\n  The number of unique source sides is: " + str(source_num)+'\n']
    avg = float(sum(counts)) / source_num
    out.append("\n  The average number of target sides per source is: " + str(avg) + '\n')

    max_n = max(counts)
    min_n = min(counts)
    if max_n - min_n > 100:
        out.append("   The distribution of target sides per source is as follows:\n" + normalized_histogram_for_print(counts, intervals, source_num, (min_n, max_n)))
    return ''.join(out)


def source_relation_numbers_display(counts, relation, total_source_num):
    if total_source_num == 0:
        return ''
    source_num = len(counts)
    if source_num == 0:
        return ''
    relNumbers = []
    while len(counts) > 0:
        relNumbers.append(counts.pop(0)[0])

    # normalize with the total number of source sides, to count for those having 0 targets with the given relation
    avg = float(sum(relNumbers)) / total_source_num
    out = ["\n  The average number of '" + relation.upper() + "' targets per source is: " + str(avg)]
    return ''.join(out)


def source_relation_numbers_display_local(counts, relation, total_source_num):
    if total_source_num == 0:
        return ''
    source_num = len(counts)
    if source_num == 0:
        return ''

    # normalize with the total number of source sides, to count for those having 0 targets with the given relation
    avg = float(sum(counts)) / total_source_num
    out = ["\n  The average number of '" + relation.upper() + "' targets per source is: " + str(avg)]
    return ''.join(out)


def extract_frequent_terms(filename, num):
    f = open(filename, 'r')
    tokenized_text = nltk.word_tokenize(f.read())
    f.close()

    text = []
    for term in tokenized_text:
        # assume the db is lowercased
        text.append(term.lower())

    res = []
    unigrams = nltk.FreqDist(text)
    # use the first num/3 most frequent unigrams
    for unigram, freq in unigrams.items()[:int(num/3)]:
        res.append(unigram)
    # res.append(unigrams.keys()[int(len(unigrams) * 0.01):int(len(unigrams) * 0.01) + int(num/3)])

    bigram_measures = nltk.collocations.BigramAssocMeasures()
    trigram_measures = nltk.collocations.TrigramAssocMeasures()

    # change this to read in your data
    finder = nltk.collocations.BigramCollocationFinder.from_words(text)

    # only bigrams that appear 3+ times
    finder.apply_freq_filter(3)

    # return the 10 n-grams with the highest PMI
    for bigram in finder.nbest(bigram_measures.pmi, int(num/3)):
        res.append(" ".join(bigram))

    finder = nltk.collocations.TrigramCollocationFinder.from_words(text)
    finder.apply_freq_filter(3)
    for trigram in finder.nbest(trigram_measures.pmi, int(num/3)):
        res.append(" ".join(trigram))
    return res


def extract_terms(filename):
    f = open(filename, 'r')
    text = f.readlines()
    f.close()

    res = []
    for term in text:
        #the text should contain a single term (incl. multi-word) per line
        res.append(term.replace('\n', '').replace('\r', ''))
    return res
