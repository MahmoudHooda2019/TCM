from InquirerPy import inquirer

def main_menu():
    options = [
        "Enter API & HASH",
        "Select old channel",
        "Select new channel",
        "Choose content type",
        "Set start date",
        "Change delay",
        "Start transfer",
        "Exit"
    ]
    choice = inquirer.select(
        message="Select an option:",
        choices=options,
        pointer="▶",
        default=None
    ).execute()
    return choice
