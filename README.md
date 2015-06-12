# auto-investor
Python library interfacing with LendingClub. Run this as a cronjob to automatically invest in notes that meet your investment criteria.

[![Build Status](https://travis-ci.org/jbutler/auto-investor.svg?branch=master)](https://travis-ci.org/jbutler/auto-investor)

## Requirements
* Python 3
* requests

## Configuration
Account configuration and lending criteria are two pieces that you'll need/want to tweak. There are separate config files for each.

### Account configuration
There are five fields of interest in the account configuration json file (config.json):
* iid - This is your account number. Find it on the account summary page
* auth - This is an authentication string used to communicate with LendingClub. You will need access to the API. Find this under "API Settings" on the "Settings" page.
* orderamnt - This is the integer amount to invest in loans that pass your filters. Must be a multiple of $25.
* min_balance - This is your desired minimum account balance. auto-investor will initiate a transfer when your available cash plus the sum of any pending transfers is less than this amount. Keep in mind that money transfers take 4 business days to complete.
* email - Email address to send purchase notification to

### Filters
Filters are defined in the "exclusions" section of rules.json. Filters are defined as a key, an operator, and a comparison value. Loans are discarded when they PASS the filter. In other words, you add failure conditions.

Take a look at rules_template.json for an idea of how to write up filters.
