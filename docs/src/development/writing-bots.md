# Writing Bots

Check out [Python README](https://github.com/yulesxoxo/AdbAutoPlayer/blob/main/docs/src/development/python-README.md) if you need help with setting up the project in general.

## AFK Journey
If you want to add any feature to the AFK Journey Bot:
1. Create a new mixin in the mixins dir [python/adb_auto_player/games/afk_journey/mixins](https://github.com/yulesxoxo/AdbAutoPlayer/tree/main/python/adb_auto_player/games/afk_journey/mixins)
    ```python
    import logging
    from abc import ABC
    from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase
    
    class YourMixin(AFKJourneyBase, ABC):
        def your_mixin_entry_point(self) -> None:
            """Entry for your feature."""
            logging.info("Hello World!")
            self.start_up() # initializes most things you will need like device and config
            # if your bot needs to be fast e.g. Fishing or any other interactive mode you need to enable device streaming
            # self.start_up(device_streaming=True)
    ```

2. Add a new Command in [class AFKJourney](https://github.com/yulesxoxo/AdbAutoPlayer/tree/main/python/adb_auto_player/games/afk_journey/main.py).
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
3. You can now run your Mixin using `uv run adb-auto-player YourCommandName`.

Check out these classes:  
[Game](https://github.com/yulesxoxo/AdbAutoPlayer/tree/main/python/adb_auto_player/game.py) and AFK Journey [Base](https://github.com/yulesxoxo/AdbAutoPlayer/tree/main/python/adb_auto_player/games/afk_journey/base.py) for functions you can use in your Mixin.

And of course check out other Mixins to get a rough idea how to get started!


## New Game
For the simplest setup check the [Infinity Nikki Bot](https://github.com/yulesxoxo/AdbAutoPlayer/tree/main/python/adb_auto_player/games/infinity_nikki).  
It only has a single feature and a single config option.  
Besides making your Game Class you just have to add the game to the `__get_games()` function in [main.py](https://github.com/yulesxoxo/AdbAutoPlayer/blob/main/python/adb_auto_player/main.py)
