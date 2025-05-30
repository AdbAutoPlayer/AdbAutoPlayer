<script lang="ts">
  import { Modal } from "@skeletonlabs/skeleton-svelte";

  let { showModal = $bindable(), modalContent, onClose } = $props();

  function handleOpenChange(e: { open: boolean }) {
    if (!e.open && showModal) {
      // Modal is being closed, call the parent's close handler
      if (onClose) {
        onClose();
      }
    } else {
      showModal = e.open;
    }
  }
</script>

<Modal
  open={showModal}
  onOpenChange={handleOpenChange}
  backdropClasses="backdrop-blur-sm"
  positionerAlign=""
  contentBase="card bg-surface-100-900 p-5 space-y-4 shadow-xl max-w-screen-sm m-4 max-h-[90vh] min-w-[280px]"
>
  {#snippet content()}
    {@render modalContent?.()}
  {/snippet}
</Modal>
