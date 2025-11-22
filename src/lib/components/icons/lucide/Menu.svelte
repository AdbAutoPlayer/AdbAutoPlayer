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
  <path d="M4 5h16"/>
  <path d="M4 12h16"/>
  <path d="M4 19h16"/>
</svg>
