#!/bin/bash

# Runs python script within virtualenv
# Use this for your cron jobs if you require a virtual environment
#
# Example:
# ./run_investor.sh /home/user/virtual_env main.py
#

cd `dirname $0`
source $1/bin/activate
python "${@:2}"

