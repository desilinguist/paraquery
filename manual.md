ParaQuery User Manual
---------------
This document describes the various capablities of ParaQuery.

### Attaching a paraphrase database
If you run `paraquery` in a directory that contains a ".paradb" file, that database will be automatically attached when the ParaQuery session begins. To manually attach a paraphrase database, use `attach <directory>`, where `<directory>` is the full path to the directory containing a `.paradb` file (*not* the full path to the .paradb file itself).

### ParaQuery parameters

ParaQuery has a number of parameters that affect the output of the various commands. This section provides a comprehensive list of parameters and explains the contexts in which each is used. The default value of the parameter is indicated in parentheses after the name.

- `limit` (10): limits the number of rules output by the `show` and `explain` commands. Does not affect the results for the `analyze` command. To set a new limit value, use the command `set limit <value>`. To turn off the limit, you can use `set limit none` or `set limit off`. Note that a value of 0 is not acceptable.

- `order` (highest first): when set to "highest first", the paraphrase rules with the highest probability values are shown first. To look at the rules with the lowest probabilities first, use `set order increasing` (or `set order up`, for short). To look at the highest ones first, use `set order decreasing` (or `set order down`, for short).

- `identical` (False): when set to "False", paraphrase rules where the target string is identical to the source string are excluded from the output of all commands. To include identical rules in results, use `set identical true` or `set identical on`. To exclude them, use `set identical false` or `set identical off`.

- `same_pos` (False): when set to "True", only paraphrase rules where the target string has the same part-of-speech (POS) as the source string are included in the results. Currently, the POS is determined via a WordNet lookup which means that it only works reliably for single words. To turn it on (off), use `set same_pos on (off)`.

- `unique_tgt` (False): when set to "True", paraphrase rules where the target strings are variants of the same lemma are excluded, e.g., if the source word "examination" has two paraphrase rules - one with "examined" as the target string and one with "examine", only the latter is retained in the output. To turn unique targets on (off), use `set unique_tgt on (off)`.

- `group_by` (): this parameter is used to group the results of count queries (see [Counting paraphrase rules](#counting-paraphrase-rules below), e.g., if set to, say, the WordNet relation field (`set group_by relation`) and a query like `show count source = "man"` is issued, separate counts for each type of relation will be output. If `group_by` is empty (`set group_by none`), then a single count value is returned. Possible values for `group_by` are:
    - *target*: group counts by target strings.
    - *tgtlen*: group counts by target string lengths.
    - *lendiff*: group counts by difference in lengths between the source and target strings.
    - *relation*: group counts by WordNet relations.
    - *pivotnum*: group counts by number of pivots.
    - *distance*: group counts by WordNet distance.
    - *samepos*: group counts by whether the POS is the same for the source and target strings.
    - *tgtdupl*: group counts by whether targets have duplicate lemmas or not.

To see the value of all parameters at any point, issue the `set` command without any arguments.

### Examining paraphrase rules

The `show` command allows the user to examine rules from the attached database that satisfy the given conditions. The possible conditions that can be specified with `show` are described below (note that multiple conditions can be strung together using `and`):

1. source or target strings, e.g., `show source = "man"`, `show target = "market"`. The strings may also contain asterisks as wildcards, e.g., `show source = "man*"`.

2. paraphrase probability, e.g., `show prob > 0.01`. This particular condition is most useful when combined with source and/or target string conditions, e.g., `show source = "man" and prob > 0.1`.

3. source or target lengths, e.g., `show source is 4 words` or `show target > 2 words`. For certain applications, it may be more useful to compare the lengths of the source and target strings. ParaQuery also supports this: `show source > target` will show rules where the source string is longer than the target string. The length conditions are more likely to be useful in combination with other conditions.

4. WordNet relations, e.g., '`show relation = "hypernym"`. Possible values for `relation` are *synonym*, *antonym*, *hypernym*, *hyponym*, *co-hyponym*, *meronym*, *pertainym*, *holonym*, *undefined relation* (which means that the source-target link is still in WordNet but undefined), and *not in WN* (which means that the link is not in WordNet at all). Obviously, this is most useful when combined with a source or target string condition. Since this information comes from WordNet, it works most reliably with single words.

5. WordNet distance, e.g., `show distance = 4` which shows rules with a WordNet distance of 4 between the source and target strings. Again, the utility comes from combining with other conditions and the same caveats about single words apply since WordNet is involved.

6. characteristics of pivots, e.g., `show pivots = 1` which shows rules that were generated using a single foreign language pivot and `show pivots include homme` which will show rules where the set of pivots included the pivot "homme" in it. Most useful in combination with other conditions. Note that it is possible to specify both types of pivots conditions together, e.g., if you wanted to see rules that were generated via a single pivot and that pivot was "homme", you could say `show pivots = 1 and pivots include "homme"`. However, the two conditions *must* be specified in that order (number of pivots first and then the pivot string.)

7. exploring the database; to randomly explore paraphrase rules in the database*, use the command `show different` which will show a random selection of paraphrase rules. To see the paraphrases with the highest (lowest) probabilities, use the command `show most (least) probable`.

Note that:

 - the results of all `show` queries are subject to the `limit` parameter which is set
 to 10 by default.
 - the '!=' operator is also supported where appropriate. This might be quite useful, e.g. `show source = "man" where relation != "not in WN"`.

### Displaying pivot information

It is also useful to examine what pivots were used to generate a particular phrase pair. ParaQuery allows this with the `explain` command. All of the above `show` conditions are supported with `explain`. The output displays a list of all the foreign language pivots for each rule in the output along with the probability mass contribution of that pivot.

### Counting paraphrase rules

The `show` command can also be used to produce a rule count instead of the actual rules themselves. This is easily done by placing the word `count` before the condition part of the `show` command, e.g., `show count source = "man" and prob > 0.1`. The result are simple counts unless the `group_by` (see [ParaQuery parameters](#paraquery-parameters) above) in which case multiple count values may be returned. Note that the `count` modifier is only supported with the `show` command and *not* with `explain` and `analyze`.

### Analyzing paraphrase rules in detail

ParaQuery also allows analyzing paraphrase rules in much more detail. This is accomplished using the `analyze` command, which can be applied to any of the `show` commands described above. The analysis is carried out in terms of the following:

- the distribution of the paraphrase probability of the results
- the distribution of WordNet relations present among the results
- source and target string distributions, e.g., number of unique source strings, average number of target strings per source

In some cases, the above analysis is produced not just for the entire rule set but also for the top, middle and bottom part of the rule set; these parts are computed automatically by ParaQuery in terms of the paraphrase probabilities of the rule set. This is useful to get a sense of the distinction between the high-scoring and low-scoring paraphrase rules.

For every `analyze` command, some results are shown interactively whereas even more detailed results are automatically written to a file called `analysis.txt` created in the current directory. If the file does not exist, it is created but if it already exists, new analysis results are appended to the existing file along with identifying information, e.g., the command used to run the analysis and the date and time that the command was run.

ParaQuery also allows analyzing rules based on external sources. This is very useful if you want to check whether a particular paraphrase database has the coverage you need for the text from your specific domain and, even if it does, how good is the quality of the paraphrases. There are two possible ways of specifying an external source:

1. `using text <filename>`: `<filename>` here refers to a file with one sentence on each line. This command will tell ParaQuery to automatically the 100 most frequent terms from the input file and construct queries with each of those terms as a source string (the 100 terms are equally divided between unigrams, bigrams and trigrams).

2. `using terms <filename>`: `<filename>` here refers to a file containing a collection of domain terms, one on each line. This command tells ParaQuery to construct queries with each of those terms as a source string.

The external sources only provide the source string conditions for the queries. If *all* the rules for each of those source strings need to be analyzed, then the command is `analyze all using ...`. If only the top N rules for each of those source strings need to be analyzed, then the command is `analyze top <N> using ...`. Finally, the rules to be analyzed can be constrained by using conditions predicated on other fields (excluding `source` obviously) and putting them between `analyze` and `using`, e.g., to only analyze rules that have a probability greater than 0.5 for each of the source strings, the command is `analyze prob > 0.5 using ...`.

More detailed analysis is appended to `analysis.txt` in the current directory even for external source analyses, just as for regular analyses.

**IMPORTANT**: Please note that regular analyses (the ones not using external sources) are subject to the `limit` parameter, i.e., if the `limit` was set to, say, 10, only the top 10 rules for the specified query conditions will be analyzed. However, for external source analyses, the `limit` parameter is ignored since the constraints are specified explicitly as described above.

### Scripting Support

Although the main use of ParaQuery is as an interactive tool, it is possible to use it to extract the paraphrases from the database in batch mode, perhaps once the analysis is finished and the user wants to extract the relevant paraphrases for his or her application. `show` and `explain` commands can be run in batch mode and produce tab-separated output that can be easily consumed by other scripts or tools. `analyze` commands are not supported in batch mode since it is designed only for interactive analysis and not for programmatic use. Running scripts is extremely simple, just write the commands you want to run into a file and run `paraquery <script>`. Please note that an explicit `attach` command should be the first line of the script unless you are running the script inside a directory that already contains a .paradb file.
