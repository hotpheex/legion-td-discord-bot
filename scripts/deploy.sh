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

function deploy_dev {
  echo "Deploying to dev..."

  cd cloudformation
  pipenv run python3 template.py && cat template.yaml | cfn-lint && docker run --rm -v "`pwd`:/cwd" \
      -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
      -e AWS_DEFAULT_REGION=ap-southeast-2 \
      realestate/stackup:latest \
          legion-td-discord-bot-development up \
            -t template.yaml \
            --tags tags.json \
            -o EnableDebug="true" \
            -o DiscordApplicationId="1058247991867219990" \
            -o DiscordPublicKey="f5f2ad3d28b06fb464d8e9ee6d3667e149392467341759d4811ee6996d2e918a" \
            -o GoogleApiKey="${GOOGLE_API_KEY}" \
            -o GoogleSheetId="${GOOGLE_SHEET_ID_DEV}" \
            -o ChallongeApiKey="${CHALLONGE_API_KEY}" \
            -o AlertWebhook="${ALERT_WEBHOOK}"
  cd ..
}

function deploy_prod {
  echo "Deploying to prod..."

  cd cloudformation
  pipenv run python3 template.py && cat template.yaml | cfn-lint && docker run --rm -v "`pwd`:/cwd" \
      -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
      -e AWS_DEFAULT_REGION=ap-southeast-2 \
      realestate/stackup:latest \
          legion-td-discord-bot up \
            -t template.yaml \
            --tags tags.json \
            -o DiscordApplicationId="1015271519414399038" \
            -o DiscordPublicKey="42be1d3d4136ed14b3a46a60bb11fe92c73c0d84be9337f3e6f11e21edf6e75d" \
            -o GoogleApiKey="${GOOGLE_API_KEY}" \
            -o GoogleSheetId="${GOOGLE_SHEET_ID_PROD}" \
            -o ChallongeApiKey="${CHALLONGE_API_KEY}" \
            -o AlertWebhook="${ALERT_WEBHOOK}"
  cd ..
}

case "${1}" in
  dev)
    deploy_dev ;;
  prod)
    deploy_prod ;;
  *)
    echo "./deploy.sh <dev | prod>"; exit 1 ;;
esac
