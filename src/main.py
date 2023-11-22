from gui import app

def main():
    gui_app = app.App()
    gui_app.mainloop()

if __name__ == "__main__":
    # TODO sanitize input when getting msa name from entry box
    # TODO make year built consistent with year built drop down
    main()
