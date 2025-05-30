<script lang="ts">
  import { Modal } from "@skeletonlabs/skeleton-svelte";

  interface ModalProps {
    showModal: boolean;
    modalContent?: () => any;
    onClose?: () => void;
  }

  let { showModal = $bindable(), modalContent, onClose }: ModalProps = $props();

  function handleOpenChange(e: { open: boolean }) {
    if (e.open) {
      showModal = true;
      return;
    }

    if (onClose) {
      onClose();
      return;
    }

    showModal = false;
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
