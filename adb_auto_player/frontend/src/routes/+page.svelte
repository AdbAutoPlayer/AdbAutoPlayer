<script lang="ts">
    let eel = window.eel;
    eel?.set_host('ws://localhost:8888');
    import CommandPanel from "./CommandPanel.svelte";

    function eelTest(event: Event) {
        event.preventDefault();
        eel.say_hello_py("Javascript World!");
    }
</script>

<main class="container">
    <h1>Adb Auto Player</h1>
    <CommandPanel title={"Test"}>
        <button onclick={eelTest}>Test Eel</button>
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
