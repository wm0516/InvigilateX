import pymysql

connection = pymysql.connect(
    host="WM05.mysql.pythonanywhere-services.com",
    user="WM05",
    password="Pythonanywhere",
    database="WM05$InvigilateX"
)
print("Connected successfully!")
connection.close()