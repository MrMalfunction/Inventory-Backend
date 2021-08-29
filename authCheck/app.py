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
    ssn = dynamodb.Table('SSN_Data')
    request_check = {"statusCode": 400,
                     "isBase64Encoded": 'false',
                     "headers": {'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*',
                                 'Access-Control-Allow-Headers': "Content-Type",
                                 "Access-Control-Allow-Methods": "OPTIONS,POST"}
                     }
    if not "type" in event:
        request_check['statusCode'] = 400
        request_check['body'] = json.dumps({"Message": "Type Not Given"})
        return request_check
    if event['type'] == "List":
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        username = event['username']
        auth_check = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if auth_check['Count'] == 0:
            request_check['statusCode'] = 401
            request_check['body'] = json.dumps({'Message': 'Illegal Transaction'})
            return request_check
        else:
            if auth_check['Items'][0]['cookie'] == event['cookie']:
                request_check['statusCode'] = 403
                request_check['body'] = json.dumps({'Message': 'Not Authorised'})
                return request_check
            if auth_check['Items'][0]['roles']['SignUp'] == "false":
                request_check['statusCode'] = 403
                request_check['body'] = json.dumps({'Message': 'Policy Denied'})
                return request_check
            cred_list = table.query(KeyConditionExpression=Key('shopid').eq(shopid))
            data = []
            for i in cred_list['Items']:
                data.append({"username": i['username']})
            request_check['statusCode'] = 200
            request_check['body'] = json.dumps(data)
            return request_check
    if event['type'] == "SignUp":
        root_role = {
            "Data_In": "false",
            "Data_Out": "false",
            "View_Live": "false",
            "View_Past": "false",
            "Return": "false",
            "SignUp": "false",
            "Reset": "false",
            "Export": "false"
        }
        if not "roles" in event:
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Message': 'Roles not given'})
            return request_check
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        username = event['username']
        auth_check = table.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if auth_check['Count'] == 0:
            request_check['statusCode'] = 401
            request_check['body'] = json.dumps({'Message': 'Illegal Transaction'})
            return request_check
        else:
            if not pbkdf2_sha256.verify(event['password'], auth_check['Items'][0]['password']):
                request_check['statusCode'] = 401
                request_check['body'] = json.dumps({'Message': 'Illegal Transaction'})
                return request_check
            if auth_check['Items'][0]['roles']['SignUp'] == "false":
                request_check['statusCode'] = 403
                request_check['body'] = json.dumps({'Message': 'Policy Denied'})
                return request_check
        new_username = event['new_username']
        username_check = table.query(
            KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(new_username))
        policy_reset = ""
        if not "policy" in event:
            policy_reset = "false"
        else:
            policy_reset = "true"
        if username_check['Count'] != 0 and policy_reset == "false":
            request_check['statusCode'] = 400
            request_check['body'] = json.dumps({'Message': 'User Name should be unique'})
            return request_check
        for i in event['roles']:
            root_role[i] = "true"
        password_hash = pbkdf2_sha256.hash(event['new_password'])
        signup_flag = table.put_item(Item={
            'username': new_username,
            'password': password_hash,
            'multi': 'True',
            'roles': root_role,
            'shopid': str(shopid)
        })
        if signup_flag['ResponseMetadata']['HTTPStatusCode'] == 200:
            request_check['statusCode'] = 200
            request_check['body'] = json.dumps({'Message': 'SignUp Success'})
            return request_check
        else:
            request_check['statusCode'] = 500
            request_check['body'] = json.dumps({'Message': 'Something Went Wrong'})
            return request_check
    elif event['type'] == "Login":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        login_check = table.query(
            KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(event['username']))
        if login_check['Count'] == 1:
            if pbkdf2_sha256.verify(event['password'], login_check['Items'][0]['password']):
                cookie = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(15))
                request_check['body'] = json.dumps({'cookie': cookie, 'role': login_check['Items'][0]['roles']})
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
                request_check['statusCode'] = 401
                request_check['body'] = json.dumps({'cookie': 'NULL', 'Message': 'Password Mismatch'})
                return request_check
        else:
            request_check['statusCode'] = 401
            request_check['body'] = json.dumps({'cookie': 'NULL', 'Message': 'User not registered'})
            return request_check
    elif event['type'] == "CC":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        cc = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if cc['Count'] == 1:
            if cc['Items'][0]['cookie'] == event['cookie']:
                request_check['statusCode'] = 200
                request_check['body'] = json.dumps(
                    {'cookie': cc['Items'][0]['cookie'], 'role': cc['Items'][0]['roles']})
                return request_check
            else:
                request_check['statusCode'] = 401
                request_check['body'] = json.dumps({'Message': 'Cookie not matched'})
                return request_check
        else:
            request_check['body'] = json.dumps({'Message': 'Cookie not found'})
            request_check['statusCode'] = 401
            return request_check
    elif event['type'] == "Reset":
        username = event['username']
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        login_check = table.query(
            KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if login_check['Count'] == 1:
            password_hash = pbkdf2_sha256.hash(event['password'])
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
    elif event['type'] == "Delete":
        shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
        username = event['username']
        auth_check = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(username))
        if auth_check['Count'] == 0:
            request_check['statusCode'] = 401
            request_check['body'] = json.dumps({'Message': 'Illegal Transaction'})
            return request_check
        else:
            if auth_check['Items'][0]['cookie'] == event['cookie']:
                request_check['statusCode'] = 403
                request_check['body'] = json.dumps({'Message': 'Not Authorised'})
                return request_check
            if auth_check['Items'][0]['roles']['SignUp'] == "false":
                request_check['statusCode'] = 403
                request_check['body'] = json.dumps({'Message': 'Policy Denied'})
                return request_check
        table.delete_item(Key={'shopid': shopid, 'username': event['new_username']})
        ssn.delete_item(Key={'shopid': shopid, 'username': event['new_username']})
        request_check['statusCode'] = 200
        return request_check
    else:
        request_check['body'] = json.dumps(({'cookie': 'NULL', 'Message': 'Wrong Input'}))
        return request_check
