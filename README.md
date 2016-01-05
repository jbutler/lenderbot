# lenderbot
Don't be a scrub and manage your own LendingClub account. Retire and drink mimosas on the beach while lenderbot does this crap for you.

[![Build Status](https://travis-ci.org/jbutler/lenderbot.svg?branch=master)](https://travis-ci.org/jbutler/lenderbot)

## Dependencies
* Python 3
* pyparsing
* requests

## Installation
### Linux
Set up a virtualenv:

`virtualenv -p python3 <virtual environment>`

Sync down the code, `source` the newly created virtual env, and pip install:

`source <virtual environment>/bin/activate`

`pip install -r requirements.txt`

`pip install /<path>/<to>/<lenderbot>`

Make sure to install the package in Development Mode if you wish to make code changes:

`pip install -e /<path>/<to>/<lenderbot>`

### Windows
You'll figure it out

## Command Line Options
Run `python main.py --help` for the most up to date list of command line options. Currently supported options include:
* `-a`, `--autoMode`: Enter auto-mode. Check notes, fund account, and invest in available loans.
* `-f`, `--fundAccount`: Transfer funds to meet minimum account balance.
* `-i`, `--invest`: Invest spare cash in available loans passing filters.
* `-l`, `--findLate`: Find notes that are no longer current and notify user.
* `-p`, `--productionMode`: Enter production mode. Required to invest or transfer funds.
* `-s`, `--summarizeNotes`: Provide status summary of all held notes.
* `-t`, `--testFilters`: Test loan filters by applying them to all loans currently listed.

## Configuration
Put the config files in your home dir under `~/.lenderbot/`. See config in `example_config` for examples.

### Account configuration
There are five fields of interest in the account configuration json file (config.json):
* `iid` - This is your account number. Find it on the account summary page
* `auth` - This is an authentication string used to communicate with LendingClub. You will need access to the API. Find this under "API Settings" on the "Settings" page.
* `orderamnt` - This is the integer amount to invest in loans that pass your filters. Must be a multiple of $25.
* `min_balance` - This is your desired minimum account balance. `lenderbot` will initiate a transfer when your available cash plus the sum of any pending transfers is less than this amount. Keep in mind that money transfers take 4 business days to complete.
* `email` - Email address to send purchase notification to

### Filters
This is where `lenderbot` kicks ass. It includes a parser which allows you to write arbitrarily complex filters using multiple loan keys and operators. The available loan keys are defined as part of the LendingClub API. You can find these on the developer section of their webpage.

The filter parser supports (in)equalities as well as basic math functions. Make sure it's a boolean filter.

Available operators: `+, -, *, /, %, >, >=, <, <=, ==, !=`

#### Filter Syntax
Just look at the examples and `example_config/rules.json`

##### Basic Example
`{term} == 36`

This one illustrates how to perform key lookups. Toss anything that's not a 36 month note. Nobody's got time to wait around for 5 years.

##### More Complicated Example
`{annualInc} * 0.3 > {loanAmount}`

Income discrimination at its finest.
