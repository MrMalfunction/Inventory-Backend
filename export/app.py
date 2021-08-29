import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
from datetime import datetime
from openpyxl import Workbook
import json
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def lambda_handler(event, context):
    event = event['Records'][0]['Sns']['Message']
    # event = event['body']
    event = json.loads(event)
    shopid = str(uuid.uuid5(uuid.NAMESPACE_OID, event['shopid']))
    transaction_type = event['type']
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.resource('s3')
    s3Mail = boto3.client("s3")
    transact = dynamodb.Table('Transactions')
    start = time.mktime(datetime(year=int(event['year']), month=1, day=1).timetuple())
    end = time.mktime(datetime(year=int(event['year']), month=12, day=31).timetuple())
    data = transact.query(
        KeyConditionExpression=Key('shopid').eq(shopid + "_" + transaction_type) & Key(
            'timestamp').between(str(start), str(end)))
    print_data = []
    while data['Items'] != []:
        for i in data["Items"]:
            temp = []
            temp.append(i['transaction-id'])
            temp.append(datetime.fromtimestamp(int(i['timestamp'])).strftime("%d/%m/%Y"))
            temp.append(i['merchant'])
            temp.append(str(i['discount']))
            temp.append(str(i['pre_tax']))
            temp.append(str(i['sgst']))
            temp.append(str(i['cgst']))
            temp.append(str(i['igst']))
            temp.append(str(i['total']))
            main_data = ""
            for j in i['data']:
                main_data += j['itemName'] + ',' + str(j['itemCount']) + ',' + j['itemPrice'] + '\n'
            temp.append(main_data)
            print_data.append(temp)
        if 'LastEvaluatedKey' in data:
            data = transact.query(
                KeyConditionExpression=Key('shopid').eq("019162b4-df11-54e4-8b01-c3ead0ebb4ab_OUT") & Key(
                    'timestamp').between(str(start), str(end)), ExclusiveStartKey=data['LastEvaluatedKey'])
        else:
            data['Items'] = []

    wb = Workbook(write_only=True)
    ws = wb.create_sheet("OUT")
    ws.append(["Transaction Id", "Date", "Merchant", "Discount", "Pre Tax", "SGST", "CGST", "IGST", "TOTAL", "Items"])
    for i in print_data:
        ws.append(i)
    wb.save('/tmp/' + transaction_type + '_' + str(event['year']) + '.xlsx')
    bucket_name = "annual-export-files"
    s3.Bucket(bucket_name).upload_file('/tmp/' + transaction_type + '_' + str(event['year']) + '.xlsx',
                                       shopid + '/' + transaction_type + '_' + str(event['year']) + '.xlsx')
    wb.close()
    msg = MIMEMultipart()
    SENDER = "Inventory-noreply@amolbohora.com"
    AWS_REGION = "ap-south-1"
    response = s3Mail.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket_name,
                                                                                'Key':shopid + '/' + transaction_type + '_' + str(event['year']) + '.xlsx'},
                                             ExpiresIn=518400)
    data = '<h1 style="text-align: center;">Your Annual ' + str(
        transaction_type) + ' Report</h1> <p style="text-align: center;">The following link is going to be available ' \
                            'for 5 days for unlimited uses.</p> <h2 style="text-align: center;"><a href="' + str(
        response) + '">Click Here</a></h2>'
    CHARSET = "utf-8"
    BODY_HTML = data
    SUBJECT = event['shopid'] + ' ' + transaction_type + ' ' + 'Annual Report'
    client = boto3.client('ses', region_name=AWS_REGION)
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER
    msg['To'] = event['email']
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
    msg.attach(htmlpart)
    response = client.send_raw_email(
        Source=SENDER,
        Destinations=[event['email']],
        RawMessage={'Data': msg.as_string()}
    )
