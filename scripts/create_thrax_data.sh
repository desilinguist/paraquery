#!/bin/bash

if [ $# -ne 3 ]; then
  echo "usage: create_thrax_data.sh <fr> <en> <alignment>"
  exit
fi

paste -d'|' $1 $2 $3 | sed 's/|/ ||| /g' 
