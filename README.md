# lenderbot
Automated tool for managing your LendingClub account. Unlike other tools which serve similar purposes, lenderbot supports advanced filtering capabilities and has been optimized to ensure you never miss out on the loans you're interested in.

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

### Windows
You're on your own for the virtualenv setup, but otherwise should be the same

## Command Line Options
Once installed, you can invoke the lenderbot module via the command line with `python3 -m lenderbot.run`. Currently supported options include:
* `-a`, `--autoMode`: Enter auto-mode. Check notes, fund account, and invest in available loans.
* `-c`, `--configDir`: Specify a non-default configuration directory.
* `-f`, `--fundAccount`: Transfer funds to meet minimum account balance.
* `-i`, `--invest`: Invest spare cash in available loans passing filters.
* `-l`, `--findLate`: Find notes that are no longer current and notify user.
* `-p`, `--productionMode`: Enter production mode. Required to invest or transfer funds.
* `-s`, `--summarizeNotes`: Provide status summary of all held notes.
* `-t`, `--testFilters`: Test loan filters by applying them to all loans currently listed.

## Configuration
Put the config files in your home dir under `~/.lenderbot/`. See config in `example_config` for examples. Alternatively place these whereever you want and pass the `--configDir` option.

### Account configuration
There are several fields of interest in the account configuration json file (config.json):
* `name` - Human readable string to identify the account.
* `iid` - This is your account number. Find it on the account summary page
* `auth` - This is an authentication string used to communicate with LendingClub. You will need access to the API. Find this under "API Settings" on the "Settings" page.
* `orderamnt` - This is the integer amount to invest in loans that pass your filters. Must be a multiple of $25.
* `min_balance` - This is your desired minimum account balance. `lenderbot` will initiate a transfer when your available cash plus the sum of any pending transfers is less than this amount. Keep in mind that money transfers take 4 business days to complete.
* `email` - Email address to send purchase notification to
* `portfolio` - Format string to place loans into specific portfolios. Use any modifiers used in the `datetime` module.

### Filters
This is where `lenderbot` kicks ass. It includes a parser which allows you to write arbitrarily complex filters using multiple loan keys and operators. The available loan keys are defined as part of the LendingClub API. You can find these on the developer section of their webpage.

The filter parser supports (in)equalities as well as basic math functions. Make sure it's a boolean filter.

Available operators: `+, -, *, /, %, >, >=, <, <=, ==, !=`

#### Filter Syntax
Look at `example_config/filters.json`
