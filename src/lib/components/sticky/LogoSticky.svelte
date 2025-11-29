<script lang="ts">
  import { activeProfile, profileStates } from "$lib/stores";

  const awake = "/images/3583082.png"
  const sleep = "/images/3583083.png"
</script>

<div class="pointer-events-none fixed right-5 bottom-0 -z-50 m-0 select-none">
  <img
    src={$profileStates[$activeProfile]?.active_task ? sleep : awake}
    alt="uwu"
    draggable="false"
    class="max-w-[200px]"
  />
</div>
