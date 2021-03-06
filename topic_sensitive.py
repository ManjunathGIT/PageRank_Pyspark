
#!/usr/bin/env python

import re, sys
from operator import add

from pyspark import SparkContext


def computeContribs(urls, rank):
    """Calculates URL contributions to the rank of other URLs."""
    num_urls = len(urls)
    for url in urls: yield (url, rank / num_urls)


def parseNeighbors(urls):
    """Parses a urls pair string into urls pair."""
    parts = re.split(r'\s+', urls)
    return parts[0], parts[1]


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print >> sys.stderr, "Usage: pagerank <master> <file> <number_of_iterations>"
        exit(-1)

    # Initialize the spark context.
    sc = SparkContext(sys.argv[1], "TopicSensitive")
    
    # Loads in input file. It should be in format of:
    #     URL         neighbor URL
    #     URL         neighbor URL
    #     URL         neighbor URL
    #     ...
    lines = sc.textFile(sys.argv[2], 1)
    pages = sc.textFile(sys.argv[4], 1)
    # Loads all URLs from input file and initialize their neighbors.
    links = lines.map(lambda urls: parseNeighbors(urls)).distinct().groupByKey().cache()
    topics = pages.map(lambda urls: urls).distinct()
    # Loads all URLs with other URL(s) link to from input file and initialize ranks of them to one.
    ranks = links.map(lambda (url, neighbors): (url, 1.0))
    # Calculates and updates URL ranks continuously using PageRank algorithm.
    for iteration in xrange(int(sys.argv[3])):
        # Calculates URL contributions to the rank of other URLs.
        contribs = links.join(ranks).flatMap(lambda (url, (urls, rank)):
            computeContribs(urls, rank))
        # Re-calculates URL ranks based on neighbor contributions.
        ranks = contribs.reduceByKey(add).mapValues(lambda rank: rank * 0.85)
        new_ranks = [(v[0], v[1]) for i, v in enumerate(ranks.collect())]
        for number, i in enumerate(new_ranks):
            if i[0] in topics.collect():
                new_ranks[number] = (i[0], i[1]+0.15)
        ranks = sc.parallelize(new_ranks)

    # Collects all URL ranks and dump them to console.
    for (link, rank) in ranks.collect():
        print "%s has rank: %s." % (link, rank)

