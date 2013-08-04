from pyparsing import oneOf, Literal, Word, nums, OneOrMore, Optional, Group, dblQuotedString, sglQuotedString, Combine


class Parser:

    def __init__(self):

        ###################################################
        # 1. BINARY SOURCE/TARGET <-> SOURCE/TARGET QUERY
        #    Example: source > target, source = target etc.
        ###################################################
        sourceOrTarget = oneOf("source target")
        integer = Word(nums)
        Op1 = oneOf("= != < >")
        binarySourceTargetQueryStr = (sourceOrTarget("lhs") + Op1("op") + sourceOrTarget("rhs") + Optional(Group(Literal("by") + integer("lendiff") + Optional(oneOf("word words")))("lenclause")))("condition*")

        #######################################################################
        # 2. BINARY SOURCE/TARGET <-> Phrase query
        #    Example: source contains man, source = man, source is 4 words etc.
        #######################################################################
        # Phrase = Combine(OneOrMore(Word(alphas + " ")))
        Phrase = dblQuotedString | sglQuotedString
        Op2 = oneOf("is = > <")
        WordLenExpr = Group(Word(nums)("len") + oneOf("word words"))
        binarySourceTargetPhraseQueryStr = (sourceOrTarget("lhs") + Op2("op") + (WordLenExpr("lenclause") | Phrase("phrase")))("condition*")

        ####################################################
        # 3. BINARY relation query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Rel = oneOf("relation rel")
        Op3 = oneOf("= is > < != >= <=")
        RelName = dblQuotedString | sglQuotedString | Word(nums)
        binaryRelQueryStr = (Rel + Op3("op") + RelName("relname"))("condition*")

        ####################################################
        # 3. BINARY pivots query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Piv = Literal("pivots")
        Op4 = oneOf("= is > < != >= <= include")
        Pivots = Word(nums) | dblQuotedString | sglQuotedString
        binaryPivotsQueryStr = (Piv + Op4("op") + Pivots("pivotnum"))("condition*")

        ####################################################
        # 3. BINARY distance query
        #    Example: relation = synonym, relation is antonym
        ####################################################
        Dist = Literal("distance")
        Op5 = oneOf("= is > < != >= <=")
        Distance = Word(nums)
        binaryDistanceQueryStr = (Dist + Op5("op") + Distance("wndist"))("condition*")

        ####################################################
        # 3. BINARY Prob <-> number query
        #    Example: prob < 0.5, prob >= 0.5
        ####################################################
        zeroToOneFloat = Combine(Literal("0.") + Word(nums)) | Combine(Word(nums) + Literal("e-") + Word(nums))
        Op6 = oneOf("> < <= >=")
        binaryProbQueryStr = (Literal("prob")("lhs") + Op6("op") + zeroToOneFloat("probval"))("condition*")

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
        count = Literal("count")
        self._queryStr = Optional(count("count")) + (multipleBinaryQueryStr | unaryQueryStr)

    def parse(self, query):
        return self._queryStr.parseString(query)
