<script lang="ts">
  import { pollRunningGame } from "$lib/stores/polling";
</script>

<div class="logo-sticky">
  <img
    src={$pollRunningGame ? "/images/3583082.png" : "/images/3583083.png"}
    alt="uwu"
    draggable="false"
  />
</div>

<style>
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
    max-width: 200px;
  }
</style>
