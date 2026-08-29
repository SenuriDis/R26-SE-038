
# Title: Assignment 05

# Description: Working with Dictionaries and Files

#              When the program starts, load each "row" of data

#              in "ToDoList.txt" into a python Dictionary.

#              Add each dictionary "row" to a python list "table"

# ChangeLog (Who,When,What):

# RRoot,1.1.2030,Created started script

# Tiya Farah ,05/16/2022 Added

# ------------------------------------------------------------------------ #



# -- Data -- #

# declare variables and constants

objFile = "ToDoList.txt"   # An object that represents a file

objF = None   # File handle

strData = ""  # A row of text data from the file

dicRow = {}    # A row of data separated into elements of a dictionary {Task,Priority}

lstTable = []  # A list that acts as a 'table' of rows

strMenu = ""   # A menu of user options

strChoice = "" # A Capture the user option selection

strTask = ""   # New task entry from the user

strPriority = ""  # New priority entry from the user

strRemove = ""   # A task to be removed



# -- Processing -- #

# Step 1 - When the program starts, load the data you have

# in a text file called ToDoList.txt into a python list of dictionaries rows (like Lab 5-2)

try:

    objF = open(objFile, "r")

    for row in objF:

        strData = row.split(" - ")  # returns a list

        dicRow = {"Task": strData[0], "Priority": strData[1].strip()}

        lstTable.append(dicRow)

    objF.close()

except:

    print('File not found, new file will be created, when you save.')

# -- Input/Output -- #

# Step 2 - Display a menu of choices to the user

while (True):

    print("""

    Menu of Options

    1) Show current data

    2) Add a new item.

    3) Remove an existing item.

    4) Save Data to File

    5) Exit Program

    """)

    strChoice = str(input("Which option would you like to perform? [1 to 5] - "))

    print()  # adding a new line for looks

    # Step 3 - Show the current items in the table

    if (strChoice.strip() == '1'):

        print('Current To Do List [Task - Priority]:')

        for row in lstTable:

            print(row["Task"], row["Priority"], sep=" - ")

        continue

    # Step 4 - Add a new item to the list/Table

    elif (strChoice.strip() == '2'):

        strTask = input("Please enter a task: ")

        strPriority = input("Please give it a priority: ")

        lstTable.append({"Task": strTask, "Priority": strPriority})

        print("New Task has been added!")

        continue

    # Step 5 - Remove an item from the list/Table

    elif (strChoice.strip() == '3'):

        strRemove = input("Enter a task to remove: ")

        for row in lstTable:

            if row["Task"].lower() == strRemove.lower():

                lstTable.remove(row)

                print("The task has been removed")

            else:

                print("The task was not found")

        continue

    # Step 6 - Save tasks to the ToDoToDoList.txt file

    elif (strChoice.strip() == '4'):

        objF = open(objFile, "w")

        for row in lstTable:

            objF.write(str(row["Task"]) + " - " + str(row["Priority"]) + "\n")

        objF.close()

        print("The data was saved!")

        continue

    # Step 7 - Exit program

    elif (strChoice.strip() == '5'):

        print("Program Ended")

        break  # and Exit the program

    else:

        print("Please only choose 1-5!")
