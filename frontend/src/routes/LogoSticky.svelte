<script lang="ts">
  import { pollRunningGame } from "$lib/stores/polling";
</script>

<div class="select-none pointer-events-none fixed bottom-0 right-5 -z-50 m-0">
  <img
    src={$pollRunningGame ? "/images/3583082.png" : "/images/3583083.png"}
    alt="uwu"
    draggable="false"
    class="max-w-[200px]"
  />
</div>
