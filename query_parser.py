from pyparsing import oneOf, Literal, Word, nums, OneOrMore, Optional, Group, dblQuotedString, sglQuotedString, Combine


class Parser:

    def __init__(self):

        ###################################################
        # 1. BINARY SOURCE/TARGET <-> SOURCE/TARGET QUERY
        #    Example: source > target, source = target etc.
        ###################################################
        sourceOrTarget = oneOf("source target")
        integer = Word(nums)
        Op = oneOf("= != < > <= >=")
        binarySourceTargetQueryStr = (sourceOrTarget("lhs") + Op("op") + sourceOrTarget("rhs") + Optional(Group(Literal("by") + integer("lendiff") + Optional(oneOf("word words")))("lenclause")))("condition*")

        #######################################################################
        # 2. BINARY SOURCE/TARGET <-> Phrase query
        #    Example: source contains man, source = man, source is 4 words etc.
        #######################################################################
        # Phrase = Combine(OneOrMore(Word(alphas + " ")))
        Phrase = dblQuotedString | sglQuotedString
        Op = oneOf("is = > <")
        WordLenExpr = Group(Word(nums)("len") + oneOf("word words"))
        binarySourceTargetPhraseQueryStr = (sourceOrTarget("lhs") + Op("op") + (WordLenExpr("lenclause") | Phrase("phrase")))("condition*")

        ####################################################
        # 3. BINARY relation query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Rel = Word('relation') | Word('rel')
        Op = oneOf("= is > < != >= <=")
        RelName = dblQuotedString | sglQuotedString | Word(nums)
        binaryRelQueryStr = (Rel + Op("op") + RelName("relname"))("condition*")

        ####################################################
        # 3. BINARY pivots query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Piv = Word('pivots')
        Op = oneOf("= is > < != >= <= include")
        Pivots = Word(nums) | dblQuotedString | sglQuotedString
        binaryPivotsQueryStr = (Piv + Op("op") + Pivots("pivotnum"))("condition*")

        ####################################################
        # 3. BINARY distance query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Dist = Word('distance')
        Op = oneOf("= is > < != >= <=")
        Distance = Word(nums)
        binaryDistanceQueryStr = (Dist + Op("op") + Distance("wndist"))("condition*")

        ####################################################
        # 3. BINARY Prob <-> number query
        #    Example: prob < 0.5, prob >= 0.5
        ####################################################
        zeroToOneFloat = Combine(Literal("0.") + Word(nums))
        Op = oneOf("> < <= >=")
        binaryProbQueryStr = (Literal("prob")("lhs") + Op("op") + zeroToOneFloat("probval"))("condition*")

        ##################################
        # 3. UNARY identical/non-identical
        ##################################
        unaryIdentQueryStr = oneOf("non-identical identical same different").setResultsName("ident")

        ############################################################
        # 4. UNARY probability
        #    Example: most probable, least probable etc.
        ############################################################
        adjective = oneOf("most least")
        unaryProbQueryStr = (adjective("adj") + Literal("probable"))("prob")

        ############################################################
        # 4. Combination of any of the binary queries
        #    Example: most probable, least probable etc.
        ############################################################
        unaryQueryStr = unaryIdentQueryStr | unaryProbQueryStr
        binaryQueryStr = binarySourceTargetQueryStr | binarySourceTargetPhraseQueryStr | binaryProbQueryStr | binaryRelQueryStr | binaryPivotsQueryStr | binaryDistanceQueryStr
        multipleBinaryQueryStr = binaryQueryStr + Optional(OneOrMore(Literal("and") + binaryQueryStr))

        # final query string
        # Lili Kotlerman: added 'count' to queries
        count = Word('count')
        self._queryStr = Optional(count("count"))+(multipleBinaryQueryStr | unaryQueryStr)

    def parse(self, query):
        return self._queryStr.parseString(query)
