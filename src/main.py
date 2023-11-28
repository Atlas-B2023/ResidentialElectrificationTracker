from gui import app
from wakepy import keep
from backend.helper import log


def main() -> None:
    gui_app = app.App()
    gui_app.mainloop()


if __name__ == "__main__":
    # TODO make year built consistent with year built drop down
    with keep.running() as k:
        if k.success:
            main()
        else:
            log(
                "Could not establish always on mode. Consider turning on sleep mode in your computers settings.",
                "warn",
            )
