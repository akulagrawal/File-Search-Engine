import glob
import re
import nltk
from nltk.corpus import stopwords
from pathlib import Path
import json
from math import log2
import time
from autocorrect import spell
import os.path
# import linecache
# import copy


class FileIndexing:

    def __init__(self, doclist, wordlist, wordloclist):
        self.docfile = doclist
        self.wordfile = wordlist
        self.wordlocfile = wordloclist
        self.avgdl = 0
        self.numdocs = 0
        content = {}
        # if files are not made, then make them
        if not Path(doclist).is_file():
            with open(self.docfile, 'w') as outfile:
                json.dump(content, outfile, default=self.jdefault, indent=4)

        if not Path(wordlist).is_file():
            with open(self.wordfile, 'w') as outfile:
                json.dump(content, outfile, default=self.jdefault, indent=4)

        if not Path(wordloclist).is_file():
            with open(self.wordlocfile, 'w') as outfile:
                json.dump(content, outfile, default=self.jdefault, indent=4)

    def jdefault(self, o):
        return o.__dict__

    def get_text_only(self, textdata):
        # removing non alpha-numeric terms
        splitter = re.compile('\\W+')
        mp = splitter.split(textdata)
        tokens = [s.lower() for s in mp if s != '']
        # stemming the terms
        ps = nltk.stem.PorterStemmer()
        stemmed = []
        for words in tokens:
            stemmed.append(ps.stem(words))
        # returning the list of stemmed words
        return stemmed

    def crawl(self, dirname):
        print("Checking for new files")
        # pr = "./programming/"
        pr = dirname
        with open(self.docfile, 'r+') as json_data:
            doclist = json.load(json_data)
        with open(self.wordfile, 'r+') as json_data:
            wordlist = json.load(json_data)
        with open(self.wordlocfile, 'r+') as json_data:
            wordloclist = json.load(json_data)
        if len(doclist) > 0 and doclist['dirname'] != pr:
            doclist = {}
            wordlist = {}
            wordloclist = {}
            doclist['dirname'] = pr
        else:
            if len(doclist) == 0:
                doclist['dirname'] = pr
        for file in glob.glob(pr + "*.txt"):
            url = file
            if url in doclist:
                modifiedtime = time.ctime(os.path.getmtime(url))
                if modifiedtime == doclist[url]['lastmodtime']:
                    continue
            with open(url, 'r', errors='ignore') as f:
                counter = 1
                wordcounter = 0
                # print(time.time())
                for str1 in f:
                    words = self.get_text_only(str1)

                    for word in words:
                        wordcounter += 1
                        if word in toignore:
                            continue

                        if word in wordlist:
                            if url in wordlist[word]:
                                wordlist[word][url] += 1
                            else:
                                wordlist[word][url] = 1
                                wordlist[word]["predoc"] += 1

                            if url in wordloclist[word]:
                                wordloclist[word][url].append([wordcounter, counter])
                            else:
                                wordloclist[word][url] = []
                                wordloclist[word][url].append([wordcounter, counter])
                        else:
                            wordlist[word] = {}
                            wordlist[word]["predoc"] = 1
                            wordlist[word][url] = 1

                            wordloclist[word] = {}
                            wordloclist[word][url] = []
                            wordloclist[word][url].append([wordcounter, counter])

                    counter += 1
                doclist[url] = {}
                doclist[url]['wordcount'] = wordcounter
                doclist[url]['lastmodtime'] = time.ctime(os.path.getmtime(url))

        with open(self.docfile, 'w') as outfile:
            json.dump(doclist, outfile, default=self.jdefault, indent=4)
        with open(self.wordfile, 'w') as outfile:
            json.dump(wordlist, outfile, default=self.jdefault, indent=4)
        with open(self.wordlocfile, 'w') as outfile:
            json.dump(wordloclist, outfile, default=self.jdefault, indent=4)
        print("Indexing Complete")


class Search:
    def __init__(self, doclist, wordlist, wordloclist):
        with open(doclist, 'r') as json_data:
            self.doclist = json.load(json_data)
        with open(wordlist, 'r') as json_data:
            self.wordlist = json.load(json_data)
        with open(wordloclist, 'r') as json_data:
            self.wordloclist = json.load(json_data)
        self.list_querywords = {}
        self.doc_for_phrasequery = {}
        self.stemmed = []

    def get_text_only(self, textdata, correction=True):
        splitter = re.compile('\\W+')
        xp = splitter.split(textdata)
        tokens = [s.lower() for s in xp if s != '']
        # print(tokens)
        if correction:
            correctedtoken = []
            refinedquery = ""
            anychange = False
            for word in tokens:
                xp = spell(word)
                # print(xp,word)
                if xp != word:
                    anychange = True
                refinedquery = refinedquery + " " + xp
                correctedtoken.append(xp)
            if anychange:
                confirm = input("Did u mean :"+refinedquery+" ? Enter 'y' to confirm...")
                if confirm == 'y':
                    tokens = correctedtoken
        self.list_querywords =tokens
        ps = nltk.stem.PorterStemmer()
        stemmed = []
        for words in tokens:
            stemmed.append(ps.stem(words))
        if not correction:
            return tokens, stemmed
        self.stemmed = stemmed
        return stemmed

    def total_length(self):
        numdocs = len(self.doclist) - 1
        summation = 0
        for x, y in self.doclist.items():
            if x == 'dirname':
                continue
            summation = summation + y['wordcount']
        avgdl = float(summation/float(numdocs))
        return avgdl, numdocs

    def query(self, q):
        self.phrasequery(q, printing=False)
        start_time = time.time()
        words = self.stemmed
        doclist = {}
        linelist = {}
        nqlist = {}
        lll = len(words)

        for word in words:
            if word in self.wordlist:
                nqlist[word] = len(self.wordloclist[word])
                pos = self.wordloclist[word]
                for docs in pos:
                    if docs in doclist:
                        if word in doclist[docs]:
                            continue
                        else:
                            linenum = [x[1] for x in pos[docs]]
                            linelist[docs].append(linenum)
                            doclist[docs][word] = pos[docs]
                    else:
                        doclist[docs] = {}
                        linelist[docs] = []
                        linenum = [x[1] for x in pos[docs]]
                        linelist[docs].append(linenum)
                        doclist[docs][word] = pos[docs]
            else:
                nqlist[word] = 0
        # print(linelist)
        if len(doclist) == 0:
            print("Not found!!")
            return
        scoring = self.partialokapi(doclist=doclist, nqlist=nqlist, querylen=lll)
        finallines = {}
        for doc in doclist:
            finallines[doc] = self.unionlists(linelist[doc])
            # print(doc, finallines[doc])
        sortscore = sorted(scoring, key=scoring.get, reverse=True)
        # print(sortscore)
        pq = "file://"
        numberofdoc = len(sortscore)
        end_time = time.time()
        print("Found %d results in %f seconds\n" % (numberofdoc, end_time-start_time))
        counter = 0
        for x in sortscore:
            if counter == 10:
                usercomm = input("Press 'y' to see next 20 results...\n")
                if usercomm == 'y':
                    counter = 0
                else:
                    return

            print("filename : ", (pq+x))
            print("\nLine Numbers :")
            # for word in doclist[x]:
            #     print(self.list_querywords[word]+" : ", [y[1] for y in doclist[x][word]])
            if x in self.doc_for_phrasequery:
                print("Query found together at linenumber(s) :", self.doc_for_phrasequery[x])
            with open(x, 'r', errors='ignore') as f:
                xp = f.readlines()
                for i in finallines[x]:
                    print_line = ''
                    line_string = xp[i-1]
                    finallist, stemmedw = self.get_text_only(line_string, correction=False)
                    # print(finallist)
                    wcounter = 0
                    for word in stemmedw:
                        if word in self.stemmed:
                            print_line = print_line + "\033[93m " + finallist[wcounter] + "\033[00m"
                        else:
                            print_line = print_line + " " + finallist[wcounter]
                        wcounter += 1
                    # if found:
                    print("Line number " + str(i) + " :" + print_line)

            print("Score : ", scoring[x])
            # print("\n")
            print('------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
            print('------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
            counter += 1

    def intersectlists(self, lists):
        if len(lists) == 0:
            return []
        # start intersecting from the smaller list
        lists.sort(key=len)
        # print lists
        mm = set(lists[0]).intersection(*lists)
        return list(mm)

    def unionlists(self, lists):
        if len(lists) == 0:
            return []
        mm = set().union(*lists)
        return sorted(list(mm))

    def phrasequery(self, q, printing=True):
        words = self.get_text_only(q)
        start_time = time.time()
        doclist = {}
        nqlist = {}
        wordll = []
        locationdict = {}
        # lll = len(words)
        for word in words:
            if word in self.wordlist:
                app = [x for x in self.wordlist[word] if x != 'predoc']
                wordll.append(app)
            else:
                if printing:
                    print("Not found!!")
                return
        finaldocs = self.intersectlists(wordll)
        # print(finaldocs)

        for word in words:
            nqlist[word] = len(self.wordloclist[word])
            pos = self.wordloclist[word]
            for docs in finaldocs:
                if docs not in doclist:
                    doclist[docs] = {}
                # print(pos[docs])
                doclist[docs][word] = pos[docs]
        # newdoclist = copy.deepcopy(doclist)
        results = {}
        linenum = {}
        for docs in doclist:
            counter = 0
            dummy = []
            for word in words:
                for x in doclist[docs][word]:
                    locationdict[x[0]] = x[1]
                    x[0] = x[0] - counter
                # doclist[docs][word][0] = [(x-counter) for x in doclist[docs][word][0]]
                dummy.append([x[0] for x in doclist[docs][word]])
                counter += 1
            # print(docs,dummy)
            resultant = self.intersectlists(dummy)
            if len(resultant) == 0:
                continue
            else:
                # print(resultant)
                linenum[docs] = [locationdict[x] for x in resultant]
                results[docs] = len(resultant)
        if printing is False:
            self.doc_for_phrasequery = linenum
            return

        if len(results) == 0:
            print("Nothing found")
            return 0
        scoring = self.phraseokapi(doclist=results)
        sortscore = sorted(scoring, key=scoring.get, reverse=True)
        # print(sortscore)
        pq = "file://"
        numberofdoc = len(sortscore)
        end_time = time.time()
        print("Found %d results in %f seconds\n" % (numberofdoc, end_time-start_time))
        for x in sortscore:
            print("filename : ", (pq + x))
            print("line number(s) :", linenum[x])
            with open(x, 'r', errors='ignore') as f:
                xp = f.readlines()
                for i in linenum[x]:
                    print_line = ''
                    line_string = xp[i-1]
                    # print(line_string)
                    finallist, stemmedw = self.get_text_only(line_string, correction=False)
                    # print(finallist)
                    wcounter = 0
                    for word in stemmedw:
                        if word in self.stemmed:
                            print_line = print_line + "\033[93m " + finallist[wcounter] + "\033[00m"
                        else:
                            print_line = print_line + " " + finallist[wcounter]
                        wcounter += 1
                    # if found:
                    print("Line number "+ str(i) +" :"+print_line)

            print("Score : ", scoring[x])
            print('------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
            print('------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
        # return numberofdoc, (end_time-start_time)

    def phraseokapi(self, doclist, k=1.2, b=0.75, delta=1.0):
        avgdl, n = self.total_length()
        counts = dict([(docid, 0) for docid in doclist])
        val = len(doclist)
        for docs in doclist:
            doc_length = int(self.doclist[docs]['wordcount'])
            numerator = (k + 1) * doclist[docs]
            denominator = doclist[docs] + k * (1 - b + b * (doc_length / avgdl))
            idf = log2(n/val)
            score = idf * (delta + numerator / denominator)
            counts[docs] = score
        ncounts = self.normalizescores(counts)
        return ncounts

    def normalizescores(self, scores, smallisbetter=0):
        vsmall = 0.00001  # Avoid division by zero errors
        if smallisbetter:
            minscore = min(scores.values())
            return dict([(u, float(minscore) / max(vsmall, l)) for (u, l) in scores.items()])
        else:
            maxscore = max(scores.values())
            if maxscore == 0:
                maxscore = vsmall
            return dict([(u, float(c) / maxscore) for (u, c) in scores.items()])

    def partialokapi(self, doclist, nqlist, querylen, k=1.2, b=0.75, delta=1.0):
        avgdl, n = self.total_length()
        # print(avgdl, N)
        counts = dict([(docid, 0) for docid in doclist])
        # print(counts)

        for docid, values in doclist.items():
            score = 0.0
            counter = 0.0
            # print(values)
            doc_length = int(self.doclist[docid]['wordcount'])
            # print(doc_length)
            for dictionarywords in values:
                    # print(dictionarywords)
                counter += 1.0
                numerator = (k + 1) * len(values[dictionarywords])
                # print(N, nqlist[dictionarywords])
                denominator = len(values[dictionarywords]) + k * (1 - b + b * (doc_length / avgdl))
                idf = log2(n/(nqlist[dictionarywords]))
                score += idf * (delta + numerator / denominator)
            counts[docid] = score*counter/(3*querylen)
        ncounts = self.normalizescores(counts)
        return ncounts


def stemmer(tokens):
    ps = nltk.stem.PorterStemmer()
    stemmed = []
    for words in tokens:
        stemmed.append(ps.stem(words))
    return stemmed


ignorewords = set(stopwords.words('english'))
toignore = stemmer(ignorewords)
# toignore = ignorewords
docfile = "doclist.txt"
wordfile = "wordfile.txt"
wordlocfile = "wordlocfile.txt"
cp = FileIndexing(docfile, wordfile, wordlocfile)
dirname = input("Please enter your directory(full path)....")
startindextime = time.time()
cp.crawl(dirname)
endindextime = time.time()
print("Indexing completed in %f seconds" % (endindextime-startindextime))

# print(cp.total_length())
permission = True
while permission:
    sp = Search(docfile, wordfile, wordlocfile)
    query = input('Please enter your query (enclose under "." for full-phrase query)....')
    if query != '':
        print('You queried for "%s"  : ' % query)
        if query.startswith('"') and query.endswith('"'):
            sp.phrasequery(query)
        else:
            sp.query(query)
    inpq = input('Want to search again, press "y" to confirm : ')
    if inpq != 'y':
        permission = False
