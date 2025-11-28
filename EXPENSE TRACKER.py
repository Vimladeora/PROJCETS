import csv
from datetime import datetime

FILE_NAME = "expenses.csv"

def initialize_file():
  try:
    with open(FILE_NAME, 'x', newline='') as file:
      writer = csv.writer(file)
      writer.writerow(["Date", "Amount","Category","Description"])
  except FileExistsError:
    pass

def menu():
  print("\n==== EXPENSE TRACKER====")
  print("1. Add expense")
  print("2. view all expense")
  print("3. calculate total expense")
  print("4. filter by category")
  print("5. exit")


def add_expense():
  date = input("enter date (yyyy-mm-dd) or leave blank for today:")
  if date.strip() == "":
      date =  datetime.today().strftime("%y-%m-%d")
  amount = input("Enter amount:")
  category = input("enter category:")
  description = input("enter description:")

  with open(FILE_NAME,"a",newline="") as file:
    writer = csv.writer(file)
    writer.writerow([date,amount,category,description])
  print("Expense added successfully!")

def view_expenses():
  with open(FILE_NAME,"r") as file:
    reader = csv.reader(file)
    for row in reader:
      print(row)

def total_expense():
  total = 0
  with open(FILE_NAME,'r') as file:
    reader = csv.dictreader(file)
    for row in reader:
      total += float(row["Amount"])
  print(f"total expense: {total}")


def filter_by_category():
  cat = input("enter category to filter: ")
  with open (FILE_NAME, "r") as file:
    reader = csv.DictReader(file)
    found = False
    for row in reader:
      if row["Category"].lower() == cat.lower():
        print(row)
        found = True
    if not found:
      print("no expense found in this category")


initialize_file()

while True:
  menu()
  choice = input("enter your choice")

 
  
  if choice == "1":
        add_expense()
  elif choice == "2":
        view_expenses()
  elif choice == "3":
        total_expense()
  elif choice == "4":
        filter_by_category()
  elif choice == "5":
        print("Goodbye!")
        break
  else:
        print("Invalid choice! Try again.")
  