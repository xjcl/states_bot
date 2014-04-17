states\_bot
=========

A reddit bot that detects when American state abbreviations are used in a comment and writes out the full state name.

Usage
-----

Just run `python states_bot.py`

The bot is already looped within that file, so no need for a cronjob.

Configuration
-------------

The configuration file is "settings.json" and should be copied from "settings.json.default". It should contain the reddit bot username (without /u/), password, the subreddits to check and comment in, an approperate useragent (a name under which the bot communicates with reddit - see default file for an example).

Dependencies
------------

states\_bot depends on the following external libraries:

* [praw](https://github.com/praw-dev/praw/) - Reddit library

Some parts of the code are copied from [groompbot](https://github.com/AndrewNeo/groompbot).

License
-------

states\_bot is free to use under the MIT License.

