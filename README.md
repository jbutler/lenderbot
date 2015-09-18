# auto-investor
Don't waste your time managing your LendingClub account. Set up a set of filters and let `auto-investor` put your spare cash to work.

[![Build Status](https://travis-ci.org/jbutler/auto-investor.svg?branch=master)](https://travis-ci.org/jbutler/auto-investor)

## Requirements
* Python 3
* pyparsing
* requests

## Installation
While this package isn't hosted on PyPI, I have included a setup.py script. I'd recommend installing this in a virtual environment instead of cluttering up your system python installation. From your virtualenv, you may install using `pip` or any other package manager relying on `distutils`.

`pip install /<path>/<to>/<auto-investor>`

Make sure to install the package in Development Mode if you wish to make code changes:

`pip install -e /<path>/<to>/<auto-investor>`

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
Account configuration and lending criteria are two pieces that you'll need/want to tweak. There are separate config files for each.

### Account configuration
There are five fields of interest in the account configuration json file (config.json):
* `iid` - This is your account number. Find it on the account summary page
* `auth` - This is an authentication string used to communicate with LendingClub. You will need access to the API. Find this under "API Settings" on the "Settings" page.
* `orderamnt` - This is the integer amount to invest in loans that pass your filters. Must be a multiple of $25.
* `min_balance` - This is your desired minimum account balance. auto-investor will initiate a transfer when your available cash plus the sum of any pending transfers is less than this amount. Keep in mind that money transfers take 4 business days to complete.
* `email` - Email address to send purchase notification to

### Filters
This is where `auto-investor` shines. It includes a parser which allows you to write arbitrarily complex filters using multiple loan keys and operators. The available loan keys are defined as part of the LendingClub API. You can find these on the developer section of their webpage.

The filter parser supports (in)equalities as well as basic math functions. The return value of a filter must be a boolean!

Available operators: `+, -, *, /, %, >, >=, <, <=, ==, !=`

#### Filter Syntax
It's easiest to illustrate the syntax with some examples. We'll start with a basic one and go from there.

##### Basic Example
`{term} == 36`

This one is pretty self explanatory, but illustrates how to perform key lookups. `{term}` represents the loan term of whatever loan this filter is applied to. It is replaced at runtime with the appropriate value (only 36 and 60 month loans are available on LendingClub). This filter will restrict your investments to 36 month loans. All others will be discarded.

##### More Complicated Example
`{annualInc} * 0.3 > {loanAmount}`

This filter looks at the borrowers income to decide if the loan amount is appropriate. Specifically, the loan amount must not exceed 30% of their annual income.

#### Filter Types
There are two types of filters available for use. The above examples are `BasicFilters`. However, it may make more logical sense to define a filter such that loans are discarded when they PASS a filter instead of when they FAIL. These filters are defined as `ExclusionFilters`. While `ExclusionFilters` do not add any flexibility, they're there for you to use. For example, you may find it more intuitive to toss out all loans originating from CA and NJ as `{addrState} == CA` and `{addrState} == NJ` instead of using a `BasicFilter` and saying `{addrState} != CA` and `{addrState] != NJ`. Tomato, tomato. Wait...

#### Filter format
Now that you're ready to come up with all your badass filters, take a look at rules_template.json for the format.

