<script lang="ts">
  let { size, className, strokeWidth = 3 }: IconProps = $props();
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width={strokeWidth}
  stroke-linecap="round"
  stroke-linejoin="round"
  class={className}
>
  <line x1="12" y1="5" x2="12" y2="19"></line>
  <polyline points="19 12 12 19 5 12"></polyline>
</svg>
