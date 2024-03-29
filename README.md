# Legion TD Tournament Discord Bot

Serverless Discord bot to help manage [Legion TD 2 Nova Cup tournaments](https://beta.legiontd2.com/esports/#about) in the [Tournament Discord Server](https://discord.gg/GJVRgHrGZV)
Runs on Lambda functions exposed via API Gateway written in Troposphere and deployed with Sceptre.

```
.
├── cloudformation <= AWS infrastructure as code
├── scripts        <= CI scripts
└── src
    ├── handler    <= Handles initial request & invokes respective lambda
    ├── checkin    <= Checkin before tournament
    ├── manage     <= Tournament organiser commands
    ├── results    <= Report match results
    ├── libs       <= Shared classes included in all functions
    └── tests
```

Update Discord slash commands:

```
scripts/slash_cmds.py <dev | prod>
```

Deploy changes:

Make sure dependencies are installed: `pipenv install`

```
scripts/deploy.sh <dev | prod>
```
