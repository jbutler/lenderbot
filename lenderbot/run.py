#!/usr/bin/env python3

import argparse
from lenderbot import lenderbot

def parse_args():
    parser = argparse.ArgumentParser(description='Autonomous LendingClub account management.')
    parser.add_argument('-a', '--autoMode',
                        action='store_true',
                        help='Enter auto-mode. Check notes, fund account, and invest in available loans.')
    parser.add_argument('-c', '--configDir',
                        action='store',
                        help='Specify a non-default configuration directory.')
    parser.add_argument('-f', '--fundAccount',
                        action='store_true',
                        help='Transfer funds to meet minimum account balance.')
    parser.add_argument('-i', '--invest',
                        action='store_true',
                        help='Invest spare cash in available loans passing filters.')
    parser.add_argument('-l', '--findLate',
                        action='store_true',
                        help='Find notes that are no longer current and notify user.')
    parser.add_argument('-p', '--productionMode',
                        action='store_true',
                        help='Enter production mode. Required to invest or transfer funds.')
    parser.add_argument('-s', '--summarizeNotes',
                        action='store_true',
                        help='Provide status summary of all held notes.')
    parser.add_argument('-t', '--testFilters',
                        action='store_true',
                        help='Test loan filters by applying them to all loans currently listed. Exit once complete.')
    return parser.parse_args()

def main():
    args = parse_args()
    lb = lenderbot.LenderBot(config_dir=args.configDir, production_mode=args.productionMode)
    if args.autoMode:
        lb.run()
    if args.fundAccount:
        lb.fund_account()
    if args.invest:
        lb.invest()
    if args.findLate:
        lb.find_late_notes()
    if args.summarizeNotes:
        lb.note_summary()
    if args.testFilters:
        lb.test_filters()

if __name__ == '__main__':
    main()
