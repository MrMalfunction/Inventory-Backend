import json
import uuid
import boto3
import simplejson
from boto3.dynamodb.conditions import Key, Attr

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
        if cc['Items'][0]['cookie'] == event['cookie'] and cc['Items'][0]['roles']['View_Past'] == 'true':
            merchant = event['merchant']
            if 'type' in event:
                data = None
                if event['Last_Key'] != "NULL":
                    last_key = event['Last_Key']
                    if event['merchant'] != "NULL":
                        data = transact.query(
                            KeyConditionExpression=Key('shopid').eq(shopid +"_"+ event['type']) & Key(
                                'timestamp').between(event['time_start'], event['time_end']),
                            FilterExpression=Attr('merchant').eq(merchant),
                            ExclusiveStartKey=json.loads(last_key))
                    else:
                        data = transact.query(
                            KeyConditionExpression=Key('shopid').eq(shopid +"_"+ event['type']) & Key(
                                'timestamp').between(event['time_start'], event['time_end']),
                            ExclusiveStartKey=(last_key))
                else:
                    if event['merchant'] != "NULL":
                        data = transact.query(
                            KeyConditionExpression=Key('shopid').eq(shopid +"_"+ event['type']) & Key(
                                'timestamp').between(event['time_start'], event['time_end']),
                            FilterExpression=Attr('merchant').eq(merchant))
                    else:
                        data = transact.query(
                            KeyConditionExpression=Key('shopid').eq(shopid + "_" + event['type']) & Key(
                                'timestamp').between(event['time_start'], event['time_end']))
                last_key = "NULL"
                if 'LastEvaluatedKey' in data:
                    last_key = data['LastEvaluatedKey']
                for i in data['Items']:
                    del i['shopid']
                    del i['pre_tax']
                    del i['cgst']
                    del i['igst']
                    del i['sgst']
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
