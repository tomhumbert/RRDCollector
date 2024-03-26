import tkinter as tk
from tkinter import Text, StringVar, OptionMenu
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
from scraper import RScraper
import pandas as pd

import sys

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.config(state=tk.NORMAL)  # Enable the widget
        self.text_widget.insert(tk.END, message)
        self.text_widget.config(state=tk.DISABLED)  # Disable the widget
        self.text_widget.see(tk.END)  # Scroll to the end of the text

    def flush(self):
        pass  # This method is required but we don't need to do anything

def start_button_clicked():
    # Get the contents of the text fields
    field_contents = [entry.get() for entry in entries]
    mode = clicked.get()
    
    # Create a message for the pop-up
    message = "Contents of the fields:\n\n"
    resume = ""
    for i, content in enumerate(field_contents, start=1):
        resume += f", {content}"
        message += f"Field {i}: {content}\n"
    message += "\nDo you want to continue with these parameters?"

    # Display the pop-up message
    response = messagebox.askyesno("Confirmation", message)
    
    # If user confirms, execute the function; otherwise, do nothing
    if response:
        # Add your function execution here
        print("Starting collection with the given parameters")
        collect_subs(field_contents[1], field_contents[2], mod=mode)
    else:
        pass

def collect_authors():
    authors = pd.read_csv("data/seed_authors.csv")
    authorlist = list(authors['authors'])

    # Scraper init
    scraper = RScraper("reddit-credentials.txt")

    data = scraper.get_authors_posts(authorlist)
    print(data.head())
    print(scraper.summary())
    input("Save this collection? Else, abort.")
    scraper.safe_all_to_csv()

def collect_subs(subreddits, kwords, mod='search'):
    scraper = RScraper("reddit-credentials.txt")

    data = scraper.get_posts(subreddits, keywords=kwords, mode=mod)

    print(data.head())
    print(scraper.summary())
    print(f"Saving this collection. It has {len(data.subreddit)} entries.")
    scraper.safe_all_to_csv()


#============ LEFT PANEL ==============

# Create the main window
root = tk.Tk()
root.title("Collection Manager")
root.geometry("900x500")  # Set initial size


# Divide the viewport into two frames
left_frame = tk.Frame(root, width=200)  # Adjust width as needed
left_frame.pack(side=tk.LEFT, fill=tk.Y)

right_frame = tk.Frame(root)
right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Input fields on the left side
input_labels = ['Title', 'Subreddits', 'Keywords']
entries = []
for label_text in input_labels:
    label = tk.Label(left_frame, text=label_text)
    label.pack()
    entry = tk.Entry(left_frame)
    entry.pack()
    entries.append(entry)

# Change the label text 
def show(): 
    label.config( text = clicked.get() ) 
# Dropdown menu options 
options = [ 
    "top",
    "new",
    "hot"
] 
# datatype of menu text 
clicked = StringVar() 
# initial menu text 
clicked.set( "top" ) 
  
# Create Dropdown menu 
label = tk.Label(left_frame, text="Mode")
drop = OptionMenu( left_frame , clicked , *options ) 
drop.pack() 
  

# 'Start' button below input fields
start_button = tk.Button(left_frame, text="Start", command=start_button_clicked)
start_button.pack()

#============ RIGHT PANEL ==============

# Create a Frame to contain the table and console
table_console_frame = tk.Frame(right_frame)
table_console_frame.pack(fill=tk.BOTH, expand=True)

#------------ CONSOLE -----------------

output_text = tk.Text(table_console_frame, wrap=tk.WORD)
output_text.pack(fill=tk.BOTH, expand=True)
output_text.config(height=7)
# Redirect stdout to the Text widget
sys.stdout = StdoutRedirector(output_text)

#------------ SEPERATOR -----------------

separator = ttk.Separator(table_console_frame, orient='horizontal')
separator.pack(fill='x', padx=5, pady=5)

#------------ TREEVIEW -----------------

def pack_the_table(data=None):
    # GET COL NAMES
    if data == None:
        columns = ('subreddit', 'title', 'content', 'upvotes', 'upvote_ratio', 'n_comments')
        # Insert dummy data into the table
        rows = [
            ('r/python', 'Python is awesome', 'Python is a versatile programming language', 1000, 0.95, 50),
            ('r/machinelearning', 'Introduction to ML', 'Learn the basics of machine learning', 800, 0.90, 30),
            ('r/datascience', 'Data Science career tips', 'How to kickstart your career in Data Science', 1200, 0.92, 60)
        ]
    else:
        columns = data.columns
        rows = data

    tree = ttk.Treeview(table_console_frame, columns=columns, show='headings')
    tree_height = int(root.winfo_reqheight() * 3 / 4)
    tree.config(height=tree_height)

    # Define column headings
    for col in columns:
        tree.heading(col, text=col.title())
    for data in rows:
        tree.insert('', 'end', values=data)

    # Pack the table
    tree.pack(fill=tk.BOTH, expand=True)
    # Calculate the maximum width of data in each column
    max_widths = [max([len(str(item)) for item in column]) for column in zip(*rows)]

    # Set the width of each column in the Treeview widget based on the maximum width of data in that column
    for i, width in enumerate(max_widths):
        tree.column(columns[i], width=width + 20)  # Add a little padding to the column width

    # Calculate the total width needed for all columns
    total_width = sum(max_widths) + len(columns) * 20  # Add padding for each column
    # Update the window size to fit the content
    if total_width > 900:
        root.geometry(f"{total_width}x500")
    return tree

# Pack the table
t = pack_the_table()

# Configure the style for dark theme
style = ttk.Style()
style.theme_use('clam')  # Choose the dark theme (you can use 'clam', 'alt', or 'default')
style.configure('Treeview', background='#333', foreground='white', fieldbackground='#333')
style.configure('Text', background='#333', foreground='white', fieldbackground='#333')
style.map('Treeview', background=[('selected', '#444')])
style.map('Text', background=[('selected', '#444')])

# Run the Tkinter event loop
root.mainloop()
