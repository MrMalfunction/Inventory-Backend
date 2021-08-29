import boto3
from boto3.dynamodb.conditions import Key, Attr
import time
from datetime import datetime
from openpyxl import Workbook

dynamodb = boto3.resource('dynamodb')
transact = dynamodb.Table('Transactions')
start = time.mktime(datetime(year=datetime.now().year, month=1, day=1).timetuple())
end = time.mktime(datetime(year=datetime.now().year, month=12, day=31).timetuple())
data = transact.query(
    KeyConditionExpression=Key('shopid').eq("019162b4-df11-54e4-8b01-c3ead0ebb4ab_OUT") & Key(
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

print(print_data)
wb = Workbook(write_only = True)
ws = wb.create_sheet("OUT")
ws.append(["Transaction Id", "Date", "Merchant", "Discount", "Pre Tax", "SGST", "CGST", "IGST","TOTAL", "Items"])
for i in print_data :
    ws.append(i)
wb.save('/tmp/write_only_file.xlsx')
wb.close()
print("DONE")