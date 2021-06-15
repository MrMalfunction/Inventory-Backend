import json
import uuid
import boto3
import simplejson
from boto3.dynamodb.conditions import Key
import time


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
        transact = dynamodb.Table('Transactions')
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        if cc['Items'][0]['cookie'] == event['cookie']:
            merchant = event['merchant']
            if 'type' in event:
                if event['Last_Key']:
                    last_key = event['Last_Key']
                    data = transact.query(
                        KeyConditionExpression=Key('shop_id').eq(shopid + "_" + event['type'] + "_" + merchant) & Key(
                            'timestamp').between(event['time_start'], event['time_end']),
                        ExclusiveStartKey=json.loads(last_key))
                else:
                    data = transact.query(
                        KeyConditionExpression=Key('shop_id').eq(shopid + "_" + event['type'] + "_" + merchant) & Key(
                            'timestamp').between(event['time_start'], event['time_end']))
                last_key = "NULL"
                if 'LastEvaluatedKey' in data:
                    last_key = data['LastEvaluatedKey']
                print(data['Items'])
                data_send = {'Items': data['Items'], 'Last_Key': last_key}
                request_check['statusCode'] = 200
                request_check['body'] = simplejson.dumps(data_send)
                return request_check
            else:
                request_check['statusCode'] = 400
                request_check['body'] = json.dumps({'Items': 'NULL', 'Message': 'Type Not Given'})
        else:
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Items': 'NULL', 'Message': 'Cookie not matched'})
            return request_check
    else:
        request_check['body'] = json.dumps({'Items': 'NULL', 'Message': 'Cookie not found'})
        request_check['statusCode'] = 400
    return request_check
