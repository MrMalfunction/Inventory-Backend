import boto3
import json
from boto3.dynamodb.conditions import Key
import uuid

def lambda_handler(event, context):
    event = event['body']
    event = json.loads(event)
    request_check = {"statusCode": 400,
                     "isBase64Encoded": 'false',
                     "headers": {'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*',
                                 'Access-Control-Allow-Headers': "Content-Type",
                                 "Access-Control-Allow-Methods": "OPTIONS,POST"}
                     }
    dynamodb = boto3.resource('dynamodb')
    ssn = dynamodb.Table('SSN_Data')
    shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))

    cc = ssn.query(KeyConditionExpression=Key('shopid').eq(shopid) & Key('username').eq(event['username']))
    if cc['Count'] == 1:
        if cc['Items'][0]['roles']['Export'] == "false":
            request_check['statusCode'] = 403
            request_check['body'] = json.dumps({'Message': 'Not Authorised'})
            return request_check
        if cc['Items'][0]['cookie'] != event['cookie']:
            request_check['statusCode'] = 403
            request_check['body'] = json.dumps({'Message': 'Not Authorised'})
            return request_check
    client = boto3.client('sns')
    event['type'] = "IN"
    response = client.publish(
        TargetArn="arn:aws:sns:ap-south-1:404907247506:Exporter",
        Message=json.dumps({'default': json.dumps(event)}),
        MessageStructure='json'
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        request_check['statusCode'] = 500
        return request_check
    event['type'] = "OUT"
    response = client.publish(
        TargetArn="arn:aws:sns:ap-south-1:404907247506:Exporter",
        Message=json.dumps({'default': json.dumps(event)}),
        MessageStructure='json'
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        request_check['statusCode'] = 500
        return request_check
    request_check['statusCode'] = 200
    return request_check
