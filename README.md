What is ParaQuery?
------------------
ParaQuery is a tool that helps a user interactively explore and characterize a given pivoted paraphrase collection, analyze its utility for a particular domain, and compare it to other popular lexical similarity resources – all within a single interface.

Requirements
------------

For running ParaQuery with the bundled databases, you need:

- Python 2.7 or higher.
- SQLite
- [NLTK](http://www.nltk.org)

However, if you need to generate paraphrase rules from your own bilingual data, then you also need:

 - Java 1.5 or higher
 - [Apache Hadoop](http://hadoop.apache.org)


File Formats
------------
ParaQuery works by taking a pivoted paraphrase database and converting it into an SQLite database which can then be queried. ParaQuery provides an `index` command that can take a gzipped file containing pivoted paraphrases and write out an SQLite database to disk. The gzipped file needs to contain _paraphrase rules_ in the following format on each line:

```[X] ||| source ||| target ||| features ||| pivots```

where `source` is the source English phrase being paraphrased, `target` is its paraphrase,  `features` is a whitespace-separated list of features associated with the paraphrase pair, and `pivots` is a list of the foreign-language pivots that were used in generating this particular paraphrase pair. The format is based on the format used by the [Joshua](http://joshua-decoder.org/) paraphrase extractor since that is what is currently used to produce the compressed paraphrase files (See section on Generating Paraphrase Rules below).

The features currently produced by the Joshua paraphrase extractor are as follows:

1. `0` (always 0; indicates whether the rule is a glue rule which it never is for paraphrases)
2. Ignored by ParaQuery.
3. `1` if `source` and `target` are identical
4. `-log p(target|source)`. This is what's currently used by ParaQuery as the score for a paraphrase pair.
5. `-log p(source|target)`
6. Ignored by ParaQuery.
7. Ignored by ParaQuery.
8. Number of words in `source`
9. Number of words in `target`
10. Difference in number of words between `target` and `source`
11. Is the rule purely lexical? (Right now, ParaQuery works best with purely lexical rules so this is always 1. However, in the future it might be useful for cases where this is not true, e.g., hierarchical or syntactic paraphrases.)
12. Ignored by ParaQuery.
13. Ignored by ParaQuery.
14. Ignored by ParaQuery.
15. Ignored by ParaQuery.
16. Ignored by ParaQuery.
17. Ignored by ParaQuery.

Note that we have made some modifications to the Joshua paraphrase extractor (e.g., some additional filtering options) and, therefore, we bundle our modified version with ParaQuery. Several fields produced by the paraphrase extractor are currently ignored by ParaQuery but may be useful in the future.

The `pivots` are a list of the pivoted phrases along with the score contributed to the pair by that pivot.

Here's an example of a paraphrase rule generated using French as the pivot language:

`[X] ||| accidents at sea ||| maritime accidents ||| 0.0 1.0 0.0 2.6342840508626013 2.5230584157523763 14.266144534541269 6.260026717543335 3.0 2.0 -1.0 1.0 0.0 0.0 3.833333333333333 0.1353352832366127 0.0 0.0 ||| ["accidents maritimes:0.07177033492822964"]`


Generating Paraphrase Rules
---------------------------
If you would like to use ParaQuery right out of the box, four databases are already available. These databases are generated from the European Parliament [bilingual corpora](http://www.statmt.org/europarl). The four ParaQuery databases available use the following languages as pivots:

1. French [.paradb](https://s3.amazonaws.com/paraquery-databases/fr-en/.paradb) (1.3 GB)
2. German [.paradb](https://s3.amazonaws.com/paraquery-databases/de-en/.paradb) (1.0 GB)
3. Spanish [.paradb](https://s3.amazonaws.com/paraquery-databases/es-en/.paradb) (1.4 GB)
4. Finnish [.paradb](https://s3.amazonaws.com/paraquery-databases/fi-en/.paradb) (775 MB)

Note that each of the above links is to a file called `.paradb` which is the SQLite database generated from the respective bilingual corpus for use with ParaQuery. Since they are all named `.paradb`, you should probably put them in seperate directories. To generate your own databases from your own data, please read on.

The code to generate the gzipped paraphrase rules in the format that's currently readable by ParaQuery is also included here. To generate pivoted paraphrases, you need three files: the file containing the foreign language sentences `sentences.fr`, the file containing the corresponding English sentences `sentences.en`, and, finally, a file `sentences.align` containing the word alignments between the sentences. To generate the word alignments, you can probably use the [Berkeley Word Aligner](https://code.google.com/p/berkeleyaligner/). The alignments need to be in the following format:

`0-0 1-1 1-2 2-3`

where the first number is an index for the foreign language sentence and the second number for the English sentence. Note also that both `sentences.fr` and `sentences.en` must be tokenized.

Please note that if you want to generate paraphrases using one of the other languages in the Europarl corpus, you do not need to do much work. Chris Callison-Burch has the files from each of the 13 languages nicely processed and available for download [here](http://www.cs.jhu.edu/~ccb/howto-extract-paraphrases.html) as part of his paraphrasing software.

Once these files are ready, paraphrase rule files can be created as follows:

- Prepare data to run through the Thrax offline grammar extractor (`create_thrax_data.sh` is bundled with ParaQuery under `scripts/`):
`create_thrax_data.sh sentences.fr sentences.en sentences.align > sentences.input`

- Run Thrax to extract the paraphrase grammar:
`hadoop jar thrax.jar hiero.conf <outdir> >& thrax.log`, where the library `thrax.jar` comes bundled with ParaQuery under the `lib/` directory and so does the configuration file `hiero.conf`. The only option you should need to modify is the `input-file` in `hiero.conf` -- to point to `sentences.input`. If you want to modify the other options, read more about Thrax [here](http://cs.jhu.edu/~jonny/thrax/). `<outdir>` is your desired output directory.

- Get the final hadoop output in the current directory:
`hadoop fs -getmerge <outdir>/final ./rules.gz`

- Sort the generated paraphrase rules by the source side:
`zcat rules.gz | sort -t'|' -k1,4 | gzip > rules-sorted.gz`

- Run the paraphrase grammar builder (note that `joshua.jar` is bundled with ParaQuery under `lib/`):
`(java -Dfile.encoding=UTF8 -Xmx8g -classpath joshua.jar joshua.tools.BuildParaphraseGrammarWithPivots -g rules-sorted.gz | gzip > para-grammar.gz) 2>build_para.log`.

- Sort by both source and target side:
`zcat para-grammar.gz | sort -t'|' -k4,7 | gzip > para-grammar-sorted.gz`

- Aggregate paraphrase rules (sum duplicate rules that you might get from different pivots):
`java -Dfile.encoding=UTF8 -Xmx8g -classpath joshua.jar joshua.tools.AggregateParaphraseGrammarWithPivots -g para-grammar-sorted.gz | gzip > final-para-grammar.gz`

- Sort by the source side:
`zcat final-para-grammar.gz | sort -t'|' -k1,4 | gzip > final-para-grammar-sorted.gz`

Using ParaQuery
---------------
Once the gzipped paraphrase file has been  generated, it can be easily converted to the SQLite database from inside ParaQuery:

 - Run `paraquery` (the launching script provided)
 - At the resulting prompt, run the following command which will create a `.paradb` file in the current directory:
`index final-para-grammar-sorted.gz`
 - If a `.paradb` file in the current directory, `paraquery` will automatically attach it and output a message when starting up. Otherwise, the path to the `.paradb` file must be provided as an argument.

Once you have a database loaded up, you can use the following commands to explore and examine the paraphrases:

- `show` : query database for paraphrase pairs with specific properties, e.g., to get all paraphrases with a probability score less than 0.1 for the word "man", use the query
`show source = "man" and prob < 0.1`.
- `examine`: show results as with the `show` command but also explain why each result exists by showing what pivots were used to generate it.
- `analyze`: analyze paraphrases rules in terms of how useful they for a given text from a given domain.

The following [paper](http://desilinguist.org/pdf/demo2013.pdf) explains and illustrates the commands in detail.

Acknowledgments
-----
We would like to thank [Juri Ganitkevitch](http://cs.jhu.edu/~juri/), [Jonny Weese](http://cs.jhu.edu/~jonny/), and [Chris Callison-Burch](http://www.cs.jhu.edu/~ccb/) for all their help and guidance during the development of ParaQuery.
