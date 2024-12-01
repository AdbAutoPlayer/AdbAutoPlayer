<script>
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
    });
    let { children } = $props();

    window.addEventListener('keydown', function(e) {
        if ((e.key === 'F5') || (e.ctrlKey && e.key === 'r')) {
            e.preventDefault(); // Prevent page refresh
        }
    });

    window.onbeforeunload = function(event) {
        event.preventDefault();
    };
</script>

{@render children()}

<div class="mdbook-sticky">
    <a href="https://yulesxoxo.github.io/AdbAutoPlayer/" target="_blank">
        <img src="/icons/help-circle.svg" alt="Documentation" width="24" height="24" draggable="false">
    </a>
</div>
<div class="logo-sticky">
    <img src="/images/3583083.png" alt="uwu" draggable="false"/>
</div>

<style>
    :root {
        color-scheme: dark;
    }

    .mdbook-sticky {
        user-select: none;
        position: fixed;
        top: 0;
        left: 0;
        z-index: 1000;
        margin: 10px;
        cursor: pointer;
    }

    .logo-sticky {
        user-select: none;
        pointer-events: none;
        position: fixed;
        bottom: 0;
        right: 0;
        z-index: -100;
        margin: 0;
    }

    .logo-sticky img {
        user-select: none;
        pointer-events: none;
        max-width: 200px;
        height: auto;
    }

    :global(:root) {
        font-family: Inter, Avenir, Helvetica, Arial, sans-serif;
        font-size: 16px;
        line-height: 24px;
        font-weight: 400;

        font-synthesis: none;
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        -webkit-text-size-adjust: 100%;
        color: #f6f6f6;
        background-color: #2f2f2f;
    }

    :global(a) {
        font-weight: 500;
        color: #646cff;
        text-decoration: inherit;
    }

    :global(a:hover) {
        color: #24c8db;
    }

    :global(h1) {
        text-align: center;
    }

    :global(
        button,
        input,
        textarea
    ) {
        border-radius: 8px;
        border: 1px solid transparent;
        padding: 0.6em 1.2em;
        font-size: 1em;
        font-weight: 500;
        font-family: inherit;
        color: #ffffff;
        background-color: #0f0f0f98;
        transition: border-color 0.25s;
        box-shadow: 0 2px 2px rgba(0, 0, 0, 0.2);
        outline: none;
    }

    :global(button) {
        cursor: pointer;
    }
    :global(button:hover) {
        border-color: #396cd8;
    }
    :global(button:active) {
        border-color: #396cd8;
        background-color: #0f0f0f69;
    }

    :global(textarea) {
        width: 80%;
        max-width: 600px;
        resize: vertical;
        min-height: 100px;
    }
</style>
