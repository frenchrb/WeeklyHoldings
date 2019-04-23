#!/usr/bin/env python

import os
from pathlib import Path
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
import catdate
import holdings

def save():
    global savepath
    desktop = Path(os.path.expanduser('~')) / 'Desktop'
    savepath = filedialog.askdirectory(initialdir=desktop)
    #print('savepath: ' + savepath)

def runCatdate():
    print()
    args = []
    args.append(startdate.get())
    args.append(enddate.get())
    args.append(savepath)
    catdate.main(args)

def runHoldings():
    print()
    args = []
    args.append(startdate.get())
    args.append(enddate.get())
    args.append(savepath)
    holdings.main(args)
    root.destroy()

root = Tk()
root.wm_title('Weekly Holdings')

label1 = Label(root, text='STEP 0: Set dates and select save location').grid(row = 1, column = 0, columnspan = 2, sticky = W)
label2 = Label(root, text='Start date (MM-DD-YYYY)').grid(row = 2, column = 0)
label3 = Label(root, text='End date (MM-DD-YYYY)').grid(row = 3, column = 0)

startdate = StringVar()
enddate = StringVar()
e1 = Entry(root, textvariable = startdate).grid(row = 2, column = 1)
e2 = Entry(root, textvariable = enddate).grid(row = 3, column = 1)

button1 = Button(root, text = 'Select save location', height = 2, width = 40, command = save).grid(row = 4, columnspan = 2)

sep1 = ttk.Separator(root).grid(row = 6, columnspan = 2, sticky = EW)

label4 = Label(root, text='STEP 1: Identify records needing cat date').grid(row = 7, column = 0, columnspan = 2, sticky = W)
button2 = Button(root, text = 'Get records (takes a while... be patient)', height = 2, width = 40, command = runCatdate)
button2.grid(row = 8, columnspan = 2)

sep1 = ttk.Separator(root).grid(row = 9, columnspan = 2, sticky = EW)

label5 = Label(root, text = 'STEP 2: Import text file into Sierra Create Lists and compare to batchload create list').grid(row = 10, column = 0, columnspan = 2, sticky = W)

sep2 = ttk.Separator(root).grid(row = 11, columnspan = 2, sticky = EW)

label6 = Label(root, text = 'STEP 3: Global update to set cat dates').grid(row = 15, column = 0, columnspan = 2, sticky = W)

sep3 = ttk.Separator(root).grid(row = 16, columnspan = 2, sticky = EW)

label7 = Label(root, text = 'STEP 4: Identify records to set holdings on').grid(row = 20, column = 0, columnspan = 2, sticky = W)
button3 = Button(root, text = 'Run holdings script', height = 2, width = 40, command = runHoldings).grid(row = 21, columnspan = 2)

sep4 = ttk.Separator(root).grid(row = 30, columnspan = 2, sticky = EW)

label8 = Label(root, text = 'STEP 5: Compare spreadsheets with create list exports').grid(row = 31, column = 0, columnspan = 2, sticky = W)

root.mainloop()
