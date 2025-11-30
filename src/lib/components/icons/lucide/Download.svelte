<script lang="ts">
  let {
    size,
    className,
    strokeWidth = 2 ,
  }: IconProps = $props();
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
  class="{className}"
>
  <path d="M12 15V3"/>
  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
  <path d="m7 10 5 5 5-5"/>
</svg>
