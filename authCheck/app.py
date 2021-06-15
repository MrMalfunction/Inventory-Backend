import secrets
import string
import time
from boto3.dynamodb.conditions import Key
from passlib.hash import pbkdf2_sha256
import boto3
import json
import uuid


def lambda_handler(event, context):
    event = event['body']
    event = json.loads(event)
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Cred_Data')
    request_check = {"statusCode": 400,
                     "isBase64Encoded": 'false',
                     "headers": {'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*',
                                 'Access-Control-Allow-Headers': "Content-Type",
                                 "Access-Control-Allow-Methods": "OPTIONS,POST"}
                     }
    if event['type'] == "SignUp":
        password_hash = pbkdf2_sha256.hash(event['password'])
        username = event['username']  # username is shop_name + "." + username (given by user)
        username_check = table.query(
            KeyConditionExpression=Key('shopid').eq(str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid'])))
        )
        if "Items" in username_check == [] and event['registerFirst'] == "true":
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({"Message": "ShopId should be unique"})
            return request_check
        if event['iam'] == "root":
            root_role = {
                "PutData": "True",
                "ViewData": "True"
            }

            signup_flag = table.put_item(Item={
                'username': username,
                'password': password_hash,
                'multi': 'True',
                'roles': root_role,
                'shopid': str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
            },
                # ReturnConsumedCapacity='TOTAL',
                # ReturnItemCollectionMetrics='SIZE'
            )
            if signup_flag['ResponseMetadata']['HTTPStatusCode'] == 200:
                request_check['statusCode'] = 200
                request_check['body'] = json.dumps({'cookie': 'NULL'})
            return request_check
        elif event['iam'] == "kiosk":
            kiosk_role = {
                "PutData": {'S': "True"},
                "ViewData": {'S': "False"}
            }
            signup_flag = table.put_item(Item={
                'username': username,
                'hash': password_hash,
                'multi': 'True',
                'roles': kiosk_role,
                'shopid': str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
            }
                # ReturnConsumedCapacity='TOTAL',
                # ReturnItemCollectionMetrics='SIZE'
            )
            if signup_flag['ResponseMetadata']['HTTPStatusCode'] == 200:
                request_check['statusCode'] = 200
                request_check['body'] = json.dumps({'cookie': 'NULL', 'Message': 'Success'})
            return request_check
        else:
            request_check['statusCode'] = 401
            request_check['body'] = json.dumps({'cookie': 'NULL', 'Message': "Wrong IAM"})
            return request_check
    elif event['type'] == "Login":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        login_check = table.query(
            KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(event['username']))
        if login_check['Count'] == 1:
            if pbkdf2_sha256.verify(event['password'], login_check['Items'][0]['password']):
                cookie = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(15))
                request_check['body'] = json.dumps({'cookie': cookie})
                ssn = dynamodb.Table('SSN_Data')
                ssn.put_item(Item={
                    'cookie': cookie,
                    'TTL': int(time.time() + 604800),
                    'username': username,
                    'roles': login_check['Items'][0]['roles'],
                    'shopid': shopid
                }
                    # ReturnConsumedCapacity='TOTAL',
                    # ReturnItemCollectionMetrics='SIZE'
                )
                request_check['statusCode'] = 200
                return request_check
            else:
                request_check['statusCode'] = 400
                request_check['body'] = json.dumps({'cookie': 'NULL', 'Message': 'User not registered'})
                return request_check
    elif event['type'] == "CC":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        ssn = dynamodb.Table('SSN_Data')
        cc = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(event['username']))
        if cc['Count'] == 1:
            if cc['Items'][0]['cookie'] == event['cookie']:
                request_check['statusCode'] = 200
                request_check['body'] = json.dumps(
                    {'cookie': cc['Items'][0]['cookie'], 'role': cc['Items'][0]['roles']})
                return request_check
            else:
                request_check['statusCode'] = 400
                request_check['body'] = json.dumps({'Message': 'Cookie not matched'})
                return request_check
        else:
            request_check['body'] = json.dumps({'Message': 'Cookie not found'})
            request_check['statusCode'] = 400
            return request_check
    elif event['type'] == "Reset":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        login_check = table.query(
            KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if login_check['Count'] == 1:
            password_hash = pbkdf2_sha256.hash(event['password'])
            print(password_hash)
            response = table.update_item(
                Key={
                    'shopid': shopid,
                    'username': username
                },
                UpdateExpression='set password = :p',
                ExpressionAttributeValues={
                    ':p': password_hash
                }
            )
            return response
    else:
        request_check['body'] = json.dumps(({'cookie': 'NULL', 'Message': 'Wrong Input'}))
        return request_check
