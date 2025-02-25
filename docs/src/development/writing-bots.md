# Writing Bots

Check out [Python README](python-README) if you need help with setting up the project in general.

## AFK Journey
If you want to add any feature to the AFK Journey Bot:

1. Create a new mixin in the mixins dir [python/adb_auto_player/games/afk_journey/mixins](../../../python/adb_auto_player/games/afk_journey/mixins)
    ```python
    import logging
    from abc import ABC
    from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase
    
    class YourMixin(AFKJourneyBase, ABC):
        def your_mixin_entry_point(self) -> None:
            """Entry for your feature."""
            logging.info("Hello World!")
            self.start_up() # initializes most things you will need like device and config
    ```

2. Add a new Command in [class AFKJourney](../../../python/adb_auto_player/games/afk_journey/main.py).
    ```python
        ...

        class AFKJourney(
            AFKStagesMixin,
            ArcaneLabyrinthMixin,
            ...,
            YourMixin,
        ):
            def get_cli_menu_commands(self) -> list[Command]:
                 # Add new commands/gui buttons here
                 return [
                     ...,
                     Command(
                         name="YourCommandName", # this has to be unique,
                         gui_label="This is Button Text in the GUI!",
                         action=self.your_mixin_entry_point, # no brackets!
                         kwargs={}, # optional if you need to pass parameters to your entrypoint
                     ),
                 ]
    ```
3. You can now run your Mixin using `poetry run adb-auto-player YourCommandName`.

Check out these classes:  
[Game](../../../python/adb_auto_player/game.py) and [AFKJourneyBase](../../../python/adb_auto_player/games/afk_journey/afk_journey_base.py) for functions you can use in your Mixin.

And of course check out other Mixins to get a rough idea how to get started!


## New Game
Right now there are placeholders in the code and the idea is to allow adding new bots, because we are only writing bots for 1 game right now it is hardcoded in some places.  
If you want to write a bot for another game and use this as a baseline reach out. [<Click Here for Contact>](../introduction.md#contact)  
We will make adjustments to support bots for new games as soon as there is somebody really interested in making one.
