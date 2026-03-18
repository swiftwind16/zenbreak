import rumps
from zenbreak.config import load_config


class ZenBreakApp(rumps.App):
    def __init__(self):
        super().__init__("ZenBreak", title="🧘 --m")
        self.config = load_config()
        self.menu = [
            rumps.MenuItem("Current: Starting up..."),
            None,
            rumps.MenuItem("Pause", callback=self.on_pause),
        ]

    def on_pause(self, sender):
        sender.state = not sender.state


def main():
    ZenBreakApp().run()


if __name__ == "__main__":
    main()
