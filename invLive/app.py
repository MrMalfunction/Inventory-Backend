import json
import uuid
import boto3
import simplejson
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    event = event['body']
    event = json.loads(event)
    dynamodb = boto3.resource('dynamodb')
    request_check = {"statusCode": 400,
                     "isBase64Encoded": 'false',
                     "headers": {'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*',
                                 'Access-Control-Allow-Headers': "Content-Type",
                                 "Access-Control-Allow-Methods": "OPTIONS,POST"}
                     }
    username = event['username']
    shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
    ssn = dynamodb.Table('SSN_Data')
    cc = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
    if cc['Count'] == 1:
        inv = dynamodb.Table('Inv_Data')
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        if cc['Items'][0]['cookie'] == event['cookie']:
            if 'item' in event:
                data = inv.query(
                    KeyConditionExpression=Key('shopid').eq(shopid) & Key('item_name').eq(event['item']))
                data_send = {'Items': data['Items']}
                request_check['statusCode'] = 200
                request_check['body'] = simplejson.dumps(data_send)
                return request_check
        else:
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Message': 'Cookie not matched'})
            return request_check
    else:
        request_check['body'] = json.dumps({'Message': 'Cookie not found'})
        request_check['statusCode'] = 400
    return request_check
