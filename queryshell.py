#!/usr/bin/env python

# This script is a command-line shell to query paraphrase tables.
# Authors: Nitin Madnani, nmadnani@ets.org, August 2011
#          Lili Kotlerman, lili.dav@gmail.com, June 2012

import math
import operator
import os
import sqlite3
import subprocess
import sys
from datetime import datetime

from cmd import Cmd

import query_parser
import para_reader
import para_wn
import para_analysis


class ParaQueryApp(Cmd):

    # set some basic class-wide variables
    _BASICSQLCMD = 'select source, target, pe2e1, relation, pivotnum, pivots, distance from paraphrase'
    # the counting SQL command needs to have a variable since we also want to show the value of the grouping by variable
    # the {} variable is instantiated later appropriately depending on the value of the group_by setting
    _COUNTSQLCMD = 'select "{}", count(*) as cnt from paraphrase'
    _FLIPPED_OPS = dict([('<', '>'), ('>', '<'), ('<=', '=>'), ('=>', '<=')])
    _POS_IDX_TO_VALUES = {1: 'same', 0: 'different', -1: 'unknown'}
    _ORDER_VALUES = {'highest first': 'pe2e1 asc', 'lowest first': 'pe2e1 desc'}

    #either 'basic' or 'count' depending on the query
    _mode = 'basic'

    # change the prompt to something more useful
    prompt = 'query> '

    # by default, we assume interactive and verbose mode
    _interactive = True

    # set up the database and cursor before entering the command loop unless
    # it was already set up by using a command line argument. Also set up
    # the default values for the internal variables in either case.
    def preloop(self):
        if not hasattr(self, '_dbfile'):
            if os.path.exists(os.path.join(os.getcwd(), '.paradb')):
                self.do_attach(os.getcwd())
            else:
                self._num_records = 0
                sys.stderr.write('\n No database found in current directory. \n Use "index <filename>" to generate a new database.\n Use "attach <path>" to attach a database.\n\n')

        # set up the internal variables
        # Applied to 'basic' queries, not to 'count' queries
        self._limit = 10
        self._identical = False
        self._order = 'highest first'
        self._debug = False
        # Field for 'group by', applied only for 'count' queries. Set to '' to avoid grouping
        self._group_by = ''
        self._explain = False
        self._same_pos = False
        self._unique_tgt = False

        # read in the query grammar
        self._query_parser = query_parser.Parser()

    def emptyline(self):
        sys.stdout.write('\n')
        sys.stdout.flush()

    # simple exit/quit methods
    def do_quit(self, arg):
        return True

    do_q = do_exit = do_EOF = do_quit

    # method to run shell commands
    def do_shell(self, arg):
        sub_cmd = subprocess.Popen(arg, shell=True, stdout=subprocess.PIPE)
        output = sub_cmd.communicate()[0]
        sys.stdout.write(output + '\n')
        sys.stdout.flush()

    # Method to regenerate the database and indices. The fields in the database are:
    #    source (text), target (text), identity (integer), srclen (integer), tgtlen (integer), lendiff [=tgtlen-srclen] (integer), pe2e1 (float),
    #    number of pivots (integers), pivots (list), wordnet relation (integer) if available, wordnet distance (integer), same pos (binary),
    #    duplicate (binary)
    # Each field should be separately indexed.
    def do_index(self, parafile):
        """
        Index a given paraphrase rule file for querying.
        """

        # create a database file
        conn = sqlite3.connect('.paradb')
        c = conn.cursor()

        sys.stderr.write(str(datetime.now()))
        # create the table
        sys.stderr.write('\n Creating table ... ')
        c.execute('''create table paraphrase (source text, target text, identity integer, srclen integer, tgtlen integer, lendiff integer, pe2e1 real, pivotnum integer, pivots text, relation integer, distance integer, samepos integer, tgtdupl integer)''')
        sys.stderr.write('done.\n')

        # populate the table
        sys.stderr.write(' Adding records to table ... ')
        reader = para_reader.ParaReader(parafile)
        src = ""
        for fieldtuple in reader:
            #Input file must be sorted by the source side. When reached a new source, clean the target_lemmas list used to detect duplicate targets (with the same lemma)
            if src != fieldtuple[0]:
                src = fieldtuple[0]
                target_lemmas = set([])
            tgt = fieldtuple[1]
            duplicate_target_lemma = 1
            for tgt_lemma in para_wn.get_lemmas(tgt):
                #consider the tgt as non-duplicate if at least one of its lemmas was not seen with the current source side before
                if tgt_lemma not in target_lemmas:
                    duplicate_target_lemma = 0
                target_lemmas.add(tgt_lemma)
            relation = para_wn.get_wordnet_relation(src, tgt)[1]
            distance = para_wn.get_shortest_path(src, tgt)
            # 1 -same, 0 - no, -1 - don't know
            samepos = para_wn.is_same_pos(src, tgt)
            fieldtuple += (relation, distance, samepos, duplicate_target_lemma)
            c.execute('insert into paraphrase values (?,?,?,?,?,?,?,?,?,?,?,?,?)', fieldtuple)
            self._num_records += 1
        sys.stderr.write('done. Added %d records.\n' % self._num_records)

        sys.stderr.write(str(datetime.now()))

        # create the indices
        sys.stderr.write(' Creating indices ... ')
        n = 13
        c.execute('''create index srcidx on paraphrase(source)''')
        sys.stderr.write(' 1 out of ' + str(n))
        c.execute('''create index tgtidx on paraphrase(target)''')
        sys.stderr.write(' 2 out of ' + str(n))
        c.execute('''create index identidx on paraphrase(identity)''')
        sys.stderr.write(' 3 out of ' + str(n))
        c.execute('''create index srclenidx on paraphrase(srclen)''')
        sys.stderr.write(' 4 out of ' + str(n))
        c.execute('''create index tgtlenidx on paraphrase(tgtlen)''')
        sys.stderr.write(' 5 out of ' + str(n))
        c.execute('''create index lendiffidx on paraphrase(lendiff)''')
        sys.stderr.write(' 6 out of ' + str(n))
        c.execute('''create index probidx on paraphrase(pe2e1)''')
        sys.stderr.write(' 7 out of ' + str(n))
        c.execute('''create index relidx on paraphrase(relation)''')
        sys.stderr.write(' 8 out of ' + str(n))
        c.execute('''create index pivotnumidx on paraphrase(pivotnum)''')
        sys.stderr.write(' 9 out of ' + str(n))
        c.execute('''create index pivotidx on paraphrase(pivots)''')
        sys.stderr.write(' 10 out of ' + str(n))
        c.execute('''create index distidx on paraphrase(distance)''')
        sys.stderr.write(' 11 out of ' + str(n))
        c.execute('''create index sameposidx on paraphrase(samepos)''')
        sys.stderr.write(' 12 out of ' + str(n))
        c.execute('''create index tgtduplidx on paraphrase(tgtdupl)''')
        sys.stderr.write(' 13 out of ' + str(n))
        sys.stderr.write('Done.\n')
        sys.stderr.write(str(datetime.now()))

        # analyze the indices
        sys.stderr.write(' Analyzing indices ... ')
        c.execute('''analyze''')
        sys.stderr.write('done.\n\n')

        # commit the changes and return cursor
        conn.commit()
        self._cursor = c
        self._dbfile = os.path.join(os.getcwd(), '.paradb')

    def do_attach(self, dbpath):
        """
        Attach to database at given path.
        """
        dbfile = os.path.join(dbpath, '.paradb')
        if os.path.exists(dbfile):
            sys.stderr.write('\n Attaching paraphrase database.\n Use "index <filename>" to generate a new database.\n Use "attach <path>" to attach a different database.\n\n')
            self._dbfile = dbfile
            conn = sqlite3.connect(os.path.join(dbfile))
            c = conn.cursor()
            self._num_records, = c.execute('''select max(rowid) from paraphrase''').fetchone()
            self._cursor = c
        else:
            sys.stderr.write('\n Error: the path {} does not contain a paraphrase database.\n\n'.format(dbpath))

    # set the value for the unique_tgt variable
    def _set_unique_tgt_value(self, value):
        if value.lower() in ['off', 'false']:
            self._unique_tgt = False
        elif value.lower() in ['on', 'true']:
            self._unique_tgt = True
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the same_pos variable
    def _set_same_pos_value(self, value):
        if value.lower() in ['off', 'false']:
            self._same_pos = False
        elif value.lower() in ['on', 'true']:
            self._same_pos = True
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the identical variable
    def _set_identical_value(self, value):
        if value.lower() in ['off', 'false']:
            self._identical = False
        elif value.lower() in ['on', 'true']:
            self._identical = True
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the debug variable
    def _set_explain_value(self, value):
        if value.lower() in ['off', 'false']:
            self._explain = False
        elif value.lower() in ['on', 'true']:
            self._explain = True
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the debug variable
    def _set_debug_value(self, value):
        if value.lower() in ['off', 'false']:
            self._debug = False
        elif value.lower() in ['on', 'true']:
            self._debug = True
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the order variable
    def _set_order_value(self, value):
        if value.lower() in ['random', 'rand']:
            self._order = 'random()'
        elif value.lower() in ['prob', 'pe2e1', 'probability', 'highprobfirst', 'desc', 'down', 'decreasing']:
            self._order = 'highest first'
        elif value.lower() in ['lowprobfirst', 'asc', 'up', 'increasing']:
            self._order = 'lowest first'
        else:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')

    # set the value for the limit variable
    def _set_limit_value(self, value):
        if value in ['off', 'none']:
            value = -1
        try:
            value = int(value)
            assert value != 0
        except:
            sys.stderr.write('\n Error: incorrect value for setting.\n\n')
        else:
            self._limit = value

    # set the value for the group_by variable
    def _set_group_by_value(self, value):
        if value.lower() in ['none', 'off']:
            self._group_by = ''
        elif value.lower() in ['source', 'target', 'identity', 'srclen', 'tgtlen', 'lendiff', 'relation', 'pivotnum', 'distance', 'samepos', 'tgtdupl']:
            self._group_by = value.lower()
        else:
            sys.stderr.write("\n Error: incorrect value for setting.\n\n")

    # print out the current variable settings
    def _show_settings(self):
        out = ['\n Current settings:']
        out.append('  limit: {}'.format(self._limit))
        out.append('  order: {}'.format(self._order))
        out.append('  identical: {}'.format(self._identical))
        out.append('  same_pos: {}'.format(self._same_pos))
        out.append('  unique_tgt: {}'.format(self._unique_tgt))
        out.append('  group_by: {}'.format(self._group_by))
        out.append('  debug: {}'.format(self._debug))
        out.append('\n')
        sys.stdout.write('\n'.join(out))
        sys.stdout.flush()

    # generate the sql for 'show non-identical', 'show same'
    def _generate_ident_sql(self, results):
        identval = '1' if results.ident in ['same', 'identical'] else '0'
        conditional_part = 'where identity = {}'.format(identval)
        order_part = 'order by random()'
        if self._mode == 'basic':
            # Lili Kotlerman: to remove limit, set limit off
            limit_part = 'limit {}'.format(self._limit) if self._limit > 0 else ''
            finalsql = ' '.join([ParaQueryApp._BASICSQLCMD, conditional_part, order_part, limit_part])
        else:
            #'count'
            # Lili Kotlerman: to remove grouping, set group_by = ''
            group_part = 'group by "{}"'.format(self._group_by)
            finalsql = ' '.join([ParaQueryApp._COUNTSQLCMD.format(self._group_by), conditional_part, group_part, 'order by cnt asc'])
        return finalsql

    # generate the sql for 'show most probable', 'show least probable etc.'
    def _generate_unary_prob_sql(self, results):
        direction = 'desc' if results.adj == 'least' else 'asc'
        conditional_part = 'where identity = {}'.format(int(self._identical)) if not self._identical else ''
        if self._same_pos:
            if conditional_part == '':
                conditional_part = 'where samepos = 1'
            else:
                conditional_part += 'and samepos = 1'
        if self._unique_tgt:
            if conditional_part == '':
                conditional_part = 'where tgtdupl = 0'
            else:
                conditional_part += 'and tgtdupl = 0'
        order_part = 'order by pe2e1 {}'.format(direction)
        if self._mode == 'basic':
            # Lili Kotlerman: to remove limit, set limit < 0
            limit_part = 'limit {}'.format(self._limit) if self._limit > 0 else ''
            finalsql = ' '.join([ParaQueryApp._BASICSQLCMD, conditional_part, order_part, limit_part])
        else:
            #'count'
            # Lili Kotlerman: to remove grouping, set group_by = ''
            group_part = 'group by "{}"'.format(self._group_by)
            finalsql = ' '.join([ParaQueryApp._COUNTSQLCMD.format(self._group_by), conditional_part, group_part, 'order by cnt asc'])
        return finalsql

    def _generate_conditional_sql(self, results):
        conditional_part = []
        order_part = ''
        identity_clause = False

        for cond in results.condition:
            if bool(cond.probval):
                probval = str(round(-math.log(float(cond.probval)), 4))
                op = ParaQueryApp._FLIPPED_OPS[cond.op]
                conditional_part.append(' '.join(['pe2e1', op, probval]))
            elif bool(cond.rhs):
                if cond.op in ['<', '>', '<=', '=>']:
                    op = ParaQueryApp._FLIPPED_OPS[cond.op] if cond.lhs == 'source' else cond.op
                    if bool(cond.lenclause):
                        lendiff = '-' + cond.lenclause.lendiff if cond.lhs == 'source' else cond.lenclause.lendiff
                        conditional_part.append(' '.join(['lendiff = ', lendiff]))
                    else:
                        conditional_part.append(' '.join(['lendiff', op, '0']))
                else:
                    identval = '1' if cond.op == '=' else '0'
                    conditional_part.append('identity = ' + identval)
                    identity_clause = True
            elif bool(cond.lenclause):
                fieldname = 'srclen' if cond.lhs == 'source' else 'tgtlen'
                conditional_part.append(' '.join([fieldname, cond.op, cond.lenclause.len]))
            elif bool(cond.phrase):
                op = 'GLOB' if cond.phrase.find('*') > 0 else '='
                # phrase = '*' + cond.phrase + '*' if cond.op == 'contains' else cond.phrase
                conditional_part.append(' '.join([cond.lhs, op, cond.phrase]))
            elif bool(cond.relname):
                #Lili Kotlerman: added (WN) relation condition
                relname = cond.relname
                if relname in map(str, range(11)):
                    conditional_part.append(' '.join(['relation', cond.op, relname.replace("'", '')]))
                else:
                    relid = para_wn.get_relation_id(relname.replace('"', '').replace("'", ''))
                    if relid >= 0:
                        conditional_part.append(' '.join(['relation', cond.op, str(relid)]))
            elif bool(cond.pivotnum):
                #Lili Kotlerman: added condition for number of pivots
                pivotnum = cond.pivotnum
                if cond.op == 'include':
                    # In this case pivotnum should hold one pivot's text. Pivots field contains ["pivot:score", "pivot:score",...]
                    conditional_part.append(' '.join(['pivots LIKE', "'%" + '"' + pivotnum.replace('"', '').replace("'", '') + ":%'"]) + " OR" + ' pivots =="' + pivotnum.replace('"', '').replace("'", '') + '"')
                else:
                    conditional_part.append(' '.join(['pivotnum', cond.op, pivotnum]))
            elif bool(cond.wndist):
                #Lili Kotlerman: added condition for WordNet distance
                wndist = cond.wndist
                conditional_part.append(' '.join(['distance', cond.op, wndist]))

        # AND all the conditions for the conditional part
        if not identity_clause and not self._identical:
            conditional_part.append('identity = {}'.format(int(self._identical)))
        if self._same_pos:
            conditional_part.append('samepos = {}'.format(int(self._same_pos)))
        if self._unique_tgt:
            conditional_part.append('tgtdupl = 0')
        conditional_part = 'where ' + ' and '.join(conditional_part)

        # generate the order part
        order_part = 'order by {}'.format(self._ORDER_VALUES[self._order])

        if self._mode == 'basic':
            # Lili Kotlerman: to remove limit, set limit < 0
            limit_part = 'limit {}'.format(self._limit) if self._limit > 0 else ''
            finalsql = ' '.join([ParaQueryApp._BASICSQLCMD, conditional_part, order_part, limit_part])
        else:
            #'count'
            # Lili Kotlerman: to remove grouping, set group_by=''
            group_part = 'group by "{}"'.format(self._group_by)
            finalsql = ' '.join([ParaQueryApp._COUNTSQLCMD.format(self._group_by), conditional_part, group_part, 'order by cnt asc'])
        return finalsql

    # method to take a pyparsing ParseResults object and convert
    # into an appropriate sql query.
    def _generate_sql_from_query(self, query_results):
        # set _mode = 'basic' or 'count' but only for the show command. Nothing else.
        self._mode = 'count' if query_results.count else 'basic'
        if bool(query_results.prob):
            return self._generate_unary_prob_sql(query_results)
        elif bool(query_results.ident):
            return self._generate_ident_sql(query_results)
        elif bool(query_results.condition):
            return self._generate_conditional_sql(query_results)

    # how to display the output of the query
    def _display(self):
        if self._mode == 'basic':
            rows = self._cursor.fetchall()
            if not rows:
                return ''
            newrows = []
            for row in rows:
                src, tgt, pe2e1, rel, pivnum, piv, dist = row
                pe2e1 = math.exp(-float(pe2e1))
                pe2e1str = '{:>6.4}'.format(pe2e1) if pe2e1 < 0.0001 else '{:0<6.4f}'.format(pe2e1)
                rel_or_path = para_wn.get_relation_name(rel)
                if rel_or_path == 'undefined relation':
                    rel_or_path = 'WN distance=' + str(dist) if dist >= 0 else 'not connected in WN'
                newrows.append([src.encode('utf-8'), tgt.encode('utf-8'), pe2e1str, rel_or_path, pivnum, piv.encode('utf-8'), dist])
            srclens = map(len, map(operator.itemgetter(0), newrows))
            trglens = map(len, map(operator.itemgetter(1), newrows))
            probstrlens = map(len, map(operator.itemgetter(2), newrows))
            relationlens = map(len, map(operator.itemgetter(3), newrows))
            maxsrclen, maxtrglen, maxproblen, maxrellen = max(srclens), max(trglens), max(probstrlens), max(relationlens)
            return self._format_display(newrows, self._interactive, maxsrclen, maxtrglen, maxproblen, maxrellen)
        # display the count results
        else:
            rows = self._cursor.fetchall()
            if not rows:
                return ''
            res = ['']
            rows = sorted(rows)
            if self._group_by == 'relation':
                rows = [(para_wn.get_relation_name(group), count) for (group, count) in rows]
            elif self._group_by == 'samepos':
                rows = [(self._POS_IDX_TO_VALUES[group], count) for (group, count) in rows]
            else:
                rows = [(str(group), count) for (group, count) in rows]
            grouplens = map(len, map(operator.itemgetter(0), rows))
            maxgrouplen = max(grouplens)
            for group, count in rows:
                if group == '':
                    res.append(str(count))
                else:
                    res.append('{}\t{}'.format(group.rjust(maxgrouplen), count))
            res.append('')
            return '\n'.join(res)

    # helper formatting method for _display
    def _format_display(self, rows, interactive_mode, maxsrclen, maxtrglen, maxproblen, maxrellen):
        # if the results are to be shown interactively ...
        if interactive_mode:
            out = ['']
            too_wide = maxsrclen > 25 and maxtrglen > 25
            for row in rows:
                src, trg, pe2e1str, relstr, pivnum, piv, dist = row

                pivot_display = ""
                if self._explain:
                    pivots = piv.strip().replace('["', '').replace('"]', '').replace('\n', '').split('", "')
                    cnt = 1
                    for pivot in pivots:
                        pivot_display += "\n    " + str(cnt) + ".  " + pivot.replace(':', ' : ')
                        cnt += 1

                if too_wide:
                    out.append('\n  {} =>\n  {}\n  [{}]  {}  {}'.format(src, trg, pe2e1str.rjust(maxproblen), relstr.ljust(maxrellen), pivot_display))
                else:
                    if self._explain:
                        # if we are displaying pivots then we don't need to make the prob and relation fields look perfectly aligned
                        pivot_display += '\n'
                        out.append('  {} => {} [{}] {} {}'.format(src.rjust(maxsrclen), trg.ljust(maxtrglen), pe2e1str, relstr, pivot_display))
                    else:
                        out.append('  {} => {} [{}] {} {}'.format(src.rjust(maxsrclen), trg.ljust(maxtrglen), pe2e1str.rjust(maxproblen), relstr.ljust(maxrellen), pivot_display))
            out.append('')
        # otherwise generate simple tab-separated output for the script
        else:
            out = []
            for row in rows:
                src, trg, pe2e1str, relstr, pivnum, piv, dist = row
                if self._explain:
                    out.append('{}\t{}\t{}\t{}\t{}'.format(src, trg, pe2e1str, relstr, piv.strip()))
                else:
                    out.append('{}\t{}\t{}\t{}'.format(src, trg, pe2e1str, relstr))
        return '\n'.join(out)

    # method that runs the "show <query>"" command
    def do_show(self, query):
        """
        Run queries on attached paraphrase database. Examples:

        # show all paraphrases of the word "barrier"
        show source = "barrier"

        # show all paraphrases of the word "barrier" and include the identity paraphrase
        set identical on
        show source = "barrier"

        # show all phrases for which "barrier" is a paraphrase
        show target = "barrier"

        # show all paraphrases containing the word \"barrier\" and
        # where the paraphrase is of length 2 words (turn off identity paraphrases)
        set identical off
        show source = "barrier*" and target is 2 words

        # show paraphrases with highest probability
        show most probable

        # show a random set of paraphrases
        show different

        # show a random sample of paraphrases for the word "man" with
        # probability > 0.005 but a random sample instead of being sorted
        # by probability (as is the default)
        set order random
        show source = "man" and prob > 0.005

        # Perform select count(*) by adding "count" in the beginning of the query
        # e.g. show count source="man" and prob > 0.005
        # Pay attention: the returned value is not limited by the "limit" parameter
        """
        try:
            results = self._query_parser.parse(query)
        except:
            sys.stderr.write('\n Error: cannot parse query.\n\n')
        else:
            sql_query = self._generate_sql_from_query(results)
            if self._debug:
                sys.stderr.write('\nQuery: ' + sql_query + ';\n')
            self._cursor.execute(sql_query)
            sys.stdout.write(self._display() + '\n')
            sys.stdout.flush()

    # method that runs the "explain <query>"" command
    def do_explain(self, query):
        if query.count('count') > 0:
            sys.stderr.write('\n Error: cannot use "count" modifier for explain queries.\n\n')
            return False
        else:
            self._set_explain_value('on')
            try:
                results = self._query_parser.parse(query)
            except:
                sys.stderr.write('\n Error: cannot parse query.\n\n')
            else:
                sql_query = self._generate_sql_from_query(results)
                if self._debug:
                    sys.stderr.write('\nQuery: ' + sql_query + ';\n')
                self._cursor.execute(sql_query)
                sys.stdout.write(self._display() + '\n')
                sys.stdout.flush()
            self._set_explain_value('off')

    # Lili Kotlerman: added method returning query output
    # method that returns the "<query>" command results
    def do_get(self, query):
        """
        Run queries on attached paraphrase database and get their output in return.
        Examples the same as for do_show(), with "get" instead of "show"
        """
        res = []
        try:
            results = self._query_parser.parse(query)
        except:
            raise Exception
        else:
            sql_query = self._generate_sql_from_query(results)
            if self._debug:
                sys.stderr.write('\nQuery: ' + sql_query + ';\n')
            self._cursor.execute(sql_query)
            res = self._cursor.fetchall()
        return res

    # method to set some internal variables for the query shell
    def do_set(self, arg):
        """
        Set internal variables. Run \"set\" to see current settings.
        """
        # show settings if no argument
        if not arg:
            self._show_settings()
            return False
        else:
            args = arg.split('=') if '=' in arg else arg.split()

        # make sure there are the correct number of arguments
        if len(args) != 2:
            sys.stderr.write('Error: incorrect set statement.\n')
        else:
            args = [x.strip() for x in args]

        # make sure that only the appropriate settings are being set
        if args[0] in ['identical', 'order', 'limit', 'debug', 'group_by', 'explain', 'same_pos', 'unique_tgt']:
            exec('self._set_{}_value("{}")'.format(args[0], args[1]))
        else:
            sys.stderr.write('\n Error: incorrect setting name. Use "set" to see current settings.\n\n')

    # method to display information about the paraphrase database
    def do_info(self, arg):
        """
        Show information on current database.
        """
        if hasattr(self, '_dbfile'):
            sys.stdout.write('\n Database {} with {} paraphrase rules.\n\n'.format(self._dbfile, self._num_records))
            sys.stdout.flush()
        else:
            sys.stderr.write('\n No database attached. Cannot show info.\n\n')
            return False

    def _get_rules(self, arg, query):
        # get the currently set limit value since we may have to override it
        old_limit = self._limit

        rules = []
        if arg.count('top') > 0:
            # expected command is "analyze top N", where N is an int
            top_n_rules = int(arg.split()[1])
            self._set_limit_value(top_n_rules)
            get_arg = query
        elif arg.count('all') > 0:
            # expected command is "analyze all"
            self._set_limit_value(-1)
            get_arg = query
        else:
            # note that here the results are subject to the global limit
            # if the source is not specified then assume it's everything
            get_arg = arg if query == 'source = "*"' else " and ".join([query, arg])

        try:
            rules = self.do_get(get_arg)
        except:
            sys.stderr.write('\n Error: cannot parse query.\n')

        # restore previously set limit value
        self._set_limit_value(old_limit)

        return rules

    # Lili Kotlerman: added method to analyze the database
    def do_analyze(self, arg):
        """
        Analyze the attached paraphrase database / query results and output the results to "analysis.txt" in the current directory
        """
        # analyze commands can only be run in interactive mode
        if not self._interactive:
            sys.stderr.write('\n Error: analyze commands cannot be run from scripts.\n\n')
            return False

        # no counting allowed
        if arg.count('count') > 0:
            sys.stderr.write('\n Error: cannot use "count" modifier for analyze queries.\n\n')
            return False

        if arg.count('using') > 0:
            # no source conditions allowed unless 'using' is not specified
            if arg.count('source') > 0:
                sys.stderr.write('\n Error: cannot specify source condition for analyze queries with external source.\n\n')
                return False
            rules = []
            user_srcs = []
            if arg.count('text') > 0:
                user_srcs = para_analysis.extract_frequent_terms(arg.split('text ')[1], 100)
                user_srcs.sort()
                sys.stdout.write('\nThe {} most frequent terms in the given text are:\n {}\n'.format(len(user_srcs), ', '.join(user_srcs)))
            elif arg.count('terms') > 0:
                user_srcs = para_analysis.extract_terms(arg.split('terms ')[1])
                sys.stdout.write('\n Found {} terms.\n'.format(str(len(user_srcs))))
            else:
                sys.stderr.write('\n Error: cannot parse query.\n\n')
                return False

            sys.stdout.write('\n Retrieving rules from the database ... ')
            sys.stdout.flush()
            for user_src in user_srcs:
                query = 'source = "' + user_src.lower() + '"'
                rules += self._get_rules(arg, query)
        else:
            user_srcs = []
            query = 'source = "*"'
            sys.stdout.flush()
            rules = self._get_rules(arg, query)
            sys.stdout.write('\n Retrieving rules from the database ... ')

        db_size = len(rules)
        if self._limit > 0 and arg.count('using') == 0:
            sys.stdout.write("found {} paraphrase rules (limit = {}).\n".format(db_size, self._limit))
        else:
            sys.stdout.write("found {} paraphrase rules.\n".format(db_size))
        if db_size > 0:
            sys.stdout.write("\n Analyzing...")
            # sort to group rules for each source together, one by one
            rules.sort()
            out_text = ['\n\n\n===================================================== ANALYSIS =================================================================\n']
            out_text.append('Command: {}\n'.format('analyze ' + arg))
            out_text.append(self._dbfile + '\n')
            out_text.append(str(datetime.now()) + '\n\n')
            # write out a warning for non "using" queries if the limit was set
            if self._limit > 0 and arg.count('using') == 0:
                out_text.append('WARNING: this analysis was conducted with limit set to {}, i.e., only the top {} rules for each source string were analyzed. To analyze all rules, please use "set limit none" before running the analysis command.\n\n'.format(self._limit, self._limit))
            if user_srcs:
                out_text.append('Terms analyzed: {}\n'.format(user_srcs))
            # top rules have scores > percentiles[3] percentile, bottom rules have scores < percentiles[0] percentile,
            # middle rules are between percentiles[1] and percentiles[2] percentile
            percentiles = [15, 40, 60, 85]
            out_text.append("Analyzing: " + str(db_size) + " paraphrase rules.\n")
            score_distribution = para_analysis.get_score_distribution(rules)
            out_text.append(para_analysis.scores_and_percentiles_display(score_distribution, para_analysis.intervals, db_size, (0, 1)))
            percentile_scores = para_analysis.get_percentile_scores(percentiles, score_distribution)
            data = para_analysis.analyze_rules(rules, percentile_scores)

            # Add analysis of the whole collection
            analysis_to_print = para_analysis.whole_analysis_display(db_size, data)
            out_text.append(analysis_to_print)
            sys.stdout.write(analysis_to_print + '\n\n')
            sys.stdout.flush()

            if db_size > 1000:
                for part in para_analysis.parts:
                    out_text.append(para_analysis.part_analysis_display(part, data, percentile_scores, percentiles))

            f = open('analysis.txt', 'a')
            f.write(''.join(out_text))
            f.flush()
            f.close()

if __name__ == '__main__':

    # check if there are any input arguments
    args = sys.argv[1:]

    if len(args) > 0:

        # if there is a directory argument provided, assume that it is a folder containing
        # a paraphrase database and send it to do_attach
        if os.path.isdir(args[0]):
            # instantiate the interactive version of the app
            interactive_app = ParaQueryApp()
            interactive_app.do_attach(args[0])
            interactive_app.cmdloop()

        # if the input argument is a file, treat it as a script
        elif os.path.isfile(args[0]):
            with open(args[0], 'rt') as input:
                noninteractive_app = ParaQueryApp(stdin=input)
                noninteractive_app.use_rawinput = False
                noninteractive_app.prompt = ''
                noninteractive_app._interactive = False
                noninteractive_app.cmdloop()

    # if no arguments at all, then simply drop into the loop
    else:
        # instantiate the interactive version of the app
        interactive_app = ParaQueryApp()
        interactive_app.cmdloop()
