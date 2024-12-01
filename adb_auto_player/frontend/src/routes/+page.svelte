<script lang="ts">
    import CommandPanel from "./CommandPanel.svelte";

    let disabled = false;

    function eelTest(event: Event) {
        event.preventDefault();
        disabled = true;
        window.eel?.test_bla_bla()((response: string) => {
            console.log(response);
            disabled = false;
        });
    }
</script>

<main class="container">
    <h1>Adb Auto Player</h1>
    <CommandPanel title={"Menu"}>
        <button {disabled} onclick={eelTest} >Push Season Talent Stages</button>
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
