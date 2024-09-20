# -*- coding: utf-8 -*-
"""CSCSI550-Miniproject-1.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1YeET52Q8paC89vcKT-Pmq7s4_za9jgho

# The New York Social Graph

[New York Social Diary](https://www.newyorksocialdiary.com/) provides a
fascinating lens onto New York's socially well-to-do.  The data forms a natural social graph for New York's social elite.  Take a look at this page of a recent [To Love Unconditionally](https://www.newyorksocialdiary.com/to-love-unconditionally/).

You will notice the photos have carefully annotated captions labeling those that appear in the photos.  We can think of this as implicitly implying a social graph: there is a connection between two individuals if they appear in a picture together.

For this project, we will assemble the social graph from photo captions for parties.  Using this graph, we can make guesses at the most popular socialites, the most influential people, and the most tightly coupled pairs.

We will attack the project in three phases:
1. Get a list of all the photo pages to be analyzed.
2. Get all captions in each party, Parse all of the captions and extract guests' names.
3. Assemble the graph, analyze the graph and answer the questions

## Phase One

The first step is to crawl the data.  We want photos from parties on or before December 1st, 2014.  Go to the [Party Pictures Archive](https://web.archive.org/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures) to see a list of (party) pages.  We want to get the url for each party page, along with its date.

Here are some packages that you may find useful.  You are welcome to use others, if you prefer.
"""

import requests
#!pip install dill
import dill
import glob
from bs4 import BeautifulSoup
from datetime import datetime
import time

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import re

import itertools  # itertools.combinations may be useful
import networkx as nx

#!pip install spacy
#!python -m spacy download en_core_web_lg

import spacy
from spacy.language import Language
from spacy.tokens import Span

# from google.colab import drive
# drive.mount('/content/drive/')

"""We recommend using Python [Requests](http://docs.python-requests.org/en/master/) to download the HTML pages, and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) to process the HTML.  Let's start by getting the [first page](https://web.archive.org/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures)."""

nysd_url = "https://web.archive.org/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures"
page = requests.get(nysd_url) # Use requests.get to download the page.

"""Now, we process the text of the page with BeautifulSoup."""

soup = BeautifulSoup(page.text, "lxml")

"""This page has links to 50 party pages. Look at the structure of the page and determine how to isolate those links.  Your browser's developer tools (usually `Cmd`-`Option`-`I` on Mac, `Ctrl`-`Shift`-`I` on others) offer helpful tools to explore the structure of the HTML page.

Once you have found a pattern, use BeautifulSoup's [select](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors) or [find_all](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#find) methods to get those elements.
"""

links = soup.select("div.views-row")

print("URL: ", links[0].find("a").get("href"))
print("Date: ", links[0].select("span.field-content")[1].text)

"""There should be 50 per page."""

len(links) == 50

"""Let's take a look at that first link.  Figure out how to extract the URL of the link, as well as the date.  You probably want to use `datetime.strptime`.  See the [format codes for dates](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) for reference."""

link = links[0]
# Check that the title and date match what you see visually.
links[0].find("a").get("href")

"""For purposes of code reuse, let's put that logic into a function.  It should take the link element and return the URL and date parsed from it."""

def get_link_date(el):
    url = el.find("a").get("href")
    date_text = el.select("span.field-content")[1].text
    ## Example date format:
    ## Tuesday, September 1, 2015
    date = datetime.strptime(date_text, "%A, %B %d, %Y")
    return url, date

get_link_date(links[0])

"""You may want to check that it works as you expected.

Once that's working, let's write another function to parse all of the links on a page.  Thinking ahead, we can make it take a Requests [Response](https://requests.readthedocs.io/en/master/api/#requests.Response) object and do the BeautifulSoup parsing within it.
"""

def get_links(response):
  links = []
  for r in response:
    links.append(get_link_date(r))
  return links # A list of URL, date pair s

get_links(links)

"""If we run this on the previous response, we should get 50 pairs."""

# These should be the same links from earlier
len(get_links(links)) == 50

"""But we only want parties with dates on or before the first of December, 2014.  Let's write a function to filter our list of dates to those at or before a cutoff.  Using a keyword argument, we can put in a default cutoff, but allow us to test with others."""

def filter_by_date(links, cutoff=datetime(2014, 12, 1)):
    # Return only the elements with date <= cutoff
    # Date in second element of links tuples
    # link = (URL, Date)
    return [link for link in links if link[1] <= cutoff]

filter_by_date(get_links(links))

"""With the default cutoff, there should be no valid parties on the first page.  Adjust the cutoff date to check that it is actually working."""

# Double check the dates are being extracted correctly
len(filter_by_date(get_links(links))) == 0

"""Now we should be ready to get all of the party URLs.  Click through a few of the index pages to determine how the URL changes.  Figure out a strategy to visit all of them.

HTTP requests are generally IO-bound.  This means that most of the time is spent waiting for the remote server to respond.  If you use `requests` directly, you can only wait on one response at a time.  [requests-futures](https://github.com/ross/requests-futures) lets you wait for multiple requests at a time.  You may wish to use this to speed up the downloading process.
"""

#!pip install requests-futures
#from requests_futures.sessions import FuturesSession

link_list = []
# You can use link_list.extend(others) to add the elements of others
# to link_list.

for i in range(1, 27):
  index_url = f"https://web.archive.org/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures?page={i}"
  page = requests.get(index_url)
  soup = BeautifulSoup(page.text, "lxml")
  links = soup.select("div.views-row")
  link_list.extend(filter_by_date(get_links(links)))
  time.sleep(10) ### Avoid getting blocked by making requests too quickly

"""In the end, you should have 1193 parties."""

# Make sure you are using the same /web/stringofdigits/... for each page
# This is to prevent the archive from accessing later copies of the same page
# If you are off by a just a few, that can be the archive misbehaving
len(link_list) == 1193

"""In case we need to restart the notebook, we should save this information to a file.  There are many ways you could do this; here's one using `dill`."""

dill.dump(link_list, open('nysd-links.pkd', 'wb'))

"""To restore the list, we can just load it from the file.  When the notebook is restarted, you can skip the code above and just run this command."""

link_list = dill.load(open('nysd-links.pkd', 'rb'))

print(len(link_list))
print(link_list[0])
print(link_list[-1])

"""### Question 1: In which month did most of the parties occur? (10 p)
### Question 2: What is the overall trend of parties from 2007 to 2014? (10 p)
Use visualizations to answer the two questions above. Ensure that you interpret your plots thoroughly.
"""

## Code cell generated with Google Gemini
df = pd.DataFrame(link_list, columns=['url', 'date'])
df['month'] = df['date'].dt.month

# Group by month and count the number of parties in each month
monthly_counts = df.groupby('month').size()

print(monthly_counts)

plt.bar(monthly_counts.index, monthly_counts.values)
plt.xlabel("Month")
plt.ylabel("Number of Parties")
plt.title("Number of NYSD Parties by Month")

plt.show()

## Code cell generated with Google Gemini

df['year'] = df['date'].dt.year

## Number of parties per year
yearly_counts = df.groupby('year').size()

plt.scatter(yearly_counts.index, yearly_counts.values)
z = np.polyfit(yearly_counts.index, yearly_counts.values, 1)
p = np.poly1d(z)
plt.plot(yearly_counts.index, p(yearly_counts.index), "r--")

plt.xlabel("Year")
plt.ylabel("Number of Parties")
plt.title("Trend of NYSD Parties from 2007 to 2014")

plt.show()

"""## Phase Two

In this phase, we concentrate on getting the names out of captions for a given page.  We'll start with [the benefit cocktails and dinner](https://web.archive.org/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures/2015/celebrating-the-neighborhood) for [Lenox Hill Neighborhood House](http://www.lenoxhill.org/), a neighborhood organization for the East Side.

Take a look at that page.  Note that some of the text on the page is captions, but others are descriptions of the event.  Determine how to select only the captions.
"""

url = "https://web.archive.org/web/20151114014941/http://www.newyorksocialdiary.com/party-pictures/2015/celebrating-the-neighborhood"
page = requests.get(url)
soup = BeautifulSoup(page.text, "lxml")

captions = soup.select("div.photocaption")

"""By our count, there are about 110.  But if you're off by a couple, you're probably okay."""

# These are for the specific party referenced in the text
abs(len(captions) - 110) < 5

"""Let's encapsulate this in a function.  As with the links pages, we want to avoid downloading a given page the next time we need to run the notebook.  While we could save the files by hand, as we did before, a checkpoint library like [ediblepickle](https://pypi.python.org/pypi/ediblepickle/1.1.3) can handle this for you.  (Note, though, that you may not want to enable this until you are sure that your function is working.)

You should also keep in mind that HTTP requests fail occasionally, for transient reasons.  You should plan how to detect and react to these failures.   The [retrying module](https://pypi.python.org/pypi/retrying) is one way to deal with this.
"""

def get_captions(path):
  url = f"https://web.archive.org/{path}"
  page = requests.get(url)
  soup = BeautifulSoup(page.text, "lxml")
  return soup.select("div.photocaption")

"""This should get the same captions as before."""

# This cell is expecting get_captions to return a list of the captions themselves
# Other routes to a solution might need to adjust this cell a bit
captions == get_captions("/web/20150913224145/http://www.newyorksocialdiary.com/party-pictures/2015/celebrating-the-neighborhood")

"""Now that we have some sample captions, let's start parsing names out of those captions.  There are many ways of going about this, and we leave the details up to you.  Some issues to consider:

  1. Some captions are not useful: they contain long narrative texts that explain the event.  Try to find some heuristic rules to separate captions that are a list of names from those that are not.  A few heuristics include:
    - look for sentences (which have verbs) and as opposed to lists of nouns. For example, [`nltk` does part of speech tagging](http://www.nltk.org/book/ch05.html) but it is a little slow. There may also be heuristics that accomplish the same thing.
    - Similarly, spaCy's [entity recognition](https://spacy.io/docs/usage/entity-recognition) could be useful here.
    - Look for commonly repeated threads (e.g. you might end up picking up the photo credits or people such as "a friend").
    - Long captions are often not lists of people.  The cutoff is subjective, but for grading purposes, *set that cutoff at 250 characters*.
  2. You will want to separate the captions based on various forms of punctuation.  Try using `re.split`, which is more sophisticated than `string.split`. **Note**: Use regex exclusively for name parsing.
  3. This site is pretty formal and likes to say things like "Mayor Michael Bloomberg" after his election but "Michael Bloomberg" before his election.  Can you find other titles that are being used?  They should probably be filtered out because they ultimately refer to the same person: "Michael Bloomberg."
  4. There is a special case you might find where couples are written as eg. "John and Mary Smith". You will need to write some extra logic to make sure this properly parses to two names: "John Smith" and "Mary Smith".
  5. When parsing names from captions, it can help to look at your output frequently and address the problems that you see coming up, iterating until you have a list that looks reasonable. Because we can only asymptotically approach perfect identification and entity matching, we have to stop somewhere.
  
**Questions worth considering:**
  1. Who is Patrick McMullan and should he be included in the results? How would you address this?
  2. What else could you do to improve the quality of the graph's information?
"""

### Configure spaCy to use expanded person entities
### To process titles (Mr., Mrs., Dr., etc.)
### See https://spacy.io/usage/rule-based-matching#models-rules
@Language.component("expand_person_entities")
def expand_person_entities(doc):
    new_ents = []
    for ent in doc.ents:
        if ent.label_ == "PERSON" and ent.start != 0:
            prev_token = doc[ent.start - 1]
            if prev_token.text in ("Dr", "Dr.", "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms."):
                new_ent = Span(doc, ent.start - 1, ent.end, label=ent.label)
                new_ents.append(new_ent)
            else:
                new_ents.append(ent)
        else:
            new_ents.append(ent)
    doc.ents = new_ents
    return doc

nlp = spacy.load("en_core_web_lg")
##nlp.add_pipe("expand_person_entities", after="ner")


test = "John and Jane Smith"
test2 = "Jean Shafiroff and Mary Mahoney"
def split_married_couple(text):
  groups = re.split(r',\s*(and|with|&)\s*', text)
  names = []
  for group in groups:
    match = re.search(r'(.*) (?:and|&) (.*) (\w+)', group)
    if match and len(match.group(1).split()) == 1:  ### Only repair names if first name in pair is just first name
      first_name1 = match.group(1)
      first_name2 = match.group(2)
      last_name = match.group(3)
      names.extend([f"{first_name1} {last_name}", f"{first_name2} {last_name}"])
    else:
      names.append(group)
  return ", ".join(names)


def clean_name(name):
    name = str(name)
    name = name.strip()
    name = re.sub("'s$", "", name)    ### remove trailing 's
    name = re.sub(r"\s+", " ", name)  ### replace sequences of multiple whitespaces with a single space char
    name = name.strip("\\")
    
    return name


def extract_names_spacy(caption):
  """
  Extracts names from a caption using spaCy.

  Args:
    caption: The caption text.

  Returns:
    A list of names extracted from the caption.
  """

 
  doc = nlp(split_married_couple(caption))
  names = [clean_name(ent) for ent in doc.ents if ent.label_ == "PERSON"]

  return names


### Raw caption text
##[caption.text for caption in captions]

### Names parsed from caption text
##list(map(lambda caption: extract_names_spacy(caption.text), captions))


"""Once you feel that your algorithm is working well on these captions, parse all of the captions and extract all the names mentioned.

Now, run this sort of test on a few other pages.  You will probably find that other pages have a slightly different HTML structure, as well as new captions that trip up your caption parser.  But don't worry if the parser isn't perfect -- just try to get the easy cases.

Once you are satisfied that your caption scraper and parser are working, run this for all of the pages.  If you haven't implemented some caching of the captions, you probably want to do this first.
"""

# all_captions = []
# for link in link_list:
#   captions = get_captions(link[0])
#   all_captions.extend(captions)
#   time.sleep(10)

# print(all_captions)

def get_captions_file(webpage):
  soup = BeautifulSoup(webpage, "lxml")
  return soup.select("div.photocaption")

all_captions = []
for file in glob.glob("./nysd/*"):
    with open(file, "r", encoding='utf-8', errors='ignore') as f:
        webpage = f.read()
        captions = get_captions_file(webpage)
        all_captions.extend(captions)


# import sys
# sys.setrecursionlimit(100000)
# dill.dump(all_captions, open('all_captions.pkd', 'wb'))

# all_captions = dill.load(open('all_captions.pkd', 'rb'))

print(len(all_captions))

cleaned_captions = list(map(lambda caption: extract_names_spacy(caption.text), all_captions))

len(cleaned_captions)
#71316

unique_names = set([name for names in cleaned_captions for name in names])

len(unique_names)
#151736

with open("names.txt", "w") as f:
    f.writelines([f"{str(name)}\n" for name in sorted(list(unique_names))])

list(unique_names)[:100]

##[name for name in list(unique_names) if len(name.split()) == 1]

# Scraping all of the pages could take 10 minutes to an hour

"""## Phase 3: Graph Analysis

For the remaining analysis, we think of the problem in terms of a
[network](http://en.wikipedia.org/wiki/Computer_network) or a
[graph](https://en.wikipedia.org/wiki/Graph_%28discrete_mathematics%29).  Any time a pair of people appear in a photo together, that is considered a link.  It is an example of  an **undirected weighted graph**. We recommend using python's [`networkx`](https://networkx.github.io/) library.
"""

"""All in all, you should end up with over 100,000 captions and more than 110,000 names, connected in about 200,000 pairs.

## Question 3: Graph EDA (20 p)

- Use parsed names to create the undirected weighted network and visualize it (5 p)
- Report the number of nodes and edges (5 p)
- What is the diameter of this graph? (5 p)
- What is the average clustering coeff of the graph? How you interpret this number? (5 p)

## Question 4: Graph properties (20 p)

What real-world graph properties does this graph exhibit? Please show your work and interpret your answer. Does the result make sense given the nature of the graph?

## Question 4: Who are the most photogenic persons? (10 p)

The simplest question to ask is "who is the most popular"?  The easiest way to answer this question is to look at how many connections everyone has.  Return the top 100 people and their degree.  Remember that if an edge of the graph has weight 2, it counts for 2 in the degree.

**Checkpoint:** Some aggregate stats on the solution

    "count": 100.0
    "mean": 189.92
    "std": 87.8053034454
    "min": 124.0
    "25%": 138.0
    "50%": 157.0
    "75%": 195.0
    "max": 666.0
"""

G = nx.MultiGraph()
pairs = []
for caption in cleaned_captions:
    a = itertools.combinations(caption, 2)
    pairs.extend(a)
len(pairs)

G.add_edges_from(pairs)

degrees = sorted(G.degree, key = lambda x: (-x[1]))

print(degrees[:100])
print(degrees[-100:])

"""## Question 5: Centrality analysis (20 p)

Use eccentricity centrality, closeness centrality, betweenness centrality, prestige, and PageRank to identify the top 10 individuals with the highest centrality for each measure. How do you interpret the results?

Use 0.85 as the damping parameter for page rank, so that there is a 15% chance of jumping to another vertex at random.

**Checkpoint:** Some aggregate stats on the solution for pagerank

    "count": 100.0
    "mean": 0.0001841088
    "std": 0.0000758068
    "min": 0.0001238355
    "25%": 0.0001415028
    "50%": 0.0001616183
    "75%": 0.0001972663
    "max": 0.0006085816

## Question 6: best_friends (10 p)

Another interesting question is who tend to co-occur with each other.  Give us the 100 edges with the highest weights.

Google these people and see what their connection is.  Can we use this to detect instances of infidelity?

**Checkpoint:** Some aggregate stats on the solution

    "count": 100.0
    "mean": 25.84
    "std": 16.0395470855
    "min": 14.0
    "25%": 16.0
    "50%": 19.0
    "75%": 29.25
    "max": 109.0
"""

#temple form for the answer
best_friends = [(('Michael Kennedy', 'Eleanora Kennedy'), 41)] * 100

