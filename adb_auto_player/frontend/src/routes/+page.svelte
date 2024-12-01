<script lang="ts">
    import CommandPanel from "./CommandPanel.svelte";

    let disableActions = false;
    let game: string | null = null;
    let games: string[] | null = null;

    function updateMenu() {
        window.eel?.get_menu()((response: string[] | null) => {
            // TODO
            // if the response differs from games
            // clear all the buttons in the commandpanel component
            games = response;
            if (null === games) {
                return;
            }
            // Add buttons to the commandpanel component
            // one button for each string
            // the button text should be the string
            // it should execute the executeMenuItem on click
            // and pass the index of the string from this array
        });
    }

    function updateGame() {
        if (disableActions) {
            return;
        }
        window.eel?.get_running_supported_game()((response: null|string) => {
            if (game != response) {
                updateMenu();
                game = response;
            }
        });
    }

    updateGame();
    setInterval(updateGame, 3000);

    function executeMenuItem(event: Event) {
        event.preventDefault();
        disableActions = true;
        window.eel?.execute(
            // TODO Button index
        )((response: null|string) => {
            disableActions = false;
        });
    }
</script>

<main class="container">
    <h1>{game ? game : "Please start a supported game"}</h1>

    <CommandPanel title={"Menu"}>
        Placeholder
    </CommandPanel>
</main>

<style>
    .container {
        margin: 0;
        padding-top: 2vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        text-align: center;
    }
</style>
