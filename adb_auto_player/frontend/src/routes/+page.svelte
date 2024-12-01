<script lang="ts">
    import CommandPanel from "./CommandPanel.svelte";

    let disableActions = false;
    let game: string | null = null;
    let games: string[] | null = null;
    let buttons: { label: string, index: number }[] = [];

    function append_to_log(message: string) {
        const log = document.getElementById('log') as HTMLDivElement | null;
        if (log === null) {
            return;
        }
        const logEntry = document.createElement('div');
        logEntry.style.color = 'white';
        if (message.includes('[DEBUG]')) {
            logEntry.style.color = 'blue';
        } else if (message.includes('[INFO]')) {
            logEntry.style.color = 'green';
        } else if (message.includes('[WARNING]')) {
            logEntry.style.color = 'yellow';
        } else if (messpycage.includes('[ERROR]')) {
            logEntry.style.color = 'red';
        } else if (message.includes('[CRITICAL]')) {
            logEntry.style.color = 'darkred';
        }
        logEntry.textContent = message;
        log.appendChild(logEntry);
        log.scrollTop = log.scrollHeight;
    }
    window.eel.expose(append_to_log);

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

    function updateState() {
        if (disableActions) {
            window.eel?.action_is_running()((response: boolean) => {
                disableActions = response;
            })
        } else {
            window.eel?.get_running_supported_game()((response: null | string) => {
                if (game !== response) {
                    game = response;
                    updateMenu();
                }
            });
        }

    }

    updateState();
    setInterval(updateState, 3000);

    function executeMenuItem(event: Event, index: number) {
        event.preventDefault();
        disableActions = true;
        window.eel?.execute(index);
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
        <div id="log" class="log-container"></div>
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

    .log-container {
        height: 200px;
        overflow-y: auto;
        background-color: #0f0f0f98;
        padding: 10px;
        white-space: pre-wrap;
        text-align: left;
        font-family: Consolas,monospace;
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
