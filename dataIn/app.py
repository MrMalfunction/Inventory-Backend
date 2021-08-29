import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key
import time
import secrets
import string


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
        if cc['Items'][0]['roles']['Data_In'] == "false":
            request_check['statusCode'] = 403
            request_check['body'] = json.dumps({'Message': 'Not Authorised'})
            return request_check
        inv = dynamodb.Table('Inv_Data')
        transact = dynamodb.Table('Transactions')
        order_id = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(3))
        if cc['Items'][0]['cookie'] == event['cookie']:
            put_items = []
            transact = dynamodb.Table('Transactions')
            for i in event['data']:
                item_data = inv.query(
                    KeyConditionExpression=Key('shopid').eq(shopid) & Key('item_name').eq(i['itemName']))
                if event['type'] == "IN":
                    if item_data['Count'] == 0:
                        put_items.append(
                            {'shopid': shopid, 'item_name': i['itemName'], 'liveCount': int(i['itemCount'])})
                    else:
                        put_items.append({'shopid': shopid, 'item_name': i['itemName'],
                                          'liveCount': int(i['itemCount']) + item_data['Items'][0]['liveCount']})
                if event['type'] == "OUT":
                    if item_data['Count'] == 0:
                        request_check['statusCode'] = 400
                        request_check['body'] = json.dumps(
                            {"Message": "Can't remove " + i['itemName'] + "as 0 items are "
                                                                          " there"})
                        return request_check
                    else:
                        curr_count = item_data['Items'][0]['liveCount']
                        if curr_count >= int(i['itemCount']):
                            flag = True
                            for temp in put_items:
                                if temp['item_name'] == i['itemName']:
                                    if temp['liveCount'] - i['itemCount'] >= 0:
                                        temp['liveCount'] = temp['liveCount'] - i['itemCount']
                                        flag = False
                                        break
                                    else:
                                        request_check['statusCode'] = 400
                                        request_check['body'] = json.dumps(
                                            {'Message': 'Item ' + i['itemName'] + 'withdrawal more '
                                                                                  'than allowed'})
                                        return request_check
                            if flag:
                                put_items.append(
                                    {'shopid': shopid, 'item_name': i['itemName'],
                                     'liveCount': curr_count - int(i['itemCount'])})
                        else:
                            request_check['statusCode'] = 400
                            request_check['body'] = json.dumps({'Message': 'Item ' + i['itemName'] + 'withdrawal more '
                                                                                                     'than in '
                                                                                                     'Inventory'})
                            return request_check
            for item in put_items:
                inv.put_item(Item=item)
            discount = 0
            if event['discount']:
                discount = event['discount']
            transact.put_item(
                Item={'shopid': str(shopid)+"_"+ event['type'],
                      'timestamp': str(int(time.time())), 'data': event['data'], "pre_tax": event['pre_tax'],
                      "sgst": event['sgst'], "cgst": event['cgst'], "igst": event['igst'], 'total': event['total'],
                      'merchant': event['merchant'], 'transaction-id': order_id, 'discount' :discount })
            request_check['statusCode'] = 200
            request_check['body'] = json.dumps({'Message': 'Success', 'Order Id': order_id})
            return request_check
        else:
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Message': 'Cookie not matched'})
            return request_check
    else:
        request_check['body'] = json.dumps({'Message': 'Cookie not found'})
        request_check['statusCode'] = 400
    return request_check
