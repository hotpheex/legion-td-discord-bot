# Legion TD Tournament Discord Bot

Serverless Discord bot to help manage [Legion TD 2 Nova Cup tournaments](https://beta.legiontd2.com/esports/) in the [Tournament Discord Server](https://discord.gg/GJVRgHrGZV)
Runs on Lambda functions exposed via API Gateway

```
.
├── cloudformation <= AWS infrastructure as code
├── scripts        <= CI scripts
└── src
    ├── handler    <= Handles request & invokes respective lambda
    ├── checkin    <= Checkin before tournament
    ├── manage     <= Tournament organiser commands
    ├── results    <= Report match results
    ├── libs       <= Shared classes included in all functions
    └── tests
```

Update Discord slash commands:

```
python3 slash_cmds.py <dev | prod>
```

Deploy changes:

```
./deploy.sh <dev | prod>
```
