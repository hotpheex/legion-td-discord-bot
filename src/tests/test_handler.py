import pytest


from handler.main import *


class TestHandler:
    def valid_signature(self):
        event = {
            "body": '{"app_permissions":"442368","application_id":"1058247991867219990","channel_id":"1023401872750547014","data":{"id":"1058279052319928341","name":"checkin","options":[{"name":"solo","options":[],"type":1}],"type":1},"entitlement_sku_ids":[],"guild_id":"755422118719520827","guild_locale":"en-US","id":"1085792820964630608","locale":"en-US","member":{"avatar":null,"communication_disabled_until":null,"deaf":false,"flags":0,"is_pending":false,"joined_at":"2020-09-15T13:37:48.210000+00:00","mute":false,"nick":null,"pending":false,"permissions":"4398046511103","premium_since":null,"roles":[],"user":{"avatar":"39bc9bd8f57cd0bfaa50b8e16491acee","avatar_decoration":null,"discriminator":"1477","display_name":null,"id":"164975439356362752","public_flags":0,"username":"hotpheex"}},"token":"aW50ZXJhY3Rpb246MTA4NTc5MjgyMDk2NDYzMDYwODoyNGpiNm1FWUZOeXNkV3BiR3hKWGtOMlpOcDdBdnRkaktZcmwwdktrMmNVbHE5UmFHdmFIbUFnMWYzOGI1QnBBU3RhcXBpZ3R5bkdjODlSUjI2NWg0S2VFd21TaGlJclZEQ1FuUXVndTh1dDcxaTVKQkFkdWtLc2hiaDRTcnowaA","type":2,"version":1}'
        }
        assert run(event, "zxcv") == 2
