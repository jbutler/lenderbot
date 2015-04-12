# auto-investor
Python library interfacing with LendingClub. Run this as a cronjob to automatically invest in notes that meet your investment criteria.

## Requirements
* Python 3
* requests

## Configuration
Configuration is done in 'rules.json'. This name is somewhat of a misnomer since it contains account configuration info in addition to just filter definitions.

### Account configuration
There are four fields of interest in the "config" section:
* iid - This is your account number. Find it on the account summary page
* auth - This is an authentication string used to communicate with LendingClub. You will need access to the API. Find this under "API Settings" on the "Settings" page.
* orderamnt - This is the integer amount to invest in loans that pass your filters. Must be a multiple of $25.
* email - Email address to send purchase notification to

### Filters
Filters are defined in the "exclusions" section. Filters are defined as a key, an operator, and a comparison value. Loans are discarded when they PASS the filter. In other words, you add failure conditions. This was done because I was lazy and didn't want to devise a clever method to encode inclusion filters with sufficient flexibility. It's much easier to write two filters to discard loans for vacations and auto purchases than it is to write a filter to include loans for debt consolidation, home improvement, medical bills, and moving expenses.

Take a look at rules_template.json for an idea of how to write up filters.
