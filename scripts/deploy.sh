#!/bin/bash
# set -u

function confirm {
  read -p "Are you sure you want to deploy to prod? " -n 1 -r
  echo
  if ! [[ $REPLY =~ ^[Yy]$ ]]
  then
      echo "Cancelled"
      exit 1
  fi
}

case "${1}" in
  dev)
    pipenv run sceptre --merge-vars launch dev/config.yaml -y ;;
  prod)
    confirm
    pipenv run sceptre --merge-vars launch prod/config.yaml -y ;;
  *)
    echo "./deploy.sh <dev | prod>"; exit 1 ;;
esac
