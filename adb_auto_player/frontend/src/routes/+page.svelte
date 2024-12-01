<script lang="ts">
    import CommandPanel from "./CommandPanel.svelte";

    let disableActions = false;
    let game: string | null = null;
    let games: string[] | null = null;
    let buttons: { label: string, index: number }[] = [];

    function updateMenu() {
        window.eel?.get_menu()((response: string[] | null) => {
            if (JSON.stringify(games) !== JSON.stringify(response)) {
                games = response;

                buttons = [];

                if (games !== null) {
                    buttons = games.map((gameName, index) => ({ label: gameName, index }));
                }
            }
        });
    }

    function updateGame() {
        if (disableActions) {
            return;
        }
        window.eel?.get_running_supported_game()((response: null | string) => {
            if (game !== response) {
                game = response;
                updateMenu();
            }
        });
    }

    updateGame();
    setInterval(updateGame, 3000);

    function executeMenuItem(event: Event, index: number) {
        event.preventDefault();
        disableActions = true;
        window.eel?.execute(index)(() => {
            disableActions = false;
        });
    }
    const eel = window.eel
    eel.expose(append_to_log);
    function append_to_log(message: string) {
        const log = document.getElementById('log') as HTMLTextAreaElement | null;
        if (log === null) {
            return;
        }
        log.value += message + '\n';
        log.scrollTop = log.scrollHeight;
    }
</script>

<main class="container">
    <h1>{game ? game : "Please start a supported game"}</h1>

    <CommandPanel title={"Menu"}>
        {#if buttons.length > 0}
            {#each buttons as { label, index }}
                <button disabled={disableActions} on:click={(event) => executeMenuItem(event, index)}>
                    {label}
                </button>
            {/each}
        {:else}
            <p>No menu items available.</p>
        {/if}
    </CommandPanel>
    <CommandPanel title={"Logs"}>
        <textarea id="log" readonly></textarea>
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

    textarea {
        width: 100%;
        height: 200px;
        overflow-y: scroll;
        overflow-x: scroll;
        resize: none;
        white-space: pre;
        overflow-wrap: normal;
    }

    button {
        margin: 5px;
        padding: 10px 20px;
        font-size: 1em;
        cursor: pointer;
        border: none;
        border-radius: 5px;
        transition: background-color 0.2s ease-in-out;
    }

    button:disabled {
        cursor: not-allowed;
    }
</style>
