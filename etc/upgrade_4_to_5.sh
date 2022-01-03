#!/usr/bin/env bash

if [[ -z $1 || $1 == -h || $1 == --help || $# != 1 || ! -d $1 ]]; then
  echo 'Usage: $0 DIRNAME'
  echo 'where DIRNAME is the path containing code to be updated'
  exit 1
fi

DIR=$1

grep -R 'import argparse' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/import argparse/from dewi_core.appcontext import ApplicationContext\nfrom dewi_core.optioncontext import OptionContext/'

grep -R 'def run(self, args: argparse.Namespace)' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/def run.self, args: argparse.Namespace./def run(self, ctx: ApplicationContext)/'

grep -R 'def run(self, args: argparse.Namespace)' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/def run.self, args: argparse.Namespace./def run(self, ctx: ApplicationContext)/'

grep -R 'def register_arguments(self' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/def register_arguments.self, .*\)/@staticmethod\n    def register_arguments(c: OptionContext)/'

grep -R 'parser.add_argument(.-' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/parser.add_argument/c.add_option/'


grep -R 'parser.add_argument(' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/parser.add_argument\($/c.add_option(/'

grep -R ', action=.store_true.' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/action=.store_true./is_flag=True/'


grep -R 'SealableNode' $DIR | cut -f1 -d: | uniq |
  xargs sed -ri 's/SealableNode/Node/g'
