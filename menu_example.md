https://discord.com/developers/docs/interactions/message-components#action-rows

```
    response = requests.patch(
        f"https://discord.com/api/webhooks/{APPLICATION_ID}/{event['token']}/messages/@original",
        json={
            "content": "testing",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 3,
                            "custom_id": "tournament_select",
                            "options": [
                                {
                                    "label": "Tourn1",
                                    "value": "1",
                                    "description": "description",
                                },
                                {
                                    "label": "Tourn2",
                                    "value": "2",
                                    "description": "description",
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "label": "Click me!",
                            "style": 1,
                            "custom_id": "click_one",
                        },
                    ],
                },
            ],
        },
    )
```
