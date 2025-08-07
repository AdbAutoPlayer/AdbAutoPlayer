<script lang="ts">
  import { pollRunningGame } from "$lib/stores/polling";
</script>

<div class="pointer-events-none fixed right-5 bottom-0 -z-50 m-0 select-none">
  <img
    src={$pollRunningGame ? "/images/3583082.png" : "/images/3583083.png"}
    alt="uwu"
    draggable="false"
    class="max-w-[200px]"
  />
</div>
