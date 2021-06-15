import json
import uuid
import boto3
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
        if cc['Items'][0]['roles']['PutData'] == "False":
            request_check['statusCode'] = 403
            request_check['body'] = json.dumps({'Message': 'Not Authorised'})
            return request_check
        inv = dynamodb.Table('Inv_Data')
        transact = dynamodb.Table('Transactions')
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        if cc['Items'][0]['cookie'] == event['cookie']:
            put_items = []
            transact = dynamodb.Table('Transactions')
            for i in event['data']:
                item_data = inv.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('item_name').eq(i['item']))
                if event['type'] == "IN":
                    if item_data['Count'] == 0:
                        put_items.append({'shopid': shopid, 'item_name': i['item'], 'liveCount': i['quantity']})
                    else:
                        put_items.append({'shopid': shopid, 'item_name': i['item'],
                                          'liveCount': i['quantity'] + item_data['Items'][0]['liveCount']})
                if event['type'] == "OUT":
                    if item_data['Count'] == 0:
                        request_check['statusCode'] = 400
                        request_check['body'] = json.dumps({"Message": "Can't remove " + i['item'] + "as 0 items are "
                                                                                                     "there"})
                        return request_check
                    else:
                        curr_count = item_data['Items'][0]['liveCount']
                        if curr_count >= i['quantity']:
                            put_items.append(
                                {'shopid': shopid, 'item_name': i['item'], 'liveCount': curr_count - i['quantity']})
                        else:
                            request_check['statusCode'] = 400
                            request_check['body'] = json.dumps({'Message': 'Item ' + i['item'] + 'withdrawal more '
                                                                                                 'than allowed'})
                            return request_check
            with inv.batch_writer() as writer:
                for item in put_items:
                    writer.put_item(Item=item)
            transact.put_item(
                Item={'shop_id': str(shopid + "_" + event['type'] + "_" + event['merchant']),
                      'timestamp': str(int(time.time())), 'data': event['data']})
            request_check['statusCode'] = 200
            return request_check
        else:
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Message': 'Cookie not matched'})
            return request_check
    else:
        request_check['body'] = json.dumps({'Message': 'Cookie not found'})
        request_check['statusCode'] = 400
    return request_check
