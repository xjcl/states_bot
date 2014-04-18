"""Partially based on Groompbot by /u/AndrewNeo
   
   Not really copied but come on how should I
   can't start with an empty page or whatever."""

import sys
import logging
import json
import praw
import time
import logging

#---------------------------------
# misc.
#---------------------------------

def loadSettings():
    """Load settings from file."""
    try:
        settingsFile = open("settings.json", "r")
    except IOError:
        logging.exception("Error opening settings.json.")
        sys.exit(1)
    try:
        settings = json.load(settingsFile)
        settingsFile.close()
    except ValueError:
        logging.exception("Error parsing settings.json.")
        sys.exit(1)
    
    # Check integrity
    for variable in ["reddit_username", "reddit_password", "reddit_ua", "subreddits"]:
        if (len(settings[variable]) == 0):
            logging.critical(variable+" not set.")
            sys.exit(1)
    return settings



def find_all(a_str, sub):
    """Find all instances of a substring (no overlaps).
        Source: http://stackoverflow.com/questions/4664850/
            find-all-occurrences-of-a-substring-in-python"""
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub)





#---------------------------------
# text/comment/pm-processing and -output
#---------------------------------

def get_states_dict():
    return {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    #"LA": "Louisiana (or Los Angeles)", # gee even after adding
        # the disclaimer people still downvote in masses -> don't use!
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    #"NY": "New York", # too commonly known
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virgina",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    # other
    #"DC": "District of Columbia (~~State~~ Federal District)",
    #"AS": "American Samoa (~~State~~ Territory)",
    #"GU": "Guam (~~State~~ Territory)",
    #"MP": "Northern Mariana Islands (~~State~~ Insular area)",
    #"PR": "Puerto Rico (~~State~~ Insular area)",
    #"VI": "Virgin Islands (~~State~~ Territory)",
    #"UM": "U.S. Minor Outlying Islands (~~State~~ Insular Areas)",
    #"FM": "Federated States of Micronesia (~~State~~ Freely associated state)",
    #"MH": "Marshall Islands (~~State~~ Freely associated state)",
    #"PW": "Palau (~~State~~ Freely associated state)"
    # source: http://en.wikipedia.org/wiki/List_of_U.S._state_abbreviations
    # last checked: 2014-04-14
    }

def format_message(states):
    """Format a list of states into a message formatted for reddit."""
    logging.info("Formatting message.")
    assert len(states)>0 # already checked earlier if implemented correctly
    states_dict = get_states_dict()
    lmsg = ""
    lmsg += ("I found some U.S. state abbreviations in your comment. Let me"+
        " write them out for our international redditors.")
    lmsg += "\n\n| ST | State |"
    lmsg += "\n|:-----|:------|"
    for st in states:
        state = states_dict[st]
        wikilink = "http://en.wikipedia.org/wiki/" + state.replace(" ", "_")
        lmsg += "\n" + st + " | [" + states_dict[st] + "](" + wikilink + ")"
    #lmsg += ("\n\n~~--------------------------------------------------~~"+
    #lmsg += ("\n\n^I ^am ^a ^bot.")# | [About](...) | [Source]"+
    #"(https://github.com/xjcl/...)")
    lmsg += ("\n\n^(I am a bot."+
        " I will respond to the syntax 'in ST' and 'from ST'."+
        " /u/xjcl made me.)")
    return lmsg


def check_for_states(comment):
    """Currently looks for 'in ST', 'In ST', 'from ST' and 'From ST'.
        Ignores double and ignores comments that mention the full state name
        along with the abbreviation."""
    states = []
    states_dict = get_states_dict()
    for pattern in ["in ", "In ", "from ", "From "]:
        for index in find_all(comment.body, pattern):
            try:
                # This next line: 'thing in AL. thing' -> 'AL'
                state_candidate = comment.body[
                    index+len(pattern):index+len(pattern)+2]
                # after_char weeds out 'in PAY', but keeps 'In PA,'
                after_char = comment.body[index+len(pattern)+2]
                punctuation = [" ", ",", ".", ";"]
                if state_candidate in states_dict and after_char in punctuation:
                    # ignore if full state name is mentioned as well
                    if states_dict[state_candidate] not in comment.body:
                        states.append(state_candidate)
            except IndexError:
                pass # message ends in "... I am in ." or something
    states = list(set(states)) # remove doubles
    states.sort()
    return states





#---------------------------------
# reddit-specific
#---------------------------------

def getReddit(settings):
    """Get a reference to Reddit."""
    r = praw.Reddit(user_agent=settings["reddit_ua"])
    try:
        r.login(settings["reddit_username"], settings["reddit_password"])
    except:
        logging.exception("Error logging into Reddit.")
        sys.exit(1)
    return r
    

def delete_unpopular_coms(reddit, username, threshold=-1):
    logging.info("Deleting comments with a score less than "+str(threshold)+".")
    for comment in reddit.get_redditor(username).get_comments():
        if comment.score < threshold:
            logging.info("Deleting '"+comment.id+"'.")
            logging.debug(comment.body)
            comment.delete()


def listen(reddit, answered_coms, subreddits=["all"], limit=10000):
    """Check newest comments for bot calls."""
    subreddit = "+".join(subreddits)
    logging.debug("Searching through these subreddits: "+subreddit)
    
    # the only way to reverse the list would be to store it locally -
    # which would be painful.
    # Alternatively use get_new() here. Difference to get_comments() unclear.
    for comment in reddit.get_subreddit(subreddit).get_comments(limit=limit):
        if comment.id not in answered_coms:
            states = check_for_states(comment)
            if states:
                try:
                    logging.info("Responding to '"+str(comment.author)+"' ("+comment.id+").")
                    comment.reply(format_message(states))
                    answered_coms.append(comment.id)
                    logging.info("Comment succeeded!")
                except praw.errors.RateLimitExceeded:
                    logging.error("Comment failed (RateLimitExceeded)."+
                        " You need more karma in that subreddit.")
                #except requests.exceptions.HTTPError, e:
                #except urllib2.HTTPError, e: # shit doesn't work :(
                #    if e.code not in [429, 500, 502, 503, 504]:
                #        raise
                #    logging.error("Reddit is down (error "+e.code+").")
                except Exception as e:
                    # Used here so ids saved in answered_coms will still
                    # be written to file.
                    logging.error("Unexpected error while replying to comment:"+str(e))
    logging.info("Receiving comment-ids of answered comments.")
    return answered_coms




#---------------------------------
# main
#---------------------------------

def runBot():
    """Start a run of the bot."""
    logging.info("Starting bot.")
    settings = loadSettings()
        
    logging.info("Logging into Reddit.")
    reddit = getReddit(settings)
        
    """Search comments and post"""
    """answered_coms prevents responding to the
       same comment twice"""
    try:
        of = open('answered_coms.json', 'r')
        answered_coms = json.load(of)
        of.close()
    except IOError:
        logging.info("answered_coms.json doesn't exits. "
            +" Using empty list instead.")
        answered_coms = []
    except ValueError:
        logging.info("answered_coms.json couldn't be parsed. "
            +" Using empty list instead.")
        answered_coms = []
        
    while True:
        logging.info("Looking for new comments.")
        try:
            answered_coms = listen(reddit, answered_coms, settings["subreddits"], 10000)
            delete_unpopular_coms(reddit, settings["reddit_username"], threshold=-1)
        except Exception as e: #HTTPError
            logging.error("Error while listening to latest reddit comments:"+str(e))
        logging.info("Writing comment-ids to file.")
        sf = open('answered_coms.json', 'w')
        json.dump(answered_coms, sf)
        sf.close()
        logging.info("Done!")
        time.sleep(20)



if __name__ == "__main__":
    # print to console
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    # print to log file
    #logging.basicConfig(filename='log.log',level=logging.DEBUG)
    runBot()
    logging.shutdown()
    

