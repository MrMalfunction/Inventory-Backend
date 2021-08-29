import json
import uuid
import boto3
from boto3.dynamodb.conditions import Key
import pickle
import os
import botocore


def lambda_handler(event, context):
    event = event['body']
    event = json.loads(event)
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.resource('s3')
    request_check = {"statusCode": 400,
                     "isBase64Encoded": 'false',
                     "headers": {'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*',
                                 'Access-Control-Allow-Headers': "Content-Type",
                                 "Access-Control-Allow-Methods": "OPTIONS,POST"}
                     }
    shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
    check = dynamodb.Table('Search_Helper')
    if event['selection'] == 'Retrieve':
        type = event['type']
        length = event['len']
        arr = []
        try:
            s3.Bucket('search-autocomplete').download_file(shopid + "/" + type + ".pkl", "/tmp/" + type + ".pkl")
            with open("/tmp/" + type + ".pkl", "rb") as f:
                arr = pickle.load(f)
                os.remove("/tmp/" + type + ".pkl")
        except  botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "403":
                request_check['body'] = json.dumps({'Message': 'Not created'})
            else:
                raise
        new_arr = []
        for i in range(length, len(arr)):
            new_arr.append(arr[i])
        request_check['statusCode'] = 200
        request_check['body'] = json.dumps({'Message': 'Success', 'Data': new_arr})
        return request_check

    else:
        lenCheck = check.query(KeyConditionExpression=Key('shopid').eq(shopid))
        if lenCheck['Count'] == 0:
            type = event['type']
            arr = []
            for i in event['data']:
                arr.append(i)
            with open("/tmp/" + type + ".pkl", "wb") as f:
                pickle.dump(arr, f)
            s3.Bucket('search-autocomplete').upload_file("/tmp/" + type + ".pkl", shopid + "/" + type + ".pkl")
            os.remove("/tmp/" + type + ".pkl")
            check.put_item(
                Item={
                    'shopid': shopid,
                    type: len(arr),
                    "Merchant" if type == "Items" else "Items": 0
                }
            )
            request_check['statusCode'] = 200
        else:
            type = event['type']
            arr = []
            try:
                s3.Bucket('search-autocomplete').download_file(shopid + "/" + type + ".pkl", "/tmp/" + type + ".pkl")
                with open("/tmp/" + type + ".pkl", "rb") as f:
                    arr = pickle.load(f)
                    os.remove("/tmp/" + type + ".pkl")
            except  botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "403":
                    print("The object does not exist.")
                else:
                    raise
            for i in event['data']:
                if i not in arr:
                    arr.append(i)
            other = "Merchant" if type == "Items" else "Items"
            check.put_item(
                Item={
                    'shopid': shopid,
                    type: len(arr),
                    other: lenCheck['Items'][0][other]
                }
            )
            with open("/tmp/" + type + ".pkl", "wb") as f:
                pickle.dump(arr, f)
            s3.Bucket('search-autocomplete').upload_file("/tmp/" + type + ".pkl", shopid + "/" + type + ".pkl")
            os.remove("/tmp/" + type + ".pkl")
            request_check['statusCode'] = 200
    return request_check
